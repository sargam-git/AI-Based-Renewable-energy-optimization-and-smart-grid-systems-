"""Receding-horizon unit commitment with a single-bus energy balance (MILP).

All powers are AC-side kW; one interval is one hour. No grid charging is allowed.
Binary variables prevent charge/discharge and import/export in the same interval.
"""
import numpy as np
from scipy.optimize import Bounds, LinearConstraint
from app.optimization.solver import solve_milp as milp
from scipy.sparse import lil_matrix
from app.simulation.physics import battery_step, distribute, allocate_consumers

VARIABLES=['renewable_direct_kw','charge_kw','discharge_kw','import_kw','export_kw','curtailed_kw','unserved_kw','energy_kwh','charge_mode','import_mode']
N=len(VARIABLES)

def tariff_at(timestamp,base):
    return base*(1.5 if 17<=timestamp.hour<22 else (.8 if timestamp.hour<6 else 1))

def optimize_schedule(frame, config, initial_energy=None):
    c=config.model_dump() if hasattr(config,'model_dump') else config
    b=c['battery']; capacity=b['capacity_kwh']; min_e=capacity*b['min_soc']/100; max_e=capacity*b['max_soc']/100
    initial=float(initial_energy if initial_energy is not None else capacity*b['initial_soc']/100)
    initial=float(np.clip(initial,min_e,max_e)); t=len(frame); n=N*t
    R=np.maximum(0,frame.renewable_predicted_kw.to_numpy(dtype=float)); D=np.maximum(0,frame.total_predicted_kw.to_numpy(dtype=float))
    times=list(frame.timestamp); prices=np.array([tariff_at(x,c['import_tariff']) for x in times])
    objective=np.zeros(n); lower=np.zeros(n); upper=np.full(n,np.inf); integer=np.zeros(n)
    for i in range(t):
        k=i*N
        upper[k:k+N]=[R[i],b['max_charge_kw'],b['max_discharge_kw'],c['grid_import_limit_kw'] if c['grid_available'] else 0,c['grid_export_limit_kw'] if c['grid_available'] and c['export_enabled'] else 0,R[i],D[i],max_e,1,1]
        lower[k+7]=min_e; integer[k+8:k+10]=1
        objective[k:k+8]=[0,c['degradation_cost'],c['degradation_cost'],prices[i]+.001,-c['export_tariff'],.035,100,0]
    # A x constraints: renewable balance, load balance, SOC dynamics and mode exclusivity.
    rows=3*t+4*t+t+1; A=lil_matrix((rows,n)); lo=np.full(rows,-np.inf); hi=np.full(rows,np.inf)
    for i in range(t):
        k=i*N; r=3*i
        for col,value in [(k,1),(k+1,1),(k+4,1),(k+5,1)]: A[r,col]=value
        lo[r]=hi[r]=R[i]
        for col,value in [(k,1),(k+2,1),(k+3,1),(k+6,1)]: A[r+1,col]=value
        lo[r+1]=hi[r+1]=D[i]
        A[r+2,k+7]=1; A[r+2,k+1]=-b['charge_efficiency']; A[r+2,k+2]=1/b['discharge_efficiency']
        if i: A[r+2,k+7-N]=-1; lo[r+2]=hi[r+2]=0
        else: lo[r+2]=hi[r+2]=initial
        q=3*t+4*i
        A[q,k+1]=1; A[q,k+8]=-b['max_charge_kw']; hi[q]=0
        A[q+1,k+2]=1; A[q+1,k+8]=b['max_discharge_kw']; hi[q+1]=b['max_discharge_kw']
        A[q+2,k+3]=1; A[q+2,k+9]=-upper[k+3]; hi[q+2]=0
        A[q+3,k+4]=1; A[q+3,k+9]=upper[k+4]; hi[q+3]=upper[k+4]
    # Avoid treating the last battery inventory as free energy when grid is available.
    # During an outage the stored initial energy may be used down to the safety floor.
    lo[-1]=initial if c['grid_available'] else min_e; A[-1,n-N+7]=1
    # Conservative PER-HOUR load-serving screen: 95% of 1000 kVA at 0.95 PF.
    # This is a single-bus capacity proxy, NOT an AC network power-flow solution.
    for i in range(t):
        k=i*N; row=7*t+i; A[row,k]=1; A[row,k+2]=1; A[row,k+3]=1
        hi[row]=950.0
    result=milp(c=objective,integrality=integer,bounds=Bounds(lower,upper),constraints=LinearConstraint(A.tocsr(),lo,hi),options={'time_limit':25,'mip_rel_gap':.000001})
    if not result.success or result.x is None: raise RuntimeError(f'Optimization failed: {result.message}')
    x=np.maximum(result.x,0); schedule=[]; warnings=[]
    for i in range(t):
        v=x[i*N:(i+1)*N]; row={key:float(v[j]) for j,key in enumerate(VARIABLES[:8])}
        for key in ['charge_kw','discharge_kw','import_kw','export_kw','curtailed_kw','unserved_kw']:
            if row[key]<1e-6: row[key]=0.0
        row.update({'timestamp':times[i].isoformat(),'solar_predicted_kw':float(frame.iloc[i].solar_predicted_kw),'wind_predicted_kw':float(frame.iloc[i].wind_predicted_kw),'renewable_predicted_kw':float(R[i]),'demand_predicted_kw':float(D[i]),'soc':float(100*row['energy_kwh']/capacity),'tariff':float(prices[i]),'residential_kw':float(frame.iloc[i].residential_kw),'commercial_kw':float(frame.iloc[i].commercial_kw),'industrial_kw':float(frame.iloc[i].industrial_kw)})
        row['served_kw']=max(0.0,D[i]-row['unserved_kw']); row['battery_available_kwh']=row['energy_kwh']-min_e
        row.update(allocate_consumers(row['served_kw'],{k+'_kw':float(frame.iloc[i][k+'_kw']) for k in ['residential','commercial','industrial']}))
        row['status']='Charging' if row['charge_kw']>.01 else ('Discharging' if row['discharge_kw']>.01 else 'Idle')
        row['balance_residual_kw']=row['renewable_direct_kw']+row['discharge_kw']+row['import_kw']-row['served_kw']
        share=row['renewable_direct_kw']/R[i] if R[i]>0 else 0
        row['solar_direct_kw']=row['solar_predicted_kw']*share; row['wind_direct_kw']=row['wind_predicted_kw']*share
        row['explanation']=explain_row(row,c)
        schedule.append(row)
        if row['unserved_kw']>.01: warnings.append(i)
    total_gen=float(R.sum()); total_load=float(D.sum()); served=sum(r['served_kw'] for r in schedule)
    procurement=sum(r['import_kw']*r['tariff'] for r in schedule); degradation=sum((r['charge_kw']+r['discharge_kw'])*c['degradation_cost'] for r in schedule)
    export_revenue=sum(r['export_kw']*c['export_tariff'] for r in schedule)
    net_cost=procurement+degradation-export_revenue
    baseline=sum(r['served_kw']*r['tariff'] for r in schedule)
    summary={'generation_kwh':total_gen,'solar_kwh':float(frame.solar_predicted_kw.sum()),'wind_kwh':float(frame.wind_predicted_kw.sum()),'demand_kwh':total_load,'served_kwh':served,'unserved_kwh':sum(r['unserved_kw'] for r in schedule),'import_kwh':sum(r['import_kw'] for r in schedule),'export_kwh':sum(r['export_kw'] for r in schedule),'curtailed_kwh':sum(r['curtailed_kw'] for r in schedule),'charged_kwh':sum(r['charge_kw'] for r in schedule),'discharged_kwh':sum(r['discharge_kw'] for r in schedule),'renewable_utilization':100*(total_gen-sum(r['curtailed_kw'] for r in schedule))/total_gen if total_gen else 0,'grid_dependency':100*sum(r['import_kw'] for r in schedule)/served if served else 0,'procurement_cost':procurement,'degradation_cost':degradation,'export_revenue':export_revenue,'net_cost':net_cost,'baseline_cost':baseline,'estimated_savings':baseline-net_cost,'carbon_avoided_kg':(total_gen-sum(r['curtailed_kw'] for r in schedule))*c['carbon_factor'],'peak_demand_kw':float(D.max()),'peak_hour':times[int(D.argmax())].isoformat(),'objective_value':float(result.fun),'solver':'HiGHS MILP (highspy + SciPy)','solver_gap':float(result.mip_gap),'initial_energy_kwh':initial,'final_energy_kwh':schedule[-1]['energy_kwh'],'risk_hours':len(warnings),'max_balance_residual_kw':max(abs(r['balance_residual_kw']) for r in schedule),'horizon_hours':t,'currency':'USD'}
    return {'status':'optimal' if result.mip_gap<.001 else 'feasible','summary':summary,'schedule':schedule,'constraints':{'soc_bounds_pct':[b['min_soc'],b['max_soc']],'power_bounds_kw':[b['max_charge_kw'],b['max_discharge_kw']],'import_limit_kw':upper[3],'export_limit_kw':upper[4],'no_grid_charging':True,'no_simultaneous_modes':True,'terminal_energy_floor_kwh':lo[-1],'load_serving_capacity_kw':950.0},'objective':'Minimize time-of-use procurement + battery throughput cost + curtailment penalty + unserved-load penalty − export revenue. Curtailment and grid-dependency penalties favor productive renewable use.'}

