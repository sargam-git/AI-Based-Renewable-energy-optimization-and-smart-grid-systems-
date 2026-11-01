"""Hybrid ML abnormality detection and transparent electrical rule checks."""
import numpy as np
import pandas as pd
from app.ml.predictor import load_model

def assess_power(m,timestamp,run_id=None,recent_events=0):
    bundle=load_model('anomaly'); frame=pd.DataFrame([m])[bundle['features']]
    score=float(-bundle['model'].score_samples(frame)[0]); flagged=bool(bundle['model'].predict(frame)[0]==-1)
    normalized=float(np.clip((score-bundle['score_low'])/(bundle['score_high']-bundle['score_low']),0,1))
    anomalies=[]
    def add(parameter,severity,value,lo,hi,action):
        anomalies.append({'timestamp':timestamp,'equipment_id':'TX-01' if parameter in ['transformer_loading','current'] else 'BUS-01','parameter':parameter,'severity':severity,'score':normalized,'message':f'{parameter.replace("_"," ").title()} is {value:.2f}; expected operating band {lo}–{hi}.','action':action,'acknowledged':False,'run_id':run_id})
    if not 394.25<=m['voltage']<=435.75:
        add('voltage','critical' if not 373.5<=m['voltage']<=456.5 else 'warning',m['voltage'],394.25,435.75,'Ask a qualified operator to investigate the voltage regulator, tap setting and feeder connections. Simulation only.')
    if not 49.7<=m['frequency']<=50.3:
        add('frequency','critical',m['frequency'],49.7,50.3,'Investigate supply-demand imbalance and generating-unit response. Actual protection must use certified relays.')
    if m['transformer_loading']>100:
        add('transformer_loading','critical',m['transformer_loading'],0,100,'Reduce non-critical simulated load and inspect transformer cooling before any real equipment operation.')
    elif m['transformer_loading']>85:
        add('transformer_loading','warning',m['transformer_loading'],0,85,'Review forecast peak loading and shift flexible demand away from this interval.')
    if m['power_factor']<.9:
        add('power_factor','warning',m['power_factor'],.9,1,'Investigate reactive power compensation and load composition; do not switch real capacitors from this demo.')
    if flagged and not anomalies:
        add('multivariate_pattern','warning',score,bundle['score_low'],bundle['score_high'],'Inspect the combined voltage, current, frequency, power factor and loading trend; this is an unsupervised abnormality alert.')
    stress=max(np.clip((m['transformer_loading']-65)/50,0,1),np.clip(abs(m['voltage']/415-1)/.18,0,1),np.clip(abs(m['frequency']-50)/.85,0,1),np.clip((.94-m['power_factor'])/.16,0,1))
    risk=float(np.clip(100*(.5*stress+.32*normalized+.18*min(recent_events/5,1)),0,100))
    priority='High' if risk>=65 else ('Medium' if risk>=35 else 'Low')
    health=[{'timestamp':timestamp,'equipment_id':'TX-01','name':'Main transformer','failure_risk':risk,'health_score':100-risk,'priority':priority,'recommendation':'Inspect loading, cooling and connections during the next safe maintenance window.' if risk>=35 else 'Continue trend monitoring; no abnormal stress indicated.','run_id':run_id}]
    for eid,name,base in [('LN-01','Distribution feeder',.65),('PV-01','Solar inverters',.4),('WT-01','Wind turbine drivetrain',.5)]:
        rr=risk*base; p='High' if rr>=65 else ('Medium' if rr>=35 else 'Low')
        health.append({'timestamp':timestamp,'equipment_id':eid,'name':name,'failure_risk':rr,'health_score':100-rr,'priority':p,'recommendation':'Inspect feeder current and voltage-drop trends.' if eid=='LN-01' and rr>=35 else ('Review generation-equipment operating trends.' if rr>=35 else 'Continue condition monitoring.'),'run_id':run_id})
    return {'measurement':{**m,'timestamp':timestamp.isoformat()}, 'anomalies':anomalies,'equipment':health,'ml_score':score,'ml_abnormal':flagged,'risk_method':'Heuristic 0–100 condition-risk index, NOT a calibrated failure probability: 50% operating stress + 32% normalized Isolation Forest score + 18% recent-event frequency (distinct prior timestamp/parameter pairs, up to five).'}
