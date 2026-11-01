import { ArrowUpRight, ArrowDownRight, Info, X, Check, AlertTriangle, LoaderCircle } from 'lucide-react';
import { number } from '../services/api';
export function Card({ title, subtitle, action, children, className = '', ...props }) {
  return <section className={`panel ${className}`} {...props}>{(title || action) && <div className="panel-head"><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>{action}</div>}{children}</section>;
}
export function PageHeader({ eyebrow, title, description, children }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow || 'ENERGY INTELLIGENCE'}</div><h1>{title}</h1><p>{description}</p></div>{children && <div className="heading-actions">{children}</div>}</div>;
}
export function Badge({ children, tone = 'green', dot = true }) { return <span className={`badge ${tone}`}>{dot && <i />}{children}</span>; }
export function Button({ children, icon: Icon, variant = '', loading, className = '', ...props }) { return <button className={`button ${variant} ${className}`} {...props} disabled={props.disabled || loading}>{loading ? <LoaderCircle size={16} className="spin" /> : Icon && <Icon size={16} />}{children}</button>; }
export function Stat({ label, value, unit, icon: Icon, detail, trend, tone = 'green', spark }) {
  return <div className={`stat-card ${tone}`}><div className="stat-top"><span>{label}</span>{Icon && <div className="stat-icon"><Icon size={18} strokeWidth={1.7} /></div>}</div><div className="stat-value">{value}<span>{unit}</span></div><div className="stat-bottom">{trend === 'up' ? <ArrowUpRight size={14} /> : trend === 'down' ? <ArrowDownRight size={14} /> : <span className="tiny-dot" />}<span>{detail}</span>{spark && <div className="stat-spark">{spark}</div>}</div></div>;
}
export function Notice({ children, tone = 'info', icon: Icon }) { const I = Icon || (tone === 'warning' || tone === 'error' ? AlertTriangle : Info); return <div className={`notice ${tone}`}><I size={17} /><div>{children}</div></div>; }
export function Empty({ title = 'No events to display', text = 'New results will appear here when available.' }) { return <div className="empty"><Check size={26} /><strong>{title}</strong><p>{text}</p></div>; }
export function Loading() { return <div className="loading-state"><LoaderCircle size={28} className="spin" /><h3>Connecting the energy intelligence engine</h3><p>Loading forecasts, state, and optimized energy flows…</p></div>; }
export function Progress({ value, tone = 'green' }) { return <div className={`progress ${tone}`}><span style={{ width: `${Math.min(100, Math.max(0, value))}%` }} /></div>; }
export function KV({ label, children }) { return <div className="kv"><span>{label}</span><strong>{children}</strong></div>; }
export function DataTable({ columns, rows, empty = 'No records available', compact = false }) {
  return <div className={`table-scroll ${compact ? 'compact' : ''}`}><table><thead><tr>{columns.map(c => <th key={c.key} style={c.align ? { textAlign: c.align } : {}}>{c.label}</th>)}</tr></thead><tbody>{rows.length ? rows.map((r, i) => <tr key={r.id || r.timestamp || i}>{columns.map(c => <td key={c.key} style={c.align ? { textAlign: c.align } : {}}>{c.render ? c.render(r, i) : r[c.key] ?? '—'}</td>)}</tr>) : <tr><td colSpan={columns.length} className="table-empty">{empty}</td></tr>}</tbody></table></div>;
}
export function Modal({ title, children, onClose }) { return <div className="modal-backdrop" onClick={onClose}><section className="modal" role="dialog" aria-modal="true" aria-label={title} onClick={e => e.stopPropagation()}><div className="panel-head"><h3>{title}</h3><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={20} /></button></div>{children}</section></div>; }
export function BatteryGauge({ soc, energy, capacity, status }) {
  const r = 67, circ = 2 * Math.PI * r;
  return <div className="battery-gauge"><svg viewBox="0 0 170 170" role="img" aria-label={`Battery state of charge ${number(soc)} percent`}><circle cx="85" cy="85" r={r} fill="none" stroke="var(--line)" strokeWidth="10" /><circle cx="85" cy="85" r={r} fill="none" stroke="var(--green)" strokeWidth="10" strokeLinecap="round" strokeDasharray={`${circ * Math.min(100, soc || 0) / 100} ${circ}`} transform="rotate(-90 85 85)" /><text x="85" y="84" textAnchor="middle" className="gauge-number">{number(soc, 0)}<tspan fontSize="17">%</tspan></text><text x="85" y="106" textAnchor="middle" className="gauge-label">STATE OF CHARGE</text></svg><div className="gauge-info"><strong>{number(energy, 0)} <span>/ {number(capacity, 0)} kWh</span></strong><Badge tone={status === 'Discharging' ? 'amber' : 'green'}>{status || 'Ready'}</Badge></div></div>;
}
