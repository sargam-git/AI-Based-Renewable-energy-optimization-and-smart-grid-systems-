from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.session import get_db
from app.models.records import *
from app.schemas.energy import MaintenanceRequest,AcknowledgeRequest
from app.services.engine import current_payload
from app.simulation.physics import electrical_measurements

router=APIRouter(tags=['Monitoring and maintenance'])
def records(query,db):
    return [{c.name:getattr(row,c.name) for c in row.__table__.columns} for row in db.scalars(query).all()]
@router.get('/monitoring')
def monitoring(limit:int=48,db:Session=Depends(get_db)):
    if not 1<=limit<=1000: raise HTTPException(422,'limit must be 1–1000')
    p=current_payload(db); history=records(select(PowerMeasurement).order_by(PowerMeasurement.timestamp.desc()).limit(limit),db)
    return {**p['monitoring'],'current':p['current'],'history':history[::-1],'notice':'Simulated three-phase balance; voltage is line-to-line RMS. Software alerts do not replace protection relays.'}
@router.post('/monitoring/test')
def test_monitoring(voltage:float=415,frequency:float=50,loading:float=65,power_factor:float=.96):
    if not 200<=voltage<=600 or not 45<=frequency<=55 or not 0<=loading<=200 or not .5<=power_factor<=1: raise HTTPException(422,'Input outside safe simulation range')
    m=electrical_measurements(loading*10*power_factor,datetime.utcnow()); m.update(voltage=voltage,frequency=frequency,transformer_loading=loading,power_factor=power_factor)
    m['apparent_power']=loading*10; m['active_power']=m['apparent_power']*power_factor; m['current']=m['apparent_power']*1000/(3**.5*voltage); m['reactive_power']=m['apparent_power']*(1-power_factor**2)**.5
    from app.services.monitoring import assess_power
    return assess_power(m,datetime.utcnow())
@router.get('/anomalies')
def anomalies(db:Session=Depends(get_db)): return records(select(Anomaly).order_by(Anomaly.timestamp.desc()).limit(500),db)
@router.post('/anomalies/{item_id}/acknowledge')
def acknowledge(item_id:int,body:AcknowledgeRequest,db:Session=Depends(get_db)):
    a=db.get(Anomaly,item_id)
    if not a: raise HTTPException(404,'Anomaly not found')
    a.acknowledged=True; a.note=body.note; db.commit(); return {'id':a.id,'acknowledged':True,'note':a.note}
@router.get('/equipment')
def equipment(db:Session=Depends(get_db)):
    p=current_payload(db); items=[]
    for h in p['monitoring']['equipment']:
        last=db.scalars(select(MaintenanceRecord).where(MaintenanceRecord.equipment_id==h['equipment_id']).order_by(MaintenanceRecord.created_at.desc()).limit(1)).first()
        items.append({**h,'last_maintenance':last.created_at if last else None,'maintenance_status':last.status if last else None})
    return {'items':items,'method':p['monitoring']['risk_method'],'source':p['source']}
@router.get('/maintenance')
def maintenance(db:Session=Depends(get_db)): return records(select(MaintenanceRecord).order_by(MaintenanceRecord.created_at.desc()),db)
@router.post('/maintenance',status_code=201)
def create_maintenance(body:MaintenanceRequest,db:Session=Depends(get_db)):
    if body.equipment_id not in ['TX-01','LN-01','PV-01','WT-01','BUS-01']: raise HTTPException(422,'Unknown simulated equipment')
    m=MaintenanceRecord(created_at=datetime.utcnow(),**body.model_dump()); db.add(m); db.commit(); return {'id':m.id,**body.model_dump()}
@router.patch('/maintenance/{item_id}')
def complete_maintenance(item_id:int,db:Session=Depends(get_db)):
    m=db.get(MaintenanceRecord,item_id)
    if not m: raise HTTPException(404,'Maintenance record not found')
    m.status='completed'; db.commit(); return {'id':m.id,'status':m.status}
@router.get('/history/{kind}')
def history(kind:str,limit:int=168,db:Session=Depends(get_db)):
    mapping={'generation':GenerationRecord,'consumption':ConsumptionRecord,'weather':WeatherRecord,'power':PowerMeasurement,'battery':BatteryStatus,'predictions':Prediction,'optimization':OptimizationResult,'grid':GridCondition,'simulations':Run,'equipment':EquipmentHealth}
    if kind not in mapping or not 1<=limit<=5000: raise HTTPException(422,'Unknown history kind or invalid limit')
    model=mapping[kind]; return records(select(model).order_by(model.timestamp.desc() if hasattr(model,'timestamp') else model.created_at.desc()).limit(limit),db)
