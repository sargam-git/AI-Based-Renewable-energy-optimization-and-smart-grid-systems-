import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import select
from app.config import DATA_NOTICE,SITE,TIMEZONE
from app.schemas.energy import SimulationConfig
from app.ml.predictor import forecast
from app.optimization.engine import optimize_schedule,settle_interval
from app.services.monitoring import assess_power
from app.services.recommendations import build_recommendations
from app.services.repository import get_state,save_state,persist_run,history_frame,seed_history
from app.simulation.generator import weather_at,demand_at
from app.simulation.physics import electrical_measurements
from app.models.records import Anomaly

logger=logging.getLogger('heliogrid')

def execute(db,config:SimulationConfig,timestamp,energy=None,previous_history=None):
    frame=forecast(config,timestamp,history=previous_history)
    result=optimize_schedule(frame,config,energy)
    first=result['schedule'][0]
    power=electrical_measurements(first['served_kw'],timestamp,config.fault_mode,config.demand_factor)
    recent_rows=db.execute(select(Anomaly.timestamp,Anomaly.parameter).where(Anomaly.acknowledged==False,Anomaly.timestamp<timestamp).order_by(Anomaly.timestamp.desc()).limit(100)).all()
    recent=len(set(recent_rows))
    monitoring=assess_power(power,timestamp,recent_events=recent)
    recommendations=build_recommendations(frame,result,monitoring,config)
    weather=frame.iloc[0].to_dict(); weather={k:float(weather[k]) for k in ['irradiance','temperature','humidity','cloud_cover','wind_speed','wind_direction','air_density']}
    current={'timestamp':timestamp.isoformat(),**first,**power,'energy_kwh':result['summary']['initial_energy_kwh'],'initial_soc':100*result['summary']['initial_energy_kwh']/config.battery.capacity_kwh,'weather':weather,'monitoring_status':'Abnormal' if monitoring['anomalies'] else 'Normal','active_anomalies':len(monitoring['anomalies']),'grid_status':'Supply shortfall' if first['unserved_kw']>.01 else ('Islanded' if not config.grid_available else 'Balanced')}
    return {'run_id':None,'source':DATA_NOTICE,'site':SITE,'timezone':TIMEZONE,'config':config.model_dump(),'current':current,'forecast':frame.to_dict('records'),'optimization':result,'monitoring':monitoring,'recommendations':recommendations,'weather':weather}

def run_simulation(db,config,reset_clock=False):
    from app.config import SIM_START
    state=get_state(db); timestamp=pd.Timestamp(SIM_START if reset_clock or not state else state['timestamp']).to_pydatetime()
    energy=config.battery.capacity_kwh*config.battery.initial_soc/100
    payload=execute(db,config,timestamp,energy)
    run_id=persist_run(db,payload,config,timestamp,energy)
    payload['run_id']=run_id
    saved=db.scalars(select(Anomaly).where(Anomaly.run_id==run_id).order_by(Anomaly.id)).all()
    for a,item in zip(payload['monitoring']['anomalies'],saved): a['id']=item.id
    logger.info('Simulation %s scenario=%s objective=%.4f',run_id,config.scenario,payload['optimization']['summary']['objective_value'])
    return payload

def current_payload(db):
    state=get_state(db)
    if not state: raise RuntimeError('Simulation not initialized')
    config=SimulationConfig.model_validate(state['config'])
    payload=execute(db,config,pd.Timestamp(state['timestamp']).to_pydatetime(),state['energy_kwh'])
    payload['run_id']=state['run_id']
    saved=db.scalars(select(Anomaly).where(Anomaly.run_id==state['run_id']).order_by(Anomaly.id)).all()
    for a,item in zip(payload['monitoring']['anomalies'],saved): a['id']=item.id; a['acknowledged']=item.acknowledged
    return payload

def advance_simulation(db,hours=1):
    state=get_state(db)
    if not state: raise RuntimeError('Simulation not initialized')
    config=SimulationConfig.model_validate(state['config']); timestamp=pd.Timestamp(state['timestamp']); energy=state['energy_kwh']; realized=[]
    for i in range(hours):
        payload=execute(db,config,timestamp.to_pydatetime(),energy)
        plan=payload['optimization']['schedule'][0]
        w=weather_at(timestamp,config.model_dump()); d=demand_at(timestamp,w['temperature'],config.demand_factor)
        actual=settle_interval(w,d,plan,config,energy); energy=actual['energy_kwh']; realized.append(actual)
        # Replace the current forecast operating point with the simulated realization.
        from app.services.repository import insert_history
        insert_history(db,'generation',{**actual,'solar_predicted_kw':plan['solar_predicted_kw'],'wind_predicted_kw':plan['wind_predicted_kw'],'source':'synthetic-realization'})
        insert_history(db,'consumption',{**{k:actual[k] for k in ['residential_kw','commercial_kw','industrial_kw']},'timestamp':timestamp,'total_kw':actual['total_kw'],'predicted_kw':plan['demand_predicted_kw']})
        insert_history(db,'weather',{**w,'timestamp':timestamp})
        insert_history(db,'battery',{**actual,'timestamp':timestamp,'capacity_kwh':config.battery.capacity_kwh})
        insert_history(db,'grid',{**actual,'timestamp':timestamp,'available':config.grid_available,'status':'Supply shortfall' if actual['unserved_kw']>.01 else 'Balanced'})
        m=electrical_measurements(actual['served_kw'],timestamp.to_pydatetime(),config.fault_mode,config.demand_factor)
        insert_history(db,'power',{**m,'timestamp':timestamp})
        timestamp=timestamp+pd.Timedelta(hours=1)
    payload=execute(db,config,timestamp.to_pydatetime(),energy)
    run_id=persist_run(db,payload,config,timestamp.to_pydatetime(),energy)
    db.commit()
    result=dashboard(db); result['realized_intervals']=len(realized)
    return result

def initialize(db):
    from app.database.session import Base,engine
    Base.metadata.create_all(engine); seed_history(db)
    if not get_state(db): run_simulation(db,SimulationConfig())

def dashboard(db):
    payload=current_payload(db); hist=history_frame(db,168)
    if len(hist):
        recent=hist.tail(24)
        payload['history']=hist.to_dict('records')
        payload['daily']={k:float(recent[k].sum()) for k in ['solar_kw','wind_kw','total_kw','import_kw','export_kw'] if k in recent}
    else: payload['history']=[]; payload['daily']={}
    return payload
