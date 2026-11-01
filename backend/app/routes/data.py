from fastapi import APIRouter,Depends,UploadFile,File,Form,HTTPException,Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import timedelta
import io,json
import pandas as pd
import numpy as np
from app.database.session import get_db
from app.models.records import *
from app.ml.predictor import upload_predictions
from app.config import DATA,MODELS

router=APIRouter(tags=['Data and reports'])
@router.post('/upload',status_code=201)
async def upload(file:UploadFile=File(...),target:str=Form(...),db:Session=Depends(get_db)):
    if target not in ['solar','wind','load']: raise HTTPException(422,'Invalid prediction target')
    if not file.filename or not file.filename.lower().endswith('.csv'): raise HTTPException(422,'Upload a .csv file')
    content=await file.read()
    if len(content)>2_000_000: raise HTTPException(413,'CSV exceeds the 2 MB limit')
    try:
        frame=pd.read_csv(io.BytesIO(content))
        if not 1<=len(frame)<=5000: raise ValueError('CSV must have 1–5000 data rows')
        if len(frame.columns)>60: raise ValueError('Too many columns (maximum 60)')
        if frame.columns.duplicated().any(): raise ValueError('Duplicate column names')
        output=upload_predictions(frame.to_dict('records'),target)
    except (ValueError,pd.errors.ParserError,UnicodeDecodeError,KeyError,TypeError) as e: raise HTTPException(422,str(e))
    for r in output.to_dict('records'):
        db.add(Prediction(timestamp=r['timestamp'].to_pydatetime(),target=target,predicted=r['predicted_kw'],actual=None if pd.isna(r['actual_kw']) else r['actual_kw'],model_version=target+'-v1',source='csv-upload'))
    db.commit()
    valid=output.dropna(subset=['actual_kw']); metric=None
    if len(valid)>1:
        from app.ml.training import metrics
        metric=metrics(valid.actual_kw,valid.predicted_kw)
    output['timestamp']=output.timestamp.dt.strftime('%Y-%m-%dT%H:%M:%S')
    return {'rows':len(output),'target':target,'metrics':metric,'predictions':json.loads(output.head(500).to_json(orient='records')),'csv':output.to_csv(index=False),'notice':'Predictions use models trained on synthetic data. Compatible real-world data may require recalibration and retraining.'}
