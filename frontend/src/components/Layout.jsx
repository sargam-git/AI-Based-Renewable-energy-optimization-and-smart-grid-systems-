import { useState, useEffect } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Sun, ChartNoAxesCombined, BatteryCharging, Network, Activity, ShieldCheck, Sparkles, SlidersHorizontal, Files, Zap, ChevronRight, ArrowUpRight, Bell, Moon, RefreshCw, Play, Pause, Menu, X, CircleHelp, CheckCircle2, AlertCircle, Radio, FlaskConical, ChevronDown } from 'lucide-react';
import { useGrid } from '../hooks/GridContext';
import { Badge, Button } from './UI';
export const navigation = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/renewables', label: 'Renewable analytics', icon: Sun },
  { to: '/load', label: 'Load forecasting', icon: ChartNoAxesCombined },
  { to: '/battery', label: 'Battery storage', icon: BatteryCharging },
  { to: '/grid', label: 'Smart grid', icon: Network },
  { to: '/monitoring', label: 'Power monitoring', icon: Activity },
  { to: '/maintenance', label: 'Faults & maintenance', icon: ShieldCheck },
  { to: '/optimization', label: 'AI optimization', icon: Sparkles },
  { to: '/simulation', label: 'Simulation lab', icon: SlidersHorizontal },
  { to: '/reports', label: 'Reports & data', icon: Files }
];
export default function Layout({ children }) {
  const { data, busy, auto, setAuto, lastUpdated, toast, refresh, error } = useGrid();
  const [mobile, setMobile] = useState(false), [light, setLight] = useState(() => localStorage.getItem('heliogrid-theme') === 'light');
  const location = useLocation();
  useEffect(() => { document.documentElement.dataset.theme = light ? 'light' : 'dark'; localStorage.setItem('heliogrid-theme', light ? 'light' : 'dark'); }, [light]);
  useEffect(() => { setMobile(false); window.scrollTo(0, 0); }, [location.pathname]);
  const title = navigation.find(n => n.to === location.pathname)?.label || 'Control center';
  return <div className="app-shell">
    {mobile && <div className="sidebar-overlay" onClick={() => setMobile(false)} />}
    <aside className={`sidebar ${mobile ? 'open' : ''}`}>
      <Link to="/" className="brand"><span className="brand-mark"><Zap size={23} fill="currentColor" strokeWidth={1.5} /></span><span>helio<span>grid</span><small>ENERGY INTELLIGENCE</small></span></Link>
      <div className="workspace"><div className="workspace-icon"><Network size={18} /></div><div><strong>Indore microgrid</strong><span>College demonstration</span></div><ChevronDown size={14} /></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{navigation.map((n, i) => <div key={n.to}>{i === 8 && <div className="nav-label tools-label">SIMULATE & EXPLORE</div>}<NavLink to={n.to} end={n.to === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}><n.icon size={18} strokeWidth={1.65} /><span>{n.label}</span>{n.to === '/maintenance' && data?.current.active_anomalies > 0 && <b className="nav-count">{data.current.active_anomalies}</b>}{n.to === '/optimization' && <span className="nav-ai">AI</span>}</NavLink></div>)}</nav>
      <div className="sidebar-bottom"><div className="simulation-note"><FlaskConical size={19} /><strong>Built to explore.</strong><p>A safe, simulated grid.<br />Real models. Meaningful decisions.</p><Link to="/simulation">Enter simulation lab <ArrowUpRight size={14} /></Link></div><a className="nav-item" href="/api/docs" target="_blank" rel="noreferrer"><CircleHelp size={18} /><span>API documentation</span><ArrowUpRight size={14} /></a><div className="sidebar-version"><span className="tiny-dot" /> System online <span>v1.0.0</span></div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-toggle" aria-label="Open navigation" onClick={() => setMobile(!mobile)}><Menu size={21} /></button><span>Workspace</span><ChevronRight size={13} /><strong>{title}</strong></div><div className="topbar-actions"><Badge tone={error ? 'red' : 'green'}>{error ? 'Backend offline' : 'Simulation mode'}</Badge><span className="topbar-divider" /><button className="icon-button" aria-label="Toggle light and dark theme" onClick={() => setLight(!light)}><Moon size={18} /></button><Link to="/maintenance" className="icon-button notification" aria-label="View alerts"><Bell size={18} />{data?.current.active_anomalies > 0 && <i />}</Link><div className="avatar" title="Student operator">SG</div></div></header>
    <main className="main-content">{children}<footer className="page-footer"><span><FlaskConical size={13} /> Synthetic data · Advisory simulation · Not connected to physical grid equipment</span><span>{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString('en-GB')}` : 'Connecting…'} <button aria-label="Refresh data" className="inline-icon" onClick={refresh}><RefreshCw size={12} /></button></span></footer></main></div>
    {toast && <div className={`toast ${toast.kind}`} role="status">{toast.kind === 'error' ? <AlertCircle size={20} /> : <CheckCircle2 size={20} />}<span>{toast.text}</span></div>}
  </div>;
}
export function SimulationControls() {
  const { data, auto, setAuto, busy, step } = useGrid();
  return <div className="sim-controls"><span className="sim-time"><span className="tiny-dot" />{data ? new Date(data.current.timestamp).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) + ' · ' + new Date(data.current.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : 'Simulation clock'}</span><Button icon={auto ? Pause : Play} variant="small" onClick={() => setAuto(!auto)} disabled={busy}>{auto ? 'Pause' : 'Auto play'}</Button><Button variant="small" onClick={step} loading={busy}>+1 hour</Button></div>;
}
