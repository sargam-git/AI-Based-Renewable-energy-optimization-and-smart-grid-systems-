const BASE = '/api';
export async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000);
  try {
    const response = await fetch(BASE + path, { ...options, signal: controller.signal, headers: { ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
    if (!response.ok) {
      let body; try { body = await response.json(); } catch { body = {}; }
      const detail = body.detail;
      throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(e => e.msg).join('; ') : `Request failed (${response.status})`);
    }
    return response.headers.get('content-type')?.includes('application/json') ? response.json() : response.text();
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The backend took too long to respond. Please retry.');
    if (error instanceof TypeError) throw new Error('Cannot reach the energy backend. Check that FastAPI is running, then retry.');
    throw error;
  } finally { clearTimeout(timer); }
}
export const post = (path, body) => api(path, { method: 'POST', ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
export function downloadCSV(csv, filename) {
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const number = (v, digits = 1) => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v)) ? Number(v).toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits }) : '—';
export const money = v => '$' + number(v, 2);
export const hour = value => new Date(value).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
export const dateLabel = value => new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
export const chartTime = value => hour(value);
