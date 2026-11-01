from datetime import datetime, timedelta
import json
import uuid
import pandas as pd
from sqlalchemy import select, delete
from app.models.records import *
from app.config import DATA

def get_state(db):
    row=db.get(Configuration,'simulation')
    return row.value if row else None

def save_state(db,value):
    row=db.get(Configuration,'simulation')
    if row: row.value=value; row.updated_at=datetime.utcnow()
    else: db.add(Configuration(key='simulation',value=value,updated_at=datetime.utcnow()))

def insert_history(db,kind,row):
    """One actual/simulated realization per timestamp, not each forecast revision."""
    model={'generation':GenerationRecord,'consumption':ConsumptionRecord,'weather':WeatherRecord,'power':PowerMeasurement,'battery':BatteryStatus,'grid':GridCondition}[kind]
    ts=pd.Timestamp(row['timestamp']).to_pydatetime()
    existing=db.scalars(select(model).where(model.timestamp==ts)).first()
    clean={k:v for k,v in row.items() if k in model.__table__.columns and k not in ['id','timestamp']}
    if existing:
        for k,v in clean.items(): setattr(existing,k,v)
    else: db.add(model(timestamp=ts,**clean))

def persist_run(db, payload, config, timestamp, energy, previous_history=None, persist_forecast=True):
    payload={**payload,'result':payload['optimization']}
    run_id=str(uuid.uuid4()); now=datetime.utcnow(); summary=payload['result']['summary']
    run=Run(id=run_id,created_at=now,scenario=config.scenario,config=config.model_dump(),summary=summary,schedule=payload['result']['schedule'])
    db.add(run); db.flush()
    first=payload['result']['schedule'][0]
    # Forecast revisions kept separately from unique historical actual realizations.
    if persist_forecast:
        for row in payload['result']['schedule']:
            ts=pd.Timestamp(row['timestamp']).to_pydatetime()
            for target,key in [('solar','solar_predicted_kw'),('wind','wind_predicted_kw'),('load','demand_predicted_kw')]:
                db.add(Prediction(timestamp=ts,target=target,predicted=row[key],model_version=target+'-v1',run_id=run_id,source='simulation'))
            db.add(OptimizationResult(run_id=run_id,timestamp=ts,status=payload['result']['status'],objective_value=summary['objective_value'],decision=row))
    m=payload['monitoring']['measurement']
    actual={'timestamp':timestamp,'solar_kw':first['solar_predicted_kw'],'wind_kw':first['wind_predicted_kw'],'solar_predicted_kw':first['solar_predicted_kw'],'wind_predicted_kw':first['wind_predicted_kw'],'source':'simulation-forecast','run_id':run_id}
    # These are current predicted operating values, never labelled hardware actuals.
    insert_history(db,'generation',actual)
    insert_history(db,'consumption',{**{k:first[k] for k in ['residential_kw','commercial_kw','industrial_kw']},'timestamp':timestamp,'total_kw':first['demand_predicted_kw'],'predicted_kw':first['demand_predicted_kw'],'run_id':run_id})
    insert_history(db,'weather',{**payload['weather'],'timestamp':timestamp,'run_id':run_id})
    insert_history(db,'power',{**m,'run_id':run_id})
    insert_history(db,'battery',{'timestamp':timestamp,'energy_kwh':energy,'capacity_kwh':config.battery.capacity_kwh,'soc':100*energy/config.battery.capacity_kwh,'charge_kw':first['charge_kw'],'discharge_kw':first['discharge_kw'],'run_id':run_id})
    insert_history(db,'grid',{**{k:first[k] for k in ['import_kw','export_kw','served_kw','unserved_kw']},'timestamp':timestamp,'available':config.grid_available,'status':'Supply shortfall' if first['unserved_kw']>.01 else ('Grid unavailable' if not config.grid_available else 'Balanced'),'run_id':run_id})
    for a in payload['monitoring']['anomalies']:
        db.add(Anomaly(**{**a,'timestamp':timestamp,'run_id':run_id}))
    for h in payload['monitoring']['equipment']:
        db.add(EquipmentHealth(**{**{k:v for k,v in h.items() if k!='name'},'run_id':run_id}))
    save_state(db,{'config':config.model_dump(),'timestamp':timestamp.isoformat(),'energy_kwh':energy,'run_id':run_id})
    db.commit()
    return run_id

