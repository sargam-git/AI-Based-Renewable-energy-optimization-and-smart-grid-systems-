import pytest
import pandas as pd
import numpy as np
from app.ml.predictor import load_model,predict_frame,forecast,upload_predictions
from app.ml.preprocessing import clean_dataset,prepare_upload
from app.simulation.generator import generate_dataset,weather_at,demand_at,FEATURES
from app.simulation.physics import solar_power,wind_power
from app.schemas.energy import SimulationConfig
from app.optimization.engine import optimize_schedule,settle_interval
from app.services.monitoring import assess_power
from app.simulation.physics import electrical_measurements
from datetime import datetime

def test_models_persisted_and_predict_finite():
    raw=generate_dataset(10); clean,_=clean_dataset(raw)
    for target in ['solar','wind','load']:
        bundle=load_model(target); assert bundle['features']==FEATURES[target]
        p=predict_frame(target,clean.tail(48)); assert len(p)==48
        assert np.isfinite(p).all() and (p>=0).all() and (p<=bundle['cap']).all()

def test_cleaning_handles_missing_and_outliers():
    raw=generate_dataset(120); clean,report=clean_dataset(raw)
    assert report['solar']['missing']>0
    assert report['irradiance']['invalid_or_outlier']>0
    assert clean.irradiance.dropna().between(0,1400).all()
    assert clean.solar_kw.dropna().between(0,650).all()
    assert (clean.total_lag_1.dropna()==clean.total_kw.shift(1).dropna()).all()

def test_forecast_no_future_actuals_needed():
    config=SimulationConfig(horizon=24)
    f=forecast(config,pd.Timestamp('2026-11-01T10:00'))
    assert len(f)==24 and f.timestamp.is_monotonic_increasing
    assert f.solar_predicted_kw.between(0,650).all()
    assert f.wind_predicted_kw.between(0,450).all()
    assert f.total_predicted_kw.between(0,5000).all()
    f2=forecast(config,pd.Timestamp('2026-11-01T10:00'))
    assert np.allclose(f.total_predicted_kw,f2.total_predicted_kw)

def base_frame(R=600,D=400,hours=6):
    return pd.DataFrame([{'timestamp':pd.Timestamp('2026-11-01')+pd.Timedelta(hours=i),'solar_predicted_kw':R*.65,'wind_predicted_kw':R*.35,'renewable_predicted_kw':R,'total_predicted_kw':D,'residential_kw':D*.4,'commercial_kw':D*.3,'industrial_kw':D*.3} for i in range(hours)])

@pytest.mark.parametrize('scenario',['normal','low_solar','high_demand','surplus','low_battery','outage','abnormal'])
def test_all_optimization_scenarios_constraints(scenario):
    c=SimulationConfig(scenario=scenario,horizon=24)
    f=forecast(c,pd.Timestamp('2026-11-01T10:00')); r=optimize_schedule(f,c); s=r['summary']; rows=r['schedule']
    assert r['status'] in ['optimal','feasible']
    assert s['max_balance_residual_kw']<1e-5
    for i,x in enumerate(rows):
        assert x['charge_kw']*x['discharge_kw']<1e-5
        assert x['import_kw']*x['export_kw']<1e-5
        assert c.battery.capacity_kwh*c.battery.min_soc/100-1e-5<=x['energy_kwh']<=c.battery.capacity_kwh*c.battery.max_soc/100+1e-5
        assert x['charge_kw']<=c.battery.max_charge_kw+1e-5
        assert x['discharge_kw']<=c.battery.max_discharge_kw+1e-5
        assert x['import_kw']<=r['constraints']['import_limit_kw']+1e-5
        assert x['served_kw']<=950.0+1e-5
        assert x['export_kw']<=r['constraints']['export_limit_kw']+1e-5
        assert min(x['served_kw'],x['unserved_kw'],x['curtailed_kw'])>=-1e-6
        assert x['renewable_direct_kw']+x['charge_kw']+x['export_kw']+x['curtailed_kw']==pytest.approx(x['renewable_predicted_kw'],abs=1e-5)
        previous=s['initial_energy_kwh'] if i==0 else rows[i-1]['energy_kwh']
        assert x['energy_kwh']==pytest.approx(previous+x['charge_kw']*c.battery.charge_efficiency-x['discharge_kw']/c.battery.discharge_efficiency,abs=1e-5)
        assert sum(x[k+'_served_kw'] for k in ['residential','commercial','industrial'])==pytest.approx(x['served_kw'],abs=1e-5)
        assert x['explanation']
    if scenario=='outage': assert s['import_kwh']<1e-5 and s['export_kwh']<1e-5
    if scenario=='surplus': assert s['charged_kwh']>0 and s['curtailed_kwh']+s['export_kwh']>0
    if scenario=='low_battery': assert s['initial_energy_kwh']==pytest.approx(c.battery.capacity_kwh*c.battery.min_soc/100)

