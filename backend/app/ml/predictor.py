from functools import lru_cache
import joblib
import numpy as np
import pandas as pd
from app.config import MODELS, SOLAR_CAPACITY, WIND_CAPACITY
from app.simulation.generator import weather_at, demand_at, FEATURES
from app.simulation.physics import solar_power, wind_power
from app.ml.preprocessing import prepare_upload

@lru_cache(maxsize=8)
def load_model(target):
    path=MODELS/f'{target}.joblib'
    if not path.exists(): raise RuntimeError('Models are not trained. Run python -m app.cli prepare first.')
    return joblib.load(path)

def predict_frame(target,frame):
    bundle=load_model(target)
    pred=bundle['model'].predict(frame[bundle['features']])
    return np.clip(np.nan_to_num(pred,nan=0),0,bundle['cap'])

def forecast(config, start, initial_energy=None, history=None):
    """Recursive one-step and 24-hour lags; future observed targets are never used."""
    c=config.model_dump() if hasattr(config,'model_dump') else config
    times=pd.date_range(start,periods=c['horizon'],freq='h')
    if history is None:
        previous=[]
        for i in range(48,0,-1):
            ts=start-pd.Timedelta(hours=i); w=weather_at(ts); d=demand_at(ts,w['temperature'])
            previous.append({**w,**d,'solar_kw':float(solar_power(w['irradiance'],w['temperature'])),'wind_kw':float(wind_power(w['wind_speed'],w['air_density']))})
        past=pd.DataFrame(previous)
    else: past=history
    past=past.sort_values('timestamp')
    rows=[]
    for t in times:
        w=weather_at(t,c); d=demand_at(t,w['temperature'],c['demand_factor'])
        rows.append({**w,**d,'hour':t.hour,'month':t.month,'day_of_week':t.dayofweek,'season':t.month%12//3})
    future=pd.DataFrame(rows)
    future['hour_sin']=np.sin(2*np.pi*future.hour/24); future['hour_cos']=np.cos(2*np.pi*future.hour/24)
    future['month_sin']=np.sin(2*np.pi*future.month/12); future['month_cos']=np.cos(2*np.pi*future.month/12)
    future['is_weekend']=(future.day_of_week>=5).astype(int); future['cooling_degree']=np.maximum(future.temperature-24,0); future['wind_cubic']=future.wind_speed**3
    for target,prefix,cap in [('solar','solar',SOLAR_CAPACITY),('wind','wind',WIND_CAPACITY),('load','total',5000)]:
        values=list(past[f'{prefix}_kw'].tail(48))
        if len(values)<24: values=[0]*(24-len(values))+values
        predictions=[]
        bundle=load_model(target)
        for i,r in future.iterrows():
            row=r.to_dict(); row[f'{prefix}_lag_1']=values[-1]; row[f'{prefix}_lag_24']=values[-24]
            row['load_rolling_24']=np.mean(values[-24:])
            value=float(np.clip(bundle['model'].predict(pd.DataFrame([row])[bundle['features']])[0],0,cap))
            predictions.append(value); values.append(value)
        future[f'{target}_predicted_kw']=predictions
    # The fitted model forecasts the normal operating profile. A what-if demand
    # multiplier is an explicit scenario stress applied after ML inference, not
    # a weather feature the model was trained to understand. Apply it equally to
    # the total and its sectors so a 1.65x scenario really increases demand 65%.
    future['total_predicted_kw']=future.load_predicted_kw*c['demand_factor']
    for sector in ['residential','commercial','industrial']:
        future[sector+'_kw']=future[sector+'_kw']*c['demand_factor']
    future['demand_scenario_multiplier']=c['demand_factor']
    # Keep consumer allocation consistent with the stressed forecast total.
    raw_total=future[['residential_kw','commercial_kw','industrial_kw']].sum(axis=1)
    for sector in ['residential','commercial','industrial']:
        future[sector+'_kw']=future[sector+'_kw']*future.total_predicted_kw/raw_total.replace(0,1)
    future['renewable_predicted_kw']=future.solar_predicted_kw+future.wind_predicted_kw
    future['net_kw']=future.renewable_predicted_kw-future.total_predicted_kw
    return future

def upload_predictions(records,target):
    frame=prepare_upload(records,target); predictions=predict_frame(target,frame)
    output=frame[['timestamp']].copy(); output['target']=target; output['predicted_kw']=predictions
    col={'solar':'solar_kw','wind':'wind_kw','load':'total_kw'}[target]
    output['actual_kw']=frame[col]
    return output
