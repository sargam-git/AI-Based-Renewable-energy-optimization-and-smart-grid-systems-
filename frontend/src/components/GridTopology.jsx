import { useState } from 'react';
import { Sun, Wind, BatteryCharging, Network, Home, Building2, Factory, PlugZap, ArrowRight, Info } from 'lucide-react';
import { number } from '../services/api';
import { Badge, KV } from './UI';
export default function GridTopology({ current, config, compact = false }) {
  const [selected, setSelected] = useState('bus');
  const batteryFlow = current.discharge_kw - current.charge_kw;
  const gridFlow = current.import_kw - current.export_kw;
  const nodes = [
    { id: 'solar', label: 'Solar array', sub: '650 kW installed', value: current.solar_predicted_kw, icon: Sun, color: 'solar', x: 13, y: 18 },
    { id: 'wind', label: 'Wind turbine', sub: '450 kW installed', value: current.wind_predicted_kw, icon: Wind, color: 'wind', x: 13, y: 50 },
    { id: 'battery', label: 'Battery storage', sub: `${number(config.battery.capacity_kwh, 0)} kWh capacity`, value: Math.abs(batteryFlow), icon: BatteryCharging, color: 'green', x: 13, y: 82 },
    { id: 'residential', label: 'Residential', sub: 'Priority: essential', value: current.residential_served_kw ?? current.residential_kw * (current.served_kw / Math.max(current.demand_predicted_kw, 1)), icon: Home, color: 'green', x: 87, y: 18 },
    { id: 'commercial', label: 'Commercial', sub: 'Flexible demand', value: current.commercial_served_kw ?? current.commercial_kw * (current.served_kw / Math.max(current.demand_predicted_kw, 1)), icon: Building2, color: 'wind', x: 87, y: 50 },
    { id: 'industrial', label: 'Industrial', sub: 'Base + flexible load', value: current.industrial_served_kw ?? current.industrial_kw * (current.served_kw / Math.max(current.demand_predicted_kw, 1)), icon: Factory, color: 'load', x: 87, y: 82 },
    { id: 'grid', label: 'Utility grid', sub: config.grid_available ? (gridFlow >= 0 ? 'Import connection' : 'Export connection') : 'Grid unavailable', value: Math.abs(gridFlow), icon: PlugZap, color: 'load', x: 50, y: 88 }
  ];
  const node = nodes.find(n => n.id === selected);
  const flowText = selected === 'battery' ? (batteryFlow >= 0 ? 'To microgrid' : 'From renewables') : selected === 'grid' ? (gridFlow >= 0 ? 'To microgrid' : 'To utility') : ['solar', 'wind'].includes(selected) ? 'To microgrid' : 'From microgrid';
  return <div className={`topology ${compact ? 'compact-topology' : ''}`}>
    <div className="topology-canvas"><svg className="flow-lines" viewBox="0 0 1000 400" preserveAspectRatio="none" aria-hidden="true"><defs><pattern id="grid-dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="var(--line)" /></pattern></defs><rect width="1000" height="400" fill="url(#grid-dots)" />
      <path d="M 230 72 H 350 Q 370 72 370 92 V 175 H 500" className="flow-base" /><path d="M 230 200 H 500" className="flow-base" /><path d="M 230 328 H 350 Q 370 328 370 308 V 225 H 500" className="flow-base" /><path d="M 500 175 H 630 Q 650 175 650 155 V 72 H 770" className="flow-base" /><path d="M 500 200 H 770" className="flow-base" /><path d="M 500 225 H 630 Q 650 225 650 245 V 328 H 770" className="flow-base" /><path d="M 500 225 V 310" className="flow-base" />
      {current.solar_predicted_kw > .1 && <path d="M 230 72 H 350 Q 370 72 370 92 V 175 H 500" className="flow-animated solar-flow" />}
      {current.wind_predicted_kw > .1 && <path d="M 230 200 H 500" className="flow-animated wind-flow" />}
      {Math.abs(batteryFlow) > .1 && <path d="M 230 328 H 350 Q 370 328 370 308 V 225 H 500" className={`flow-animated green-flow ${batteryFlow < 0 ? 'reverse' : ''}`} />}
      {current.served_kw > .1 && <><path d="M 500 175 H 630 Q 650 175 650 155 V 72 H 770" className="flow-animated green-flow" /><path d="M 500 200 H 770" className="flow-animated wind-flow" /><path d="M 500 225 H 630 Q 650 225 650 245 V 328 H 770" className="flow-animated load-flow" /></>}
      {Math.abs(gridFlow) > .1 && <path d="M 500 225 V 310" className={`flow-animated load-flow ${gridFlow > 0 ? 'reverse' : ''}`} />}
    </svg>
    {nodes.map(n => <button key={n.id} className={`grid-node ${n.color} ${selected === n.id ? 'selected' : ''}`} style={{ left: `${n.x}%`, top: `${n.y}%` }} onClick={() => setSelected(n.id)} aria-label={`Inspect ${n.label}`}><span className="node-icon"><n.icon size={compact ? 18 : 21} strokeWidth={1.6} /></span><strong>{n.label}</strong><span className="node-value">{number(n.value, 1)} <small>kW</small></span>{!compact && <small>{n.sub}</small>}</button>)}
    <button className={`grid-bus ${selected === 'bus' ? 'selected' : ''}`} onClick={() => setSelected('bus')} aria-label="Inspect microgrid bus"><div className="bus-symbol"><Network size={27} strokeWidth={1.5} /></div><strong>Microgrid bus</strong><span>Nominal 415 V · 50 Hz</span><Badge tone={current.unserved_kw > .01 ? 'red' : 'green'}>{current.unserved_kw > .01 ? 'Supply deficit' : 'Balanced'}</Badge></button>
    <span className="flow-label solar-label">{number(current.solar_predicted_kw, 0)} kW</span><span className="flow-label wind-label">{number(current.wind_predicted_kw, 0)} kW</span><span className="flow-label battery-label">{number(Math.abs(batteryFlow), 0)} kW</span><span className="flow-label utility-label">{number(Math.abs(gridFlow), 0)} kW</span>
    </div>
    <div className="topology-detail"><div><Info size={15} /><strong>{node?.label || 'Microgrid bus'}</strong><span>{node ? flowText : 'Supply = demand + losses'}</span></div><strong>{node ? number(node.value) + ' kW' : number(current.served_kw) + ' kW served'}</strong><span className="topology-hint">Select a node to inspect · Flows follow backend dispatch</span></div>
  </div>;
}
