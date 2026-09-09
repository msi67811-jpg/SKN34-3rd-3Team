// ============================================================
// Backend(FastAPI) 연동 레이어
//
//   Frontend(:5173) --/api--> Backend(:8000) --> DB(Postgres :5432)
//                                    └--> LLM 서비스(:8001)
//
// - 개발 서버가 /api 를 http://localhost:8000 으로 프록시한다 (vite.config.js)
// - Backend 가 꺼져 있으면 각 호출이 실패 → fallback(화면의 목데이터) 사용
// - 엔드포인트 규격: Docs/Design/API_SPEC.md
// ============================================================

import { useEffect, useState } from 'react';

const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');

function qs(params) {
  const sp = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '' && v !== '전체') sp.append(k, v);
  });
  const s = sp.toString();
  return s ? `?${s}` : '';
}

/** GET. 실패(네트워크·비2xx·타임아웃)하면 throw. */
export async function apiGet(path, { signal, timeout = 6000 } = {}) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeout);
  const relay = () => ctl.abort();
  if (signal) signal.addEventListener('abort', relay);
  try {
    const res = await fetch(BASE + path, {
      signal: ctl.signal,
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
    if (signal) signal.removeEventListener('abort', relay);
  }
}

/** POST(JSON). 실패하면 throw. */
export async function apiPost(path, body, { signal, timeout = 30000 } = {}) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeout);
  const relay = () => ctl.abort();
  if (signal) signal.addEventListener('abort', relay);
  try {
    const res = await fetch(BASE + path, {
      method: 'POST',
      signal: ctl.signal,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body || {}),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
    if (signal) signal.removeEventListener('abort', relay);
  }
}

/* ---------- 엔드포인트 헬퍼 ---------- */
export const api = {
  stats: (opt) => apiGet('/stats', opt),
  announcements: (params, opt) => apiGet('/announcements' + qs(params), opt),
  policies: (params, opt) => apiGet('/policies' + qs(params), opt),
  policy: (id, opt) => apiGet(`/policies/${id}`, opt),
  recommendations: (params, opt) => apiGet('/policies/recommendations' + qs(params), opt),
  calendar: (params, opt) => apiGet('/calendar' + qs(params), opt),
  calendarUpcoming: (params, opt) => apiGet('/calendar/upcoming' + qs(params), opt),
  taxSchedule: (params, opt) => apiGet('/tax/schedule' + qs(params), opt),
  taxDocuments: (params, opt) => apiGet('/tax/documents' + qs(params), opt),
  taxCheck: (body, opt) => apiPost('/tax/tax-reduction/check', body, opt),
  chat: (body, opt) => apiPost('/chat/messages', body, opt),
};

/**
 * 백엔드에서 데이터를 받아오되, 실패하면 fallback(목데이터)을 쓴다.
 *
 * @param {string}   path      예: '/policies/recommendations'
 * @param {*}        fallback  백엔드 없을 때 값 (모듈 상수 — 참조 고정 필요)
 * @param {Function} [map]     원본 응답 → 화면이 기대하는 형태
 * @returns {{ data:*, loading:boolean, source:'api'|'fallback', error:string }}
 */
export function useApi(path, fallback, map = (x) => x) {
  const [state, setState] = useState({
    data: fallback,
    loading: true,
    source: 'fallback',
    error: '',
  });

  useEffect(() => {
    let alive = true;
    const ctl = new AbortController();
    apiGet(path, { signal: ctl.signal })
      .then((raw) => {
        if (!alive) return;
        let mapped;
        try {
          mapped = map(raw);
        } catch (e) {
          setState({ data: fallback, loading: false, source: 'fallback', error: 'map error' });
          return;
        }
        const empty = Array.isArray(mapped) && mapped.length === 0;
        setState({
          data: empty ? fallback : mapped,
          loading: false,
          source: empty ? 'fallback' : 'api',
          error: '',
        });
      })
      .catch((e) => {
        if (alive) {
          setState({ data: fallback, loading: false, source: 'fallback', error: String(e.message || e) });
        }
      });
    return () => {
      alive = false;
      ctl.abort();
    };
    // fallback/map 은 모듈 상수라 참조 고정 → path 만 의존
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);

  return state;
}

/** 백엔드 연결 여부 배지에 쓸 상태 */
export function useBackendStatus() {
  const [ok, setOk] = useState(null); // null=확인중, true/false
  useEffect(() => {
    let alive = true;
    apiGet('/stats', { timeout: 4000 })
      .then(() => alive && setOk(true))
      .catch(() => alive && setOk(false));
    return () => {
      alive = false;
    };
  }, []);
  return ok;
}
