"""Chronological validation, real model fitting, persistence, and held-out evaluation."""
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
from app.config import DATA, MODELS
from app.simulation.generator import generate_dataset, FEATURES, TARGETS
from app.ml.preprocessing import clean_dataset

ANOMALY_FEATURES=['voltage','current','frequency','power_factor','transformer_loading']

def metrics(actual,predicted):
    return {'mae':float(mean_absolute_error(actual,predicted)), 'rmse':float(np.sqrt(mean_squared_error(actual,predicted))), 'r2':float(r2_score(actual,predicted))}

def candidates():
    return {
      'Linear regression (Ridge)':Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler()),('model',Ridge(alpha=1))]),
      'Random Forest / depth 8':Pipeline([('impute',SimpleImputer(strategy='median')),('model',RandomForestRegressor(n_estimators=65,max_depth=8,min_samples_leaf=3,random_state=42,n_jobs=1))]),
      'Random Forest / depth 14':Pipeline([('impute',SimpleImputer(strategy='median')),('model',RandomForestRegressor(n_estimators=65,max_depth=14,min_samples_leaf=2,random_state=42,n_jobs=1))]),
      'XGBoost / depth 3':XGBRegressor(n_estimators=130,max_depth=3,learning_rate=.06,subsample=.9,reg_lambda=2,random_state=42,n_jobs=1,verbosity=0),
      'XGBoost / depth 5':XGBRegressor(n_estimators=130,max_depth=5,learning_rate=.06,subsample=.9,reg_lambda=2,random_state=42,n_jobs=1,verbosity=0)
    }

def train_all(days=120):
    raw=generate_dataset(days); raw.to_csv(DATA/'synthetic_raw.csv',index=False)
    d,report=clean_dataset(raw); d.to_csv(DATA/'synthetic_clean.csv',index=False)
    n=len(d); a=int(n*.70); b=int(n*.85)
    registry={'trained_at':datetime.now(timezone.utc).isoformat(),'dataset':'Deterministic synthetic Indore-inspired microgrid; NOT measured data','rows':n,'train_rows':a,'validation_rows':b-a,'test_rows':n-b,'split':{'train_start':str(d.timestamp.iloc[0]),'train_end':str(d.timestamp.iloc[a-1]),'validation_end':str(d.timestamp.iloc[b-1]),'test_end':str(d.timestamp.iloc[-1])},'preprocessing':report,'targets':{}}
    evaluation=[]; eda={}
    for target,col in TARGETS.items():
        usable=d.dropna(subset=[col]); train=usable.iloc[:a]; val=usable.iloc[a:b]; test=usable.iloc[b:]
        fitted=[]; comparisons=[]
        for name,model in candidates().items():
            model.fit(train[FEATURES[target]],train[col])
            pred=np.clip(model.predict(val[FEATURES[target]]),0,5000 if target=='load' else (650 if target=='solar' else 450))
            fitted.append((name,model)); comparisons.append({'model':name,**metrics(val[col],pred)})
        best=min(comparisons,key=lambda x:x['mae']); model=dict(fitted)[best['model']]
        # Select using validation only. Refit selected specification on train+validation.
        model.fit(usable.iloc[:b][FEATURES[target]],usable.iloc[:b][col])
        cap=5000 if target=='load' else (650 if target=='solar' else 450)
        pred=np.clip(model.predict(test[FEATURES[target]]),0,cap)
        result=metrics(test[col],pred); version=f'{target}-v1'
        joblib.dump({'model':model,'features':FEATURES[target],'cap':cap,'version':version},MODELS/f'{target}.joblib')
        registry['targets'][target]={'selected':best['model'],'version':version,'metrics':result,'validation_comparison':comparisons,'features':FEATURES[target],'target':col,'capacity_kw':cap,'naive_seasonal_mae':float(mean_absolute_error(test[col],test[f'{"total" if target=="load" else target}_lag_24']))}
        for t,y,yh in zip(test.timestamp,test[col],pred): evaluation.append({'timestamp':str(t),'target':target,'actual':float(y),'predicted':float(yh)})
        eda[target]={'mean_kw':float(d[col].mean()),'peak_kw':float(d[col].max()),'night_solar_mean_kw':float(d.loc[d.hour<6,'solar_kw'].mean()),'correlations':{f:float(d[[col,f]].corr().iloc[0,1]) for f in FEATURES[target][:5]}}
    normal=d.iloc[:a]; normal=normal[(normal.voltage.between(400,430))&(normal.frequency.between(49.8,50.2))&(normal.transformer_loading<90)]
    detector=Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler()),('model',IsolationForest(n_estimators=100,contamination=.02,random_state=42,n_jobs=1))])
    detector.fit(normal[ANOMALY_FEATURES])
    scores=-detector.score_samples(normal[ANOMALY_FEATURES])
    joblib.dump({'model':detector,'features':ANOMALY_FEATURES,'score_low':float(np.quantile(scores,.05)),'score_high':float(np.quantile(scores,.995))},MODELS/'anomaly.joblib')
    registry['anomaly']={'model':'Isolation Forest','training_rows':len(normal),'contamination':.02,'features':ANOMALY_FEATURES,'note':'Unsupervised abnormality score; not a failure probability. Complemented by explicit electrical operating bands.'}
    (MODELS/'registry.json').write_text(json.dumps(registry,indent=2))
    pd.DataFrame(evaluation).to_csv(DATA/'holdout_predictions.csv',index=False)
    (DATA/'eda.json').write_text(json.dumps(eda,indent=2))
    return registry

if __name__=='__main__':
    print(json.dumps(train_all(),indent=2))