def explain_row(r,c):
    if r['unserved_kw']>.01:
        return f"Demand {r['demand_predicted_kw']:.1f} kW exceeds available supply and battery power/energy limits. {r['unserved_kw']:.1f} kW remains unserved; inspect the reliability warning. No unsafe limit is relaxed."
    if r['charge_kw']>.01:
        return f"Allocate renewable output to charge at {r['charge_kw']:.1f} kW, reaching {r['soc']:.1f}% SOC for later use. Forecast demand is {r['demand_predicted_kw']:.1f} kW; export is {r['export_kw']:.1f} kW within the permitted limit."
    if r['discharge_kw']>.01:
        return f"Discharge {r['discharge_kw']:.1f} kW to cover the renewable shortfall at a {r['tariff']:.3f} USD/kWh import tariff. Stored energy falls to {r['soc']:.1f}% while honoring the minimum reserve."
    if r['import_kw']>.01:
        return f"Renewables supply {r['renewable_direct_kw']:.1f} kW of {r['demand_predicted_kw']:.1f} kW demand. Import {r['import_kw']:.1f} kW; preserving battery reserve is preferable under the horizon constraints."
    if r['export_kw']>.01: return f"Meet {r['demand_predicted_kw']:.1f} kW demand with renewables and export {r['export_kw']:.1f} kW. Battery reserve or power limits make additional storage less valuable."
    if r['curtailed_kw']>.01: return f"Curtail {r['curtailed_kw']:.1f} kW after meeting demand: storage/export constraints prevent utilization. No grid charging is permitted."
    return f"Renewable output matches the {r['demand_predicted_kw']:.1f} kW demand. Battery remains idle at {r['soc']:.1f}% SOC."