def history_frame(db,hours=168):
    latest=db.scalars(select(GenerationRecord).order_by(GenerationRecord.timestamp.desc()).limit(1)).first()
    end=latest.timestamp if latest else datetime.utcnow()
    records=db.scalars(select(GenerationRecord).where(GenerationRecord.timestamp>=end-timedelta(hours=hours)).order_by(GenerationRecord.timestamp)).all()
    out=[]
    for g in records:
        c=db.scalars(select(ConsumptionRecord).where(ConsumptionRecord.timestamp==g.timestamp)).first()
        w=db.scalars(select(WeatherRecord).where(WeatherRecord.timestamp==g.timestamp)).first()
        b=db.scalars(select(BatteryStatus).where(BatteryStatus.timestamp==g.timestamp)).first()
        grid=db.scalars(select(GridCondition).where(GridCondition.timestamp==g.timestamp)).first()
        row={'timestamp':g.timestamp,'solar_kw':g.solar_kw,'wind_kw':g.wind_kw,'solar_predicted_kw':g.solar_predicted_kw,'wind_predicted_kw':g.wind_predicted_kw,'source':g.source}
        for prefix,obj in [('load',c),('weather',w),('grid',grid)]:
            if obj:
                for col in obj.__table__.columns:
                    if col.name not in ['id','timestamp','run_id'] and col.name not in row: row[col.name]=getattr(obj,col.name)
        if b: row.update({'energy_kwh':b.energy_kwh,'soc':b.soc,'charge_kw':b.charge_kw,'discharge_kw':b.discharge_kw})
        from app.simulation.physics import solar_power, wind_power
        if not row.get('solar_kw'): row['solar_kw']=float(solar_power(row['irradiance'],row['temperature']))
        if not row.get('wind_kw'): row['wind_kw']=float(wind_power(row['wind_speed'],row['air_density']))
        row['total_predicted_kw']=row.get('predicted_kw')
        out.append(row)
    return pd.DataFrame(out)

def seed_history(db):
    if db.scalars(select(GenerationRecord).limit(1)).first(): return
    from app.simulation.generator import generate_dataset
    from app.simulation.physics import electrical_measurements,distribute
    from app.services.monitoring import assess_power
    data=generate_dataset(120).tail(24*35)
    evals=pd.read_csv(DATA/'holdout_predictions.csv') if (DATA/'holdout_predictions.csv').exists() else pd.DataFrame(columns=['timestamp','target','predicted'])
    evals['timestamp']=pd.to_datetime(evals.timestamp)
    pred={(str(r.timestamp),r.target):r.predicted for r in evals.itertuples()}
    energy=744.; c={'capacity_kwh':1200,'min_soc':15,'max_soc':95,'charge_efficiency':.95,'discharge_efficiency':.95,'max_charge_kw':300,'max_discharge_kw':300}
    for r in data.to_dict('records'):
        t=r['timestamp'].to_pydatetime(); renewable=r['solar_kw']+r['wind_kw']; demand=r['total_kw']
        desired_c=min(300,max(0,renewable-demand)); desired_d=min(300,max(0,demand-renewable))
        from app.simulation.physics import battery_step
        state=battery_step(energy,desired_c,desired_d,c); energy=state['energy_kwh']
        imp=max(0,demand-renewable-state['discharge_kw']); split=distribute(renewable,demand,state['discharge_kw'],imp)
        export=min(max(0,renewable-demand-state['charge_kw']),400)
        ts=str(r['timestamp'])
        insert_history(db,'generation',{'timestamp':t,'solar_kw':r['solar_kw'],'wind_kw':r['wind_kw'],'solar_predicted_kw':pred.get((ts,'solar'),0),'wind_predicted_kw':pred.get((ts,'wind'),0),'source':'synthetic'})
        insert_history(db,'consumption',{**{k:r[k] for k in ['residential_kw','commercial_kw','industrial_kw','total_kw']},'timestamp':t,'predicted_kw':pred.get((ts,'load'),0)})
        insert_history(db,'weather',{**{k:r[k] for k in ['irradiance','temperature','humidity','cloud_cover','wind_speed','wind_direction','air_density']},'timestamp':t})
        m=electrical_measurements(demand,t,'voltage_sag' if r['voltage']<390 else ('frequency_deviation' if r['frequency']<49.7 else 'none'))
        insert_history(db,'power',{**m,'timestamp':t})
        insert_history(db,'battery',{**state,'timestamp':t,'capacity_kwh':1200})
        insert_history(db,'grid',{**split,'timestamp':t,'import_kw':imp,'export_kw':export,'available':True,'status':'Balanced'})
        if r['voltage']<390 or r['frequency']<49.7:
            result=assess_power(m,t)
            for a in result['anomalies']: db.add(Anomaly(**{**a,'acknowledged':True,'note':'Historical synthetic event reviewed during initialization.'}))
            for h in result['equipment']: db.add(EquipmentHealth(**{k:v for k,v in h.items() if k!='name'}))
    db.add(MaintenanceRecord(created_at=datetime.utcnow(),equipment_id='TX-01',action='Initial simulated inspection: verify transformer cooling, connection tightness and loading trend. No physical inspection was performed.',status='planned'))
    db.commit()
