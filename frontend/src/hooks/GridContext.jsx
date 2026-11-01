import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { api, post } from '../services/api';
const GridContext = createContext(null);
export function GridProvider({ children }) {
  const [data, setData] = useState(null), [error, setError] = useState(''), [loading, setLoading] = useState(true), [busy, setBusy] = useState(false);
  const [auto, setAuto] = useState(false), [lastUpdated, setLastUpdated] = useState(null), [toast, setToast] = useState(null);
  const mounted = useRef(true), inFlight = useRef(false);
  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try { const d = await api('/dashboard'); if (mounted.current) { setData(d); setError(''); setLastUpdated(new Date()); } }
    catch (e) { if (mounted.current) setError(e.message); }
    finally { inFlight.current = false; if (mounted.current) setLoading(false); }
  }, []);
  useEffect(() => { mounted.current = true; refresh(); return () => { mounted.current = false; }; }, [refresh]);
  useEffect(() => { if (!auto) return; const id = setInterval(() => post('/simulation/step', { hours: 1 }).then(d => { if (mounted.current) { setData(d); setLastUpdated(new Date()); setError(''); } }).catch(e => { setError(e.message); setAuto(false); }), 12000); return () => clearInterval(id); }, [auto]);
  useEffect(() => { if (!toast) return; const id = setTimeout(() => setToast(null), 5000); return () => clearTimeout(id); }, [toast]);
  const run = useCallback(async (config) => {
    setBusy(true); setAuto(false);
    try { const d = await post('/simulation', config); setData(d); setError(''); setLastUpdated(new Date()); setToast({ text: 'Scenario applied. Forecasts and dispatch schedule recalculated.', kind: 'success' }); return d; }
    catch (e) { setToast({ text: e.message, kind: 'error' }); throw e; }
    finally { setBusy(false); }
  }, []);
  const step = useCallback(async () => {
    setBusy(true);
    try { const d = await post('/simulation/step', { hours: 1 }); setData(d); setLastUpdated(new Date()); setError(''); setToast({ text: 'One simulated hour completed. Battery inventory carried forward.', kind: 'success' }); }
    catch (e) { setToast({ text: e.message, kind: 'error' }); }
    finally { setBusy(false); }
  }, []);
  return <GridContext.Provider value={{ data, error, loading, busy, auto, setAuto, lastUpdated, toast, setToast, refresh, run, step }}>{children}</GridContext.Provider>;
}
export const useGrid = () => useContext(GridContext);