def test_surplus_charges_and_deficit_discharges():
    c=SimulationConfig(horizon=6,export_enabled=False)
    f=base_frame(700,300); f.loc[3:,'renewable_predicted_kw']=0;f.loc[3:,'solar_predicted_kw']=0;f.loc[3:,'wind_predicted_kw']=0
    r=optimize_schedule(f,c); assert r['summary']['charged_kwh']>0; assert r['summary']['discharged_kwh']>0
    assert any(x['charge_kw']>0 for x in r['schedule'][:3])
    assert r['schedule'][-1]['discharge_kw']>0

def test_outage_reports_unserved_without_relaxing_limits():
    c=SimulationConfig(scenario='outage',grid_import_limit_kw=800,horizon=6)
    c.battery.initial_soc=15
    f=base_frame(0,500)
    r=optimize_schedule(f,c); assert r['summary']['unserved_kwh']>0
    assert all(x['import_kw']<1e-7 and x['energy_kwh']>=180-1e-7 for x in r['schedule'])

def test_realization_respects_energy_and_grid_limits():
    c=SimulationConfig(scenario='outage'); f=base_frame(100,600,1);p=optimize_schedule(f,c)['schedule'][0]
    w=weather_at(pd.Timestamp('2026-11-01T10:00'));d=demand_at(pd.Timestamp('2026-11-01T10:00'))
    r=settle_interval(w,d,p,c,500)
    assert r['import_kw']==0 and r['export_kw']==0
    assert 180<=r['energy_kwh']<=1140
    assert r['served_kw']+r['unserved_kw']==pytest.approx(d['total_kw'])

@pytest.mark.parametrize('mode,parameter',[('voltage_sag','voltage'),('frequency_deviation','frequency'),('overload','transformer_loading'),('combined','frequency')])
def test_fault_detection_modes(mode,parameter):
    m=electrical_measurements(1000,datetime(2026,11,1,12),mode)
    r=assess_power(m,datetime(2026,11,1,12)); assert parameter in [x['parameter'] for x in r['anomalies']]
    assert r['equipment'][0]['failure_risk']>0
    assert 'NOT' in r['risk_method']

def test_upload_missing_and_invalid_columns():
    with pytest.raises(ValueError,match='timestamp'): prepare_upload([{'irradiance':800}],'solar')
    with pytest.raises(ValueError,match='Missing columns'): prepare_upload([{'timestamp':'2026-11-01'}],'solar')
    w=weather_at(pd.Timestamp('2026-11-01T10:00'));w['temperature']='invalid'
    with pytest.raises(ValueError,match='No valid numeric'): prepare_upload([w],'solar')

def test_upload_actual_prediction_pipeline():
    rows=[]
    for h in range(48):
        t=pd.Timestamp('2026-11-01')+pd.Timedelta(hours=h);w=weather_at(t)
        rows.append({**w,'solar_kw':float(solar_power(w['irradiance'],w['temperature']))})
    output=upload_predictions(rows,'solar'); assert len(output)==48 and output.predicted_kw.notna().all()

def test_demand_multiplier_scales_forecast_total_and_every_sector():
    from app.ml.predictor import forecast
    start=pd.Timestamp('2026-11-01T10:00')
    baseline=forecast(SimulationConfig(horizon=6),start)
    for factor in [1.65,.7,1.8]:
        # Hold weather fixed to isolate the post-inference demand intervention.
        stressed=forecast(SimulationConfig(demand_factor=factor,horizon=6),start)
        for column in ['total_predicted_kw','residential_kw','commercial_kw','industrial_kw']:
            assert np.allclose(stressed[column],baseline[column]*factor)
        assert (stressed.demand_scenario_multiplier==factor).all()

def test_solver_failure_never_fabricates_dispatch(monkeypatch):
    from types import SimpleNamespace
    from app.optimization import engine
    monkeypatch.setattr(engine,'milp',lambda **kwargs:SimpleNamespace(success=False,x=None,message='test solver timeout'))
    with pytest.raises(RuntimeError,match='test solver timeout'):
        optimize_schedule(base_frame(),SimulationConfig(horizon=6))
