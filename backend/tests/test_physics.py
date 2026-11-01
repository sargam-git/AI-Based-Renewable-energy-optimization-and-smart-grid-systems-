import pytest
import numpy as np
from datetime import datetime
from app.simulation.physics import *
from app.schemas.energy import BatteryConfig,SimulationConfig

B=BatteryConfig().model_dump()
def test_solar_day_night_capacity_and_units():
    assert solar_power(0,25)==0
    assert solar_power(1000,25)==pytest.approx(650*1*(1-.0035*(53-25))*.96)
    assert solar_power(1400,25)<=650
    assert solar_power(900,35)<solar_power(900,25)

def test_wind_cut_in_rated_cut_out():
    assert wind_power(2.9)==0
    assert wind_power(3)==0
    assert wind_power(12)>0
    assert wind_power(25)==0
    assert wind_power(30)==0
    assert 0<wind_power(8)<450
    assert wind_power(8,1.1)<wind_power(8,1.225)

def test_battery_charging_efficiency():
    s=battery_step(500,100,0,B)
    assert s['energy_kwh']==pytest.approx(595)
    assert s['soc']==pytest.approx(595/1200*100)

def test_battery_discharging_efficiency():
    s=battery_step(500,0,95,B)
    assert s['energy_kwh']==pytest.approx(400)

def test_battery_full_and_empty_limits():
    full=battery_step(1140,300,0,B)
    assert full['energy_kwh']==pytest.approx(1140)
    assert full['charge_kw']==0
    empty=battery_step(180,0,300,B)
    assert empty['energy_kwh']==pytest.approx(180)
    assert empty['discharge_kw']==0

def test_partial_battery_power_is_limited_by_energy():
    s=battery_step(1120,300,0,B)
    assert s['charge_kw']==pytest.approx(20/.95)
    assert s['energy_kwh']==pytest.approx(1140)
    s=battery_step(200,0,300,B)
    assert s['discharge_kw']==pytest.approx(20*.95)
    assert s['energy_kwh']==pytest.approx(180)

@pytest.mark.parametrize('args',[(-1,0,0,1),(500,301,0,1),(500,0,301,1),(500,1,1,1),(500,-1,0,1),(500,0,0,-1),(500,0,0,0)])
def test_invalid_battery_operations(args):
    with pytest.raises(ValueError): battery_step(*args[:3],B,args[3])

def test_distribution_surplus_deficit_and_balance():
    s=distribute(700,400)
    assert s['served_kw']==400 and s['unserved_kw']==0
    s=distribute(100,500,200,100)
    assert s['served_kw']==400 and s['unserved_kw']==100
    assert s['renewable_direct_kw']+s['battery_to_load_kw']+s['grid_to_load_kw']==s['served_kw']

def test_electrical_three_phase_consistency():
    m=electrical_measurements(500,datetime(2026,11,1,12))
    assert m['apparent_power']**2==pytest.approx(m['active_power']**2+m['reactive_power']**2)
    assert m['apparent_power']*1000==pytest.approx(3**.5*m['voltage']*m['current'])
    assert m['active_power']/m['apparent_power']==pytest.approx(m['power_factor'])
    assert m['transformer_loading']==pytest.approx(m['apparent_power']/10)

def test_essential_first_load_allocation():
    d={'residential_kw':100,'commercial_kw':100,'industrial_kw':100}
    a=allocate_consumers(50,d)
    assert sum(a.values())==pytest.approx(50)
    assert a['residential_served_kw']>a['commercial_served_kw']>a['industrial_served_kw']
    a=allocate_consumers(200,d)
    assert sum(a.values())==pytest.approx(200)
    assert all(a[k+'_served_kw']<=100 for k in ['residential','commercial','industrial'])
    assert allocate_consumers(350,d)['residential_served_kw']==100

def test_scenario_presets_are_valid():
    for name in ['normal','low_solar','high_demand','surplus','low_battery','outage','abnormal']:
        c=SimulationConfig(scenario=name)
        assert c.battery.min_soc<=c.battery.initial_soc<=c.battery.max_soc

@pytest.mark.parametrize('values',[{'min_soc':90,'max_soc':20},{'initial_soc':2},{'charge_efficiency':1.2},{'capacity_kwh':-1}])
def test_invalid_battery_config(values):
    with pytest.raises(ValueError): BatteryConfig(**values)
