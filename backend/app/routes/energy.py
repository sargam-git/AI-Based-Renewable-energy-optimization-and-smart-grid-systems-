from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import json
import pandas as pd
from app.database.session import get_db
from app.schemas.energy import *
from app.services.engine import current_payload,run_simulation,advance_simulation,dashboard
from app.services.repository import get_state
from app.ml.predictor import load_model,upload_predictions,predict_frame
from app.ml.preprocessing import prepare_upload
from app.models.records import Prediction
from app.config import MODELS,DATA
from app.utils.concurrency import simulation_lock

router=APIRouter(tags=['Energy intelligence'])
@router.get('/dashboard')
def get_dashboard(db:Session=Depends(get_db)): return dashboard(db)
@router.get('/forecast')
def get_forecast(db:Session=Depends(get_db)):
    p=current_payload(db); return {'source':p['source'],'hourly':p['forecast'],'daily':{'solar_kwh':p['optimization']['summary']['solar_kwh'],'wind_kwh':p['optimization']['summary']['wind_kwh'],'demand_kwh':p['optimization']['summary']['demand_kwh']},'models':json.loads((MODELS/'registry.json').read_text())}
@router.post('/predict/{target}')
def predict(target:str,body:PredictRequest,db:Session=Depends(get_db)):
    if target not in ['solar','wind','load'] or target!=body.target: raise HTTPException(422,'Target must be solar, wind or load and match the payload')
    output=upload_predictions(body.records,target)
    for r in output.to_dict('records'):
        db.add(Prediction(timestamp=r['timestamp'].to_pydatetime(),target=target,predicted=r['predicted_kw'],actual=None if pd.isna(r['actual_kw']) else r['actual_kw'],model_version=target+'-v1',source='api'))
    db.commit(); return json.loads(output.to_json(orient='records',date_format='iso'))
@router.get('/models')
def models(): return json.loads((MODELS/'registry.json').read_text())
@router.get('/eda')
def eda(): return json.loads((DATA/'eda.json').read_text())
@router.get('/battery')
def battery(db:Session=Depends(get_db)):
    p=current_payload(db); return {'config':p['config']['battery'],'current_energy_kwh':p['current']['energy_kwh'],'current_soc':p['current']['initial_soc'],'schedule':p['optimization']['schedule'],'summary':p['optimization']['summary']}
@router.post('/optimization')
def optimize(config:SimulationConfig,db:Session=Depends(get_db)):
    with simulation_lock: return run_simulation(db,config)
@router.get('/grid')
def grid(db:Session=Depends(get_db)):
    p=current_payload(db); return {'current':p['current'],'flows':p['optimization']['schedule'][0],'schedule':p['optimization']['schedule'],'recommendations':p['recommendations']}
@router.post('/simulation')
def simulation(config:SimulationConfig,db:Session=Depends(get_db)):
    with simulation_lock: return run_simulation(db,config)
@router.post('/simulation/step')
def step(body:StepRequest,db:Session=Depends(get_db)):
    with simulation_lock: return advance_simulation(db,body.hours)
@router.get('/simulation/state')
def state(db:Session=Depends(get_db)): return get_state(db)
@router.get('/simulation/scenarios')
def scenarios(): return [{'id':x,'name':n,'description':d} for x,n,d in [('normal','Normal operation','Seasonal solar and wind with a 62% initial battery charge.'),('low_solar','Cloudy / low solar','85% cloud cover and reduced irradiance; actual ML models reforecast output.'),('high_demand','Demand surge','Demand increases 65%, stressing battery and grid import limits.'),('surplus','Renewable surplus','Strong sun and wind with 30% lower demand.'),('low_battery','Low reserve','Battery starts at its minimum allowed SOC.'),('outage','Grid outage','No imports or exports; reliability depends on renewables and storage.'),('abnormal','Electrical abnormality','Low voltage, frequency deviation and high loading for detector testing.')]]
@router.post('/simulation/reset')
def reset(db:Session=Depends(get_db)):
    # Reset the operating state, not delete the audit trail.
    with simulation_lock: return run_simulation(db,SimulationConfig(),reset_clock=True)