def settle_interval(weather, demand, plan, config, energy):
    """Realize a simulated interval; adjust imports/exports for forecast errors."""
    from app.simulation.physics import solar_power,wind_power
    c=config.model_dump() if hasattr(config,'model_dump') else config
    actual_r=float(solar_power(weather['irradiance'],weather['temperature'])+wind_power(weather['wind_speed'],weather['air_density']))
    d=demand['total_kw']; desired_c=min(plan['charge_kw'],max(0,actual_r-min(actual_r,d)))
    state=battery_step(energy,desired_c,plan['discharge_kw'],c['battery'])
    net=actual_r-min(actual_r,d)+state['discharge_kw']-state['charge_kw']
    imp=min(max(0,d-actual_r-state['discharge_kw']),c['grid_import_limit_kw'] if c['grid_available'] else 0)
    exp=min(max(0,net),c['grid_export_limit_kw'] if c['grid_available'] and c['export_enabled'] else 0)
    split=distribute(actual_r,d,state['discharge_kw'],imp)
    return {**state,**split,'timestamp':plan['timestamp'],'solar_kw':float(solar_power(weather['irradiance'],weather['temperature'])),'wind_kw':float(wind_power(weather['wind_speed'],weather['air_density'])),'export_kw':exp,'curtailed_kw':max(0,net-exp),'import_kw':imp,**demand}
