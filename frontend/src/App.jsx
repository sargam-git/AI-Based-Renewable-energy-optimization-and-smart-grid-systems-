import { Component } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { AlertTriangle, RefreshCw, WifiOff } from 'lucide-react';
import { GridProvider, useGrid } from './hooks/GridContext';
import Layout from './components/Layout';
import { Loading, Notice, Button, PageHeader } from './components/UI';
import Overview from './pages/Overview';
import Renewables from './pages/Renewables';
import LoadForecast from './pages/LoadForecast';
import Battery from './pages/Battery';
import GridControl from './pages/GridControl';
import Monitoring from './pages/Monitoring';
import Maintenance from './pages/Maintenance';
import Optimization from './pages/Optimization';
import Simulation from './pages/Simulation';
import Reports from './pages/Reports';
class ErrorBoundary extends Component {
 state={error:null};static getDerivedStateFromError(error){return {error};}
 render(){return this.state.error?<div className="fatal-error"><AlertTriangle size={35}/><h1>Something interrupted the control center.</h1><p>{this.state.error.message}</p><Button icon={RefreshCw} onClick={()=>location.reload()}>Reload application</Button></div>:this.props.children;}
}
function Workspace(){
 const {data,loading,error,refresh}=useGrid();
 const shared=page=>loading?<Loading/>:error&&!data?<div className="connection-error"><WifiOff size={38}/><h2>The energy backend is unavailable</h2><Notice tone="error">{error}</Notice><p>Start FastAPI on port 8000, then reconnect. The Vite server proxies /api to the backend.</p><Button icon={RefreshCw} onClick={refresh}>Retry connection</Button></div>:data?page:<Loading/>;
 return <Layout><Routes><Route path="/" element={shared(<Overview/>)}/><Route path="/renewables" element={shared(<Renewables/>)}/><Route path="/load" element={shared(<LoadForecast/>)}/><Route path="/battery" element={shared(<Battery/>)}/><Route path="/grid" element={shared(<GridControl/>)}/><Route path="/monitoring" element={shared(<Monitoring/>)}/><Route path="/maintenance" element={<Maintenance/>}/><Route path="/optimization" element={shared(<Optimization/>)}/><Route path="/simulation" element={shared(<Simulation/>)}/><Route path="/reports" element={<Reports/>}/><Route path="*" element={<><PageHeader title="This page is outside the grid." description="The requested workspace page does not exist."/><Link className="button" to="/">Return to overview</Link></>}/></Routes></Layout>;
}
export default function App(){return <ErrorBoundary><BrowserRouter><GridProvider><Workspace/></GridProvider></BrowserRouter></ErrorBoundary>;}
