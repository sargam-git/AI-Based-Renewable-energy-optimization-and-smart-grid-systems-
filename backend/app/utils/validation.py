"""Generate an audit-friendly scenario comparison from the actual decision engine."""
import json
from datetime import datetime,timezone
from app.database.session import SessionLocal
from app.schemas.energy import SimulationConfig
from app.services.engine import execute

def scenario_validation():
    rows=[]
    with SessionLocal() as db:
        for scenario in ['normal','low_solar','high_demand','surplus','low_battery','outage','abnormal']:
            c=SimulationConfig(scenario=scenario)
            p=execute(db,c,datetime(2026,11,1,10),c.battery.capacity_kwh*c.battery.initial_soc/100)
            s=p['optimization']['summary']
            rows.append({'scenario':scenario,'demand_multiplier':c.demand_factor,'status':p['optimization']['status'],'generation_kwh':round(s['generation_kwh'],2),'demand_kwh':round(s['demand_kwh'],2),'charged_kwh':round(s['charged_kwh'],2),'discharged_kwh':round(s['discharged_kwh'],2),'import_kwh':round(s['import_kwh'],2),'export_kwh':round(s['export_kwh'],2),'unserved_kwh':round(s['unserved_kwh'],2),'curtailed_kwh':round(s['curtailed_kwh'],2),'renewable_utilization_pct':round(s['renewable_utilization'],2),'anomalies':len(p['monitoring']['anomalies']),'balance_residual_kw':s['max_balance_residual_kw'],'solver_gap':s['solver_gap']})
    return {'generated_at':datetime.now(timezone.utc).isoformat(),'notice':'Read-only 24-hour scenario calculations from fixed initial state; not written to simulation history.','horizon_hours':24,'scenarios':rows}
if __name__=='__main__': print(json.dumps(scenario_validation(),indent=2))
