"""All suggestions are derived from the current forecast, state and optimizer solution."""
import pandas as pd

def build_recommendations(frame,result,monitoring,config):
    s=pd.DataFrame(result['schedule']); summary=result['summary']; out=[]
    def add(kind,title,detail,priority='info',saving=None):
        item={'id':kind,'title':title,'detail':detail,'priority':priority}
        if saving is not None: item['estimated_saving_usd']=round(saving,2)
        out.append(item)
    charge=s[s.charge_kw>.01]; discharge=s[s.discharge_kw>.01]
    if len(charge):
        h=', '.join(pd.to_datetime(charge.timestamp).dt.strftime('%H:%M').head(5))
        add('solar-charge','Store the renewable surplus',f"The optimizer charges {summary['charged_kwh']:.1f} kWh over {len(charge)} hour(s), including {h}. This respects the {config.battery.max_soc:g}% SOC ceiling and {config.battery.max_charge_kw:g} kW limit.")
    if len(discharge):
        saving=float((discharge.discharge_kw*discharge.tariff).sum()-(discharge.discharge_kw*config.degradation_cost).sum())
        add('battery-shift','Use storage instead of peak imports',f"Discharge {summary['discharged_kwh']:.1f} kWh across {len(discharge)} interval(s), starting at {pd.Timestamp(discharge.iloc[0].timestamp).strftime('%H:%M')}. Displaced import value minus throughput cost is estimated below.",saving=saving)
    deficit=s[s.unserved_kw>.01]
    if len(deficit):
        add('reliability','Supply shortfall requires attention',f"{summary['unserved_kwh']:.1f} kWh cannot be served in {len(deficit)} interval(s); maximum shortfall {deficit.unserved_kw.max():.1f} kW. Review grid availability, import limits and flexible demand. Battery safety limits are never bypassed.",'critical')
    elif summary['import_kwh']>0:
        peak=s.loc[s.import_kw.idxmax()]
        add('grid-peak','Plan for the largest grid import',f"The largest import is {peak.import_kw:.1f} kW at {pd.Timestamp(peak.timestamp).strftime('%H:%M')}, with forecast demand {peak.demand_predicted_kw:.1f} kW. The plan stays inside the {config.grid_import_limit_kw:g} kW connection limit.")
    if summary['curtailed_kwh']>.1:
        add('curtailment','Recover otherwise-unused generation',f"{summary['curtailed_kwh']:.1f} kWh is curtailed. Surplus beyond battery/export constraints cannot be used. Evaluate permissible export or flexible daytime consumption.",'warning')
    if frame.cloud_cover.mean()>65:
        add('weather','Prepare for cloud-limited solar output',f"Mean forecast cloud cover is {frame.cloud_cover.mean():.0f}%. Solar contributes {summary['solar_kwh']:.1f} kWh of the {summary['generation_kwh']:.1f} kWh renewable forecast. Check storage and backup requirements.",'warning')
    if len(s)>3:
        worst=s.loc[s.net_cost_idx if 'net_cost_idx' in s else (s.import_kw*s.tariff).idxmax()]; best=s.loc[(s.renewable_predicted_kw-s.demand_predicted_kw).idxmax()]
        surplus=best.renewable_predicted_kw-best.demand_predicted_kw
        if surplus>5 and worst.import_kw>5:
            shift=min(.15*worst.demand_predicted_kw,surplus,worst.import_kw)
            add('flexible-load','Shift flexible consumption into the surplus window',f"Move up to {shift:.1f} kW of flexible load from {pd.Timestamp(worst.timestamp).strftime('%H:%M')} to {pd.Timestamp(best.timestamp).strftime('%H:%M')}. This is a suggestion, not an included optimization decision; rerun with an adjusted demand profile to validate it.")
    for a in monitoring['anomalies']:
        add('inspect-'+a['parameter'],'Inspect '+a['parameter'].replace('_',' '),a['action'],'critical' if a['severity']=='critical' else 'warning')
    if not out: add('balanced','The present plan needs no intervention',f"Forecast demand is fully served with {summary['import_kwh']:.1f} kWh import and {summary['curtailed_kwh']:.1f} kWh curtailment. Maintain the current schedule and monitor forecast changes.")
    return out
