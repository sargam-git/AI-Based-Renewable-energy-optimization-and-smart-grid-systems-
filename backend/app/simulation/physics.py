"""Unit-consistent educational models. Powers in kW, energy in kWh, elapsed time in hours."""
import numpy as np
from app.config import SOLAR_CAPACITY, WIND_CAPACITY, TRANSFORMER_KVA

def solar_power(irradiance, temperature, cloud_cover=0, wind_speed=3, capacity=SOLAR_CAPACITY):
    w=np.asarray(irradiance,dtype=float); t=np.asarray(temperature,dtype=float)
    # Weather irradiance is already cloud-attenuated. Cloud cover is a model feature,
    # NOT applied a second time in this physical reference calculation.
    cell_temp=t+.028*w
    return np.clip(capacity*w/1000*(1-.0035*(cell_temp-25))*.96,0,capacity)

def wind_power(speed, air_density=1.18, capacity=WIND_CAPACITY):
    v=np.asarray(speed,dtype=float); rho=np.asarray(air_density,dtype=float)
    fraction=np.clip((v**3-3**3)/(12**3-3**3),0,1)
    return np.where((v>=3)&(v<25),capacity*fraction*np.clip(rho/1.225,.8,1.2),0.0)

def battery_step(energy, charge_kw, discharge_kw, config, hours=1):
    c=config if isinstance(config,dict) else config.model_dump()
    capacity=c['capacity_kwh']; lo=capacity*c['min_soc']/100; hi=capacity*c['max_soc']/100
    if not all(np.isfinite(v) for v in [energy,charge_kw,discharge_kw,hours]): raise ValueError('Battery inputs must be finite')
    if min(energy,charge_kw,discharge_kw)<-1e-8 or hours<=0: raise ValueError('Negative battery input or nonpositive time interval')
    if charge_kw>c['max_charge_kw']+1e-7 or discharge_kw>c['max_discharge_kw']+1e-7: raise ValueError('Battery power limit exceeded')
    if charge_kw>1e-7 and discharge_kw>1e-7: raise ValueError('Simultaneous charging and discharging is forbidden')
    charge=min(charge_kw, max(0,hi-energy)/(c['charge_efficiency']*hours)) if hours else 0
    discharge=min(discharge_kw, max(0,energy-lo)*c['discharge_efficiency']/hours) if hours else 0
    final=np.clip(energy+hours*(charge*c['charge_efficiency']-discharge/c['discharge_efficiency']),lo,hi)
    return {'energy_kwh':float(final),'soc':float(100*final/capacity),'charge_kw':float(charge),'discharge_kw':float(discharge)}

def distribute(renewable, demand, battery_discharge=0, grid_import=0):
    if min(renewable,demand,battery_discharge,grid_import)<0: raise ValueError('Power must be nonnegative')
    served=min(demand,renewable+battery_discharge+grid_import)
    used_re=min(renewable,served)
    used_battery=min(battery_discharge,max(0,served-used_re))
    used_grid=max(0,served-used_re-used_battery)
    return {'served_kw':served,'unserved_kw':demand-served,'renewable_direct_kw':used_re,'battery_to_load_kw':used_battery,'grid_to_load_kw':used_grid}

def allocate_consumers(served, demand):
    """Essential-first allocation, then proportional flexible allocation.
    Essential fractions are illustrative policy assumptions, not real load control.
    """
    sectors=['residential','commercial','industrial']
    requested=np.array([max(0,demand[k+'_kw']) for k in sectors])
    essential=requested*np.array([.65,.35,.25])
    if served < -1e-7: raise ValueError('Served load cannot be negative')
    served=max(0.0,served)
    total=requested.sum()
    if total<=0: return {k+'_served_kw':0.0 for k in sectors}
    if served>=total: return {k+'_served_kw':float(v) for k,v in zip(sectors,requested)}
    if served<=essential.sum(): allocated=essential*(served/essential.sum())
    else:
        flexible=requested-essential
        allocated=essential+flexible*((served-essential.sum())/flexible.sum())
    return {k+'_served_kw':float(v) for k,v in zip(sectors,allocated)}

def electrical_measurements(power_kw, timestamp, fault_mode='none', demand_factor=1):
    sag=fault_mode in ('voltage_sag','combined'); deviation=fault_mode in ('frequency_deviation','combined'); overload=fault_mode=='overload'
    pf=.80 if (overload or fault_mode=='combined') else .96+.015*np.sin(timestamp.hour*.6)
    voltage=415*(.83 if sag else 1+.009*np.sin(timestamp.hour*.8))
    frequency=49.15 if deviation else 50+.025*np.sin(timestamp.hour*.7)
    active=max(0,float(power_kw)); apparent=active/pf
    current=apparent*1000/(np.sqrt(3)*voltage)
    reactive=np.sqrt(max(0,apparent**2-active**2))
    return {'voltage':float(voltage),'current':float(current),'frequency':float(frequency),'active_power':active,'reactive_power':float(reactive),'apparent_power':float(apparent),'power_factor':float(pf),'transformer_loading':float(100*apparent/TRANSFORMER_KVA)}
