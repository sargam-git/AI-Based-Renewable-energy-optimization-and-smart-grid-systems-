import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
export function useApi(path, dependency) {
  const [data,setData]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
  const reload=useCallback(async()=>{setLoading(true);try{setData(await api(path));setError('');}catch(e){setError(e.message);}finally{setLoading(false);}},[path]);
  useEffect(()=>{let active=true;api(path).then(d=>{if(active){setData(d);setError('');}}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[path,dependency]);
  return {data,error,loading,reload};
}
