import pytest
from sqlalchemy import select
from app.schemas.energy import SimulationConfig
from app.models.records import Run,Configuration,MaintenanceRecord,Anomaly,Prediction
from app.database.session import SessionLocal
from app.services.engine import current_payload

@pytest.mark.parametrize('path',['/api/health','/api/dashboard','/api/forecast','/api/models','/api/eda','/api/battery','/api/grid','/api/monitoring','/api/anomalies','/api/equipment','/api/maintenance','/api/simulation/state','/api/simulation/scenarios','/api/evaluation','/api/database/summary','/api/reports?period=daily','/api/reports?period=weekly','/api/reports?period=monthly','/api/history/generation','/api/history/simulations','/api/upload/template?target=solar'])
def test_api_endpoints(client,path):
    r=client.get(path); assert r.status_code==200,(path,r.text[:300]); assert len(r.content)>0
    if 'application/json' in r.headers['content-type']: assert r.json() is not None

@pytest.mark.parametrize('scenario',['normal','low_solar','high_demand','surplus','low_battery','outage','abnormal'])
def test_scenario_api_persistence_and_balances(client,scenario):
    r=client.post('/api/simulation',json={'scenario':scenario,'horizon':12}); assert r.status_code==200,r.text
    d=r.json(); assert d['config']['scenario']==scenario; assert d['run_id']
    assert len(d['optimization']['schedule'])==12
    assert d['optimization']['summary']['max_balance_residual_kw']<1e-5
    state=client.get('/api/simulation/state').json(); assert state['run_id']==d['run_id']
    with SessionLocal() as db: assert db.get(Run,d['run_id']) is not None
    if scenario=='outage': assert d['current']['import_kw']<1e-5
    if scenario=='abnormal': assert d['current']['active_anomalies']>0

def test_invalid_simulation_and_electrical_input(client):
    assert client.post('/api/simulation',json={'wind_speed':-5}).status_code==422
    assert client.post('/api/simulation',json={'battery':{'min_soc':90,'max_soc':50}}).status_code==422
    assert client.post('/api/simulation',json={'unsafe_real_relay_command':'trip'}).status_code==422
    assert client.post('/api/monitoring/test?voltage=900').status_code==422
    assert client.get('/api/reports?period=yearly').status_code==422
    assert client.get('/api/history/unknown').status_code==422

def test_predict_api_all_targets(client):
    from app.simulation.generator import weather_at,demand_at
    import pandas as pd
    rows=[{**weather_at(t),**demand_at(t),'timestamp':t.isoformat()} for t in pd.date_range('2026-11-01',periods=25,freq='h')]
    for target in ['solar','wind','load']:
        r=client.post('/api/predict/'+target,json={'target':target,'records':rows}); assert r.status_code==200,r.text
        assert len(r.json())==25

def test_csv_upload_validation_predictions_and_reports(client):
    import pandas as pd
    from app.simulation.generator import weather_at
    rows=[weather_at(t) for t in pd.date_range('2026-11-01',periods=48,freq='h')]
    csv=pd.DataFrame(rows).to_csv(index=False)
    r=client.post('/api/upload',files={'file':('solar.csv',csv,'text/csv')},data={'target':'solar'});assert r.status_code==201,r.text
    assert r.json()['rows']==48 and 'predicted_kw' in r.json()['predictions'][0]
    bad=client.post('/api/upload',files={'file':('bad.csv','a,b\n1,2','text/csv')},data={'target':'solar'});assert bad.status_code==422
    assert 'timestamp' in bad.json()['detail']
    invalid=client.post('/api/upload',files={'file':('bad.csv',csv,'text/csv')},data={'target':'unknown'});assert invalid.status_code==422
    report=client.get('/api/reports?period=weekly&format=csv'); assert report.status_code==200
    assert 'solar_kwh' in report.text and 'attachment' in report.headers['content-disposition']

def test_maintenance_and_acknowledgement_workflow(client):
    r=client.post('/api/maintenance',json={'equipment_id':'TX-01','action':'Inspect simulated cooling and connection trends.','status':'planned'}); assert r.status_code==201
    item_id=r.json()['id']; assert client.patch(f'/api/maintenance/{item_id}').json()['status']=='completed'
    with SessionLocal() as db: assert db.get(MaintenanceRecord,item_id).status=='completed'
    assert client.patch('/api/maintenance/999999').status_code==404
    result=client.post('/api/simulation',json={'scenario':'abnormal','horizon':6}).json()
    a=result['monitoring']['anomalies'][0]; assert 'id' in a
    ack=client.post(f"/api/anomalies/{a['id']}/acknowledge",json={'note':'Reviewed for college demonstration.'});assert ack.status_code==200
    with SessionLocal() as db: assert db.get(Anomaly,a['id']).acknowledged

def test_simulation_step_updates_energy_and_restart_persistence(client):
    result=client.post('/api/simulation',json={'scenario':'normal','grid_available':False,'peak_irradiance':0,'wind_speed':0,'horizon':12}).json()
    initial=result['current']['energy_kwh']; ts=result['current']['timestamp']
    step=client.post('/api/simulation/step',json={'hours':1}); assert step.status_code==200,step.text
    d=step.json();assert d['current']['timestamp']>ts; assert d['realized_intervals']==1
    assert d['current']['energy_kwh']<initial
    state=d['run_id']; energy=d['current']['energy_kwh']
    # A fresh session reads the same committed state from SQLite.
    with SessionLocal() as db:
        saved=db.get(Configuration,'simulation'); assert saved.value['run_id']==state
        assert saved.value['energy_kwh']==pytest.approx(energy)
    assert client.get('/api/simulation/state').json()['run_id']==state

def test_state_survives_a_new_python_process(client):
    import os,sys,subprocess,json
    from app.config import DATABASE_URL
    expected=client.get('/api/simulation/state').json()
    code='import json; from sqlalchemy import create_engine,text; e=create_engine('+repr(DATABASE_URL)+'); c=e.connect(); print(c.execute(text("SELECT value FROM user_configuration WHERE key=\'simulation\'")).scalar_one()); c.close(); e.dispose()'
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,env=os.environ.copy(),check=True)
    saved=json.loads(result.stdout); assert saved['run_id']==expected['run_id']; assert saved['energy_kwh']==expected['energy_kwh']

def test_reset_restores_clock_without_deleting_runs(client):
    from app.config import SIM_START
    before=len(client.get('/api/history/simulations').json())
    result=client.post('/api/simulation/reset');assert result.status_code==200
    d=result.json();assert d['current']['timestamp']==SIM_START;assert d['config']['scenario']=='normal'
    assert len(client.get('/api/history/simulations').json())>before

def test_openapi_documentation(client):
    doc=client.get('/api/openapi.json').json(); assert '/api/simulation' in doc['paths']
    assert '/api/upload' in doc['paths'] and '/api/optimization' in doc['paths']
    assert client.get('/api/docs').status_code==200

def test_report_uses_recorded_carbon_factor(client):
    before=client.post('/api/simulation',json={'scenario':'normal','carbon_factor':.71,'horizon':6}).json()
    default_total=client.get('/api/reports?period=daily').json()['totals']['estimated_carbon_avoided_kg']
    current=before['current']; renewable=current['solar_predicted_kw']+current['wind_predicted_kw']
    client.post('/api/simulation',json={'scenario':'normal','carbon_factor':0,'horizon':6})
    zero_total=client.get('/api/reports?period=daily').json()['totals']['estimated_carbon_avoided_kg']
    assert default_total-zero_total==pytest.approx(renewable*.71,abs=1e-6)
