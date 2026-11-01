"""Deterministic synthetic weather and equipment data, never a live weather product."""
import numpy as np
import pandas as pd
from datetime import timedelta
from app.config import SOLAR_CAPACITY, WIND_CAPACITY, SIM_START
from app.simulation.physics import solar_power, wind_power, electrical_measurements

def weather_at(timestamp, scenario=None):
    timestamp=pd.Timestamp(timestamp)
    origin=pd.Timestamp(SIM_START).normalize()
    day=(timestamp.normalize()-origin).days
    hour=timestamp.hour+timestamp.minute/60
    doy=timestamp.dayofyear
    rng=np.random.default_rng(20261101+int(day)*31)
    season=np.sin(2*np.pi*(doy-100)/365)
    daylight=max(0,np.sin(np.pi*(hour-6)/12))
    cloud=float(np.clip(34+25*np.sin(day*.57)+15*np.cos(hour*.45+day)+rng.normal(0,6),0,100))
    irradiance=float(900*daylight**1.35*(1-.67*cloud/100))
    temperature=float(24+5*season+6*np.sin(2*np.pi*(hour-9)/24)+2*np.sin(day*.2)+rng.normal(0,.4))
    humidity=float(np.clip(58-15*np.sin(2*np.pi*(hour-9)/24)+15*cloud/100+rng.normal(0,3),15,98))
    speed=float(np.clip(5.9+2.5*np.sin(day*.33+hour*.21)+1.4*np.sin(hour*.63)+rng.normal(0,.55),0,24))
    direction=float((190+50*np.sin(day*.25)+hour*4)%360)
    density=float(101325/(287.05*(temperature+273.15))*0.94)
    w={'timestamp':timestamp,'irradiance':irradiance,'temperature':temperature,'humidity':humidity,'cloud_cover':cloud,'wind_speed':speed,'wind_direction':direction,'air_density':density}
    if scenario:
        peak=scenario.get('peak_irradiance',900)
        w['irradiance']=irradiance*peak/900
        if scenario.get('cloud_cover') is not None:
            ratio=(1-.67*scenario['cloud_cover']/100)/(1-.67*cloud/100)
            w['irradiance']*=ratio; w['cloud_cover']=scenario['cloud_cover']
            w['humidity']=float(np.clip(35+.55*scenario['cloud_cover'],15,98))
        if scenario.get('temperature') is not None:
            w['temperature']=scenario['temperature']
            w['air_density']=101325/(287.05*(w['temperature']+273.15))*.94
        if scenario.get('wind_speed') is not None: w['wind_speed']=scenario['wind_speed']
    return w

def demand_at(timestamp, temperature=28, factor=1):
    timestamp=pd.Timestamp(timestamp)
    h=timestamp.hour; weekend=timestamp.dayofweek>=5
    morning=np.exp(-((h-8)/2.6)**2); evening=np.exp(-((h-19)/2.9)**2)
    commercial=np.exp(-((h-13)/4.1)**2)
    residential=110+95*morning+135*evening
    business=45+(100 if not weekend else 50)*commercial
    industrial=125+35*(1 if 7<=h<=22 else 0)+12*np.sin(h*.55)
    cooling=max(0,temperature-26)*5
    values=np.array([residential+cooling*.5,business+cooling*.35,industrial+cooling*.15])*factor
    return {'residential_kw':float(values[0]),'commercial_kw':float(values[1]),'industrial_kw':float(values[2]),'total_kw':float(sum(values))}

def generate_dataset(days=120):
    end=pd.Timestamp(SIM_START)
    times=pd.date_range(end=end-timedelta(hours=1),periods=days*24,freq='h')
    rows=[]
    for i,t in enumerate(times):
        w=weather_at(t)
        rng=np.random.default_rng(70000+i)
        # Measurement noise, intermittent inverter clipping, and a conservative wind power curve.
        pv=float(solar_power(w['irradiance'],w['temperature']))
        wind=float(wind_power(w['wind_speed'],w['air_density']))
        pv=max(0,pv+rng.normal(0,4)*min(1,w['irradiance']/150))
        wind=max(0,wind+rng.normal(0,7)*min(1,w['wind_speed']/4))
        d=demand_at(t,w['temperature'])
        rows.append({**w,**d,'solar_kw':pv,'wind_kw':wind})
    df=pd.DataFrame(rows)
    df['month']=df.timestamp.dt.month; df['day']=df.timestamp.dt.day
    df['season']=df.month%12//3
    df['hour']=df.timestamp.dt.hour; df['day_of_week']=df.timestamp.dt.dayofweek
    # Reproducible missing sensor values and gross sensor spikes, cleaned by the pipeline.
    rng=np.random.default_rng(42)
    for col in ['irradiance','temperature','wind_speed','solar_kw','wind_kw','total_kw']:
        raw=df[col].copy(); mask=rng.random(len(df))<.008; raw.loc[mask]=np.nan
        spikes=rng.random(len(df))<.003; raw.loc[spikes]=raw.loc[spikes]*2.8+10
        df[col+'_raw']=raw
    # Deliberate, deterministic abnormal operating intervals for historical detection.
    fault=np.zeros(len(df),dtype=int)
    fault[(np.arange(len(df))%173).astype(int)==40]=1
    fault[(np.arange(len(df))%251).astype(int)==80]=2
    measurements=[]
    for i,r in df.iterrows():
        mode='voltage_sag' if fault[i]==1 else ('frequency_deviation' if fault[i]==2 else 'none')
        measurements.append(electrical_measurements(r.total_kw,r.timestamp,mode))
    return pd.concat([df,pd.DataFrame(measurements)],axis=1)

def add_features(df):
    d=df.sort_values('timestamp').copy()
    d['hour_sin']=np.sin(2*np.pi*d.hour/24); d['hour_cos']=np.cos(2*np.pi*d.hour/24)
    d['month_sin']=np.sin(2*np.pi*d.month/12); d['month_cos']=np.cos(2*np.pi*d.month/12)
    d['is_weekend']=(d.day_of_week>=5).astype(int)
    d['cooling_degree']=np.maximum(d.temperature-24,0)
    d['wind_cubic']=d.wind_speed**3
    for target,prefix in [('solar','solar'),('wind','wind'),('total','total')]:
        d[f'{prefix}_lag_1']=d[f'{target}_kw'].shift(1)
        d[f'{prefix}_lag_24']=d[f'{target}_kw'].shift(24)
    d['load_rolling_24']=d.total_kw.shift(1).rolling(24,min_periods=1).mean()
    return d

SOLAR_FEATURES=['irradiance','temperature','humidity','cloud_cover','wind_speed','hour','month','season','hour_sin','hour_cos','month_sin','month_cos']
WIND_FEATURES=['wind_speed','wind_direction','temperature','air_density','hour','month','wind_cubic','wind_lag_1','wind_lag_24']
LOAD_FEATURES=['temperature','humidity','cloud_cover','hour','day_of_week','month','season','hour_sin','hour_cos','is_weekend','cooling_degree','total_lag_1','total_lag_24','load_rolling_24']
FEATURES={'solar':SOLAR_FEATURES,'wind':WIND_FEATURES,'load':LOAD_FEATURES}
TARGETS={'solar':'solar_kw','wind':'wind_kw','load':'total_kw'}
CAPACITIES={'solar':SOLAR_CAPACITY,'wind':WIND_CAPACITY,'load':5000}