@router.get('/upload/template')
def template(target:str='solar'):
    if target not in ['solar','wind','load']: raise HTTPException(422,'Invalid target')
    from app.simulation.generator import weather_at,demand_at
    times=pd.date_range('2026-11-01',periods=48,freq='h'); rows=[]
    for t in times:
        w=weather_at(t); d=demand_at(t,w['temperature'])
        rows.append({**w,**d,'solar_kw':np.nan,'wind_kw':np.nan})
    csv=pd.DataFrame(rows).to_csv(index=False)
    return Response(csv,media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{target}-input-template.csv"'})
@router.get('/evaluation')
def evaluation():
    if not (DATA/'holdout_predictions.csv').exists(): raise HTTPException(404,'Train the models first')
    d=pd.read_csv(DATA/'holdout_predictions.csv')
    p=d.pivot_table(index='timestamp',columns='target',values=['actual','predicted'])
    rows=[]
    for t,r in p.iterrows():
        row={'timestamp':t}
        for target in ['solar','wind','load']:
            for kind in ['actual','predicted']: row[f'{target}_{kind}']=float(r[(kind,target)])
        rows.append(row)
    return {'notice':'Untouched chronological holdout. These predictions were made before any simulation; not live measurements.','rows':rows,'models':json.loads((MODELS/'registry.json').read_text())}
@router.get('/reports')
def report(period:str='daily',format:str='json',db:Session=Depends(get_db)):
    if period not in ['daily','weekly','monthly']: raise HTTPException(422,'period must be daily, weekly or monthly')
    if format not in ['json','csv']: raise HTTPException(422,'format must be json or csv')
    latest=db.scalars(select(GenerationRecord).order_by(GenerationRecord.timestamp.desc()).limit(1)).first()
    if not latest: raise HTTPException(404,'No history available')
    days={'daily':1,'weekly':7,'monthly':30}[period]; start=pd.Timestamp(latest.timestamp).normalize().to_pydatetime()-timedelta(days=days-1)
    generation=db.scalars(select(GenerationRecord).where(GenerationRecord.timestamp>=start).order_by(GenerationRecord.timestamp)).all()
    rows=[]
    run_configs={r.id:r.config for r in db.scalars(select(Run)).all()}
    for g in generation:
        c=db.scalars(select(ConsumptionRecord).where(ConsumptionRecord.timestamp==g.timestamp)).first()
        b=db.scalars(select(BatteryStatus).where(BatteryStatus.timestamp==g.timestamp)).first()
        grid=db.scalars(select(GridCondition).where(GridCondition.timestamp==g.timestamp)).first()
        rows.append({'timestamp':g.timestamp,'source':g.source,'solar_kwh':g.solar_kw,'wind_kwh':g.wind_kw,'renewable_kwh':g.solar_kw+g.wind_kw,'demand_kwh':c.total_kw if c else 0,'import_kwh':grid.import_kw if grid else 0,'export_kwh':grid.export_kw if grid else 0,'unserved_kwh':grid.unserved_kw if grid else 0,'battery_soc_pct':b.soc if b else 0,'charged_kwh':b.charge_kw if b else 0,'discharged_kwh':b.discharge_kw if b else 0,'estimated_carbon_avoided_kg':(g.solar_kw+g.wind_kw)*run_configs.get(g.run_id,{}).get('carbon_factor',.71)})
    d=pd.DataFrame(rows); d['date']=d.timestamp.dt.date.astype(str)
    sums=['solar_kwh','wind_kwh','renewable_kwh','demand_kwh','import_kwh','export_kwh','unserved_kwh','charged_kwh','discharged_kwh','estimated_carbon_avoided_kg']
    daily=d.groupby('date',as_index=False).agg({**{x:'sum' for x in sums},'battery_soc_pct':'mean'})
    daily['grid_dependency_pct']=100*daily.import_kwh/daily.demand_kwh.replace(0,np.nan)
    daily['renewable_coverage_pct']=100*daily.renewable_kwh/daily.demand_kwh.replace(0,np.nan)
    daily=daily.fillna(0)
    totals={x:float(daily[x].sum()) for x in sums}
    totals['grid_dependency_pct']=100*totals['import_kwh']/totals['demand_kwh'] if totals['demand_kwh'] else 0
    totals['renewable_coverage_pct']=100*totals['renewable_kwh']/totals['demand_kwh'] if totals['demand_kwh'] else 0
    result={'period':period,'days':days,'start':str(start),'end':str(latest.timestamp),'rows':json.loads(daily.to_json(orient='records')),'totals':totals,'interval_rows':len(d),'notice':'Hourly kW integrated over one hour. History contains synthetic actuals and explicitly marked forecast operating points. Carbon uses each recorded run’s configured emissions factor; seeded history defaults to 0.71 kg CO₂/kWh. Forecast revisions are not double counted.'}
    if format=='csv': return Response(daily.to_csv(index=False),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="heliogrid-{period}-report.csv"'})
    return result
@router.get('/database/summary')
def db_summary(db:Session=Depends(get_db)):
    from sqlalchemy import func
    tables=[GenerationRecord,ConsumptionRecord,WeatherRecord,PowerMeasurement,BatteryStatus,Prediction,OptimizationResult,GridCondition,Anomaly,EquipmentHealth,MaintenanceRecord,Configuration,Run]
    return {'tables':{m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in tables},'storage':'SQLite with WAL and foreign keys','persistent':True}
