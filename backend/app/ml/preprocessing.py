import pandas as pd
import numpy as np
from app.simulation.generator import add_features, FEATURES, TARGETS, CAPACITIES

def clean_dataset(raw):
    d=raw.copy(); report={}
    for target,col in TARGETS.items():
        source=col+'_raw' if col+'_raw' in d else col
        s=pd.to_numeric(d[source],errors='coerce')
        bad=~s.between(0,CAPACITIES[target])
        report[target]={'missing':int(s.isna().sum()),'invalid_or_outlier':int((bad&s.notna()).sum())}
        d[col]=s.mask(bad)
    for col in ['irradiance','temperature','humidity','cloud_cover','wind_speed','wind_direction','air_density']:
        source=col+'_raw' if col+'_raw' in d else col
        d[col]=pd.to_numeric(d[source],errors='coerce')
    bounds={'irradiance':(0,1400),'temperature':(-30,60),'humidity':(0,100),'cloud_cover':(0,100),'wind_speed':(0,40),'wind_direction':(0,360),'air_density':(.8,1.5)}
    for col,(lo,hi) in bounds.items():
        bad=~d[col].between(lo,hi)
        report[col]={'missing':int(d[col].isna().sum()),'invalid_or_outlier':int((bad&d[col].notna()).sum())}
        d[col]=d[col].mask(bad)
    # Interpolate only short sensor gaps; model pipelines contain TRAIN-fitted medians
    # for any remaining gaps, including gaps at the beginning of a series.
    for col in list(bounds)+list(TARGETS.values()):
        d[col]=d[col].interpolate(limit=2,limit_area='inside')
    d['timestamp']=pd.to_datetime(d.timestamp)
    d=d.sort_values('timestamp').drop_duplicates('timestamp')
    d['hour']=d.timestamp.dt.hour; d['month']=d.timestamp.dt.month
    d['day_of_week']=d.timestamp.dt.dayofweek; d['day']=d.timestamp.dt.day; d['season']=d.month%12//3
    d=add_features(d)
    return d,report

def prepare_upload(records,target):
    d=pd.DataFrame(records)
    if 'timestamp' not in d: raise ValueError('Required column: timestamp')
    d['timestamp']=pd.to_datetime(d.timestamp,errors='coerce')
    if d.timestamp.isna().any(): raise ValueError('Invalid or missing timestamp')
    if d.timestamp.duplicated().any(): raise ValueError('Duplicate timestamps are not supported')
    d=d.sort_values('timestamp').reset_index(drop=True)
    if len(d)>1 and not (d.timestamp.diff().dropna()==pd.Timedelta(hours=1)).all():
        raise ValueError('Uploads must contain consecutive hourly timestamps')
    requirements={'solar':['irradiance','temperature','humidity','cloud_cover','wind_speed'], 'wind':['wind_speed','wind_direction','temperature','air_density'], 'load':['temperature','humidity','cloud_cover']}
    needed=requirements[target]
    missing=[x for x in needed if x not in d]
    if missing: raise ValueError('Missing columns: '+', '.join(missing))
    for col in needed:
        d[col]=pd.to_numeric(d[col],errors='coerce')
        if d[col].isna().all(): raise ValueError(f'No valid numeric values in {col}')
        if np.isinf(d[col].to_numpy(dtype=float)).any(): raise ValueError(f'Infinite values are not allowed in {col}')
        limits={'irradiance':(0,1400),'temperature':(-30,60),'humidity':(0,100),'cloud_cover':(0,100),'wind_speed':(0,40),'wind_direction':(0,360),'air_density':(.8,1.5)}
        lo,hi=limits[col]
        valid=d[col].dropna()
        if not valid.between(lo,hi).all(): raise ValueError(f'{col} must be between {lo} and {hi}')
    d['hour']=d.timestamp.dt.hour; d['month']=d.timestamp.dt.month; d['day_of_week']=d.timestamp.dt.dayofweek; d['season']=d.month%12//3
    for t,c in TARGETS.items():
        if c not in d: d[c]=np.nan
        d[c]=pd.to_numeric(d[c],errors='coerce')
        values=d[c].dropna()
        if np.isinf(values.to_numpy(dtype=float)).any() or not values.between(0,CAPACITIES[t]).all():
            raise ValueError(f'{c} contains invalid actual values; expected 0–{CAPACITIES[t]} kW or blank')
    d=add_features(d)
    # Lag fallback is documented and uses only preceding rows, never future targets.
    prefix={'solar':'solar','wind':'wind','load':'total'}[target]
    for lag in [1,24]:
        col=f'{prefix}_lag_{lag}'
        if d[col].isna().all(): d[col]=0.0
    if target=='load': d['load_rolling_24']=d.total_kw.shift(1).rolling(24,min_periods=1).mean().fillna(0)
    return d
