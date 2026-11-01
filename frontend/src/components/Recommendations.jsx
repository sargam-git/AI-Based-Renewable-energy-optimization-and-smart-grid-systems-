import { Sparkles, ArrowRight, BatteryCharging, Sun, ShieldAlert, MoveRight, Zap, CircleCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { money } from '../services/api';
export default function Recommendations({ items, limit }) {
  const shown = limit ? items.slice(0, limit) : items;
  return <div className="recommendations">{shown.map(r => { const Icon = r.priority === 'critical' ? ShieldAlert : r.id.includes('charge') ? BatteryCharging : r.id.includes('weather') ? Sun : r.id.includes('load') ? MoveRight : r.id === 'balanced' ? CircleCheck : Zap; return <article key={r.id} className={`recommendation ${r.priority}`}><div className="recommendation-icon"><Icon size={18} /></div><div><div className="recommendation-title"><h4>{r.title}</h4>{r.estimated_saving_usd !== undefined && <span className="saving-tag">{money(r.estimated_saving_usd)} value</span>}</div><p>{r.detail}</p></div></article>; })}</div>;
}
