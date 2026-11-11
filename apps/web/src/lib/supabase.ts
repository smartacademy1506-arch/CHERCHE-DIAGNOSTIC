// Client Supabase minimal (Auth + PostgREST) sans dépendance, basé sur fetch.
import { SUPABASE_KEY, SUPABASE_URL } from './config';

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_at: number; // secondes epoch
  user: { id: string; email: string };
}

export class ApiError extends Error {
  constructor(public status: number, message: string, public code?: string) { super(message); }
  /** Erreur réseau ou serveur temporaire : l'opération peut être rejouée plus tard. */
  get retryable(): boolean { return this.status === 0 || this.status === 401 || this.status === 408 || this.status === 429 || this.status >= 500; }
}

const SESSION_KEY = 'cd.session';
let session: Session | null = readSession();
const listeners = new Set<(s: Session | null) => void>();

function readSession(): Session | null {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); } catch { return null; }
}
function setSession(s: Session | null) {
  session = s;
  try { s ? localStorage.setItem(SESSION_KEY, JSON.stringify(s)) : localStorage.removeItem(SESSION_KEY); } catch { /* stockage indisponible */ }
  listeners.forEach((l) => l(s));
}
export const getSession = () => session;
export function onSessionChange(l: (s: Session | null) => void): () => void { listeners.add(l); return () => listeners.delete(l); }

async function call(path: string, init: RequestInit & { token?: string | null } = {}): Promise<any> {
  const headers: Record<string, string> = {
    apikey: SUPABASE_KEY,
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  };
  const token = init.token === undefined ? session?.access_token : init.token;
  if (token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try { res = await fetch(SUPABASE_URL + path, { ...init, headers }); }
  catch { throw new ApiError(0, 'network'); }
  const text = await res.text();
  const body = text ? safeJson(text) : null;
  if (!res.ok) throw new ApiError(res.status, body?.msg || body?.message || body?.error_description || body?.error || res.statusText, body?.code || body?.error_code);
  return body;
}
function safeJson(t: string) { try { return JSON.parse(t); } catch { return { message: t }; } }

function toSession(b: any): Session {
  return { access_token: b.access_token, refresh_token: b.refresh_token, expires_at: Math.floor(Date.now() / 1000) + (b.expires_in ?? 3600), user: { id: b.user.id, email: b.user.email } };
}

let refreshing: Promise<void> | null = null;
/** Renouvelle le jeton s'il expire dans moins d'une minute. Hors ligne, la session locale est conservée. */
async function ensureFresh(): Promise<void> {
  if (!session || session.expires_at - Date.now() / 1000 > 60) return;
  refreshing ??= (async () => {
    try {
      const b = await call('/auth/v1/token?grant_type=refresh_token', { method: 'POST', token: null, body: JSON.stringify({ refresh_token: session!.refresh_token }) });
      setSession(toSession(b));
    } catch (e) {
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) setSession(null);
    } finally { refreshing = null; }
  })();
  await refreshing;
}

export const auth = {
  /** Renvoie la session, ou null si une confirmation par e-mail est nécessaire. */
  async signUp(email: string, password: string, data: Record<string, string>, redirectTo: string): Promise<Session | null> {
    const b = await call('/auth/v1/signup?redirect_to=' + encodeURIComponent(redirectTo), { method: 'POST', token: null, body: JSON.stringify({ email, password, data }) });
    if (b?.access_token) { const s = toSession(b); setSession(s); return s; }
    return null;
  },
  async signIn(email: string, password: string): Promise<Session> {
    const b = await call('/auth/v1/token?grant_type=password', { method: 'POST', token: null, body: JSON.stringify({ email, password }) });
    const s = toSession(b); setSession(s); return s;
  },
  async signOut(): Promise<void> {
    try { await call('/auth/v1/logout', { method: 'POST' }); } catch { /* déconnexion locale malgré tout */ }
    setSession(null);
  },
  recover(email: string, redirectTo: string): Promise<void> {
    return call('/auth/v1/recover?redirect_to=' + encodeURIComponent(redirectTo), { method: 'POST', token: null, body: JSON.stringify({ email }) });
  },
  async updatePassword(password: string): Promise<void> {
    await ensureFresh();
    await call('/auth/v1/user', { method: 'PUT', body: JSON.stringify({ password }) });
  },
  /** Récupère la session renvoyée dans l'URL par un lien de confirmation ou de réinitialisation. */
  async consumeUrlSession(): Promise<'recovery' | 'signup' | null> {
    const h = location.hash.startsWith('#') ? location.hash.slice(1) : '';
    if (!h.includes('access_token=')) return null;
    const p = new URLSearchParams(h);
    const access_token = p.get('access_token')!;
    try {
      const user = await call('/auth/v1/user', { token: access_token });
      setSession({ access_token, refresh_token: p.get('refresh_token') || '', expires_at: Math.floor(Date.now() / 1000) + Number(p.get('expires_in') || 3600), user: { id: user.id, email: user.email } });
    } catch { return null; }
    return p.get('type') === 'recovery' ? 'recovery' : 'signup';
  },
};

type Prefer = 'return=representation' | 'return=minimal' | 'resolution=merge-duplicates,return=minimal' | 'resolution=ignore-duplicates,return=minimal';

export const db = {
  async select<T = any>(table: string, query = ''): Promise<T[]> {
    await ensureFresh();
    return call(`/rest/v1/${table}?${query}`);
  },
  async insert(table: string, rows: object | object[], prefer: Prefer = 'return=minimal', onConflict?: string): Promise<any> {
    await ensureFresh();
    return call(`/rest/v1/${table}${onConflict ? `?on_conflict=${onConflict}` : ''}`, { method: 'POST', headers: { Prefer: prefer }, body: JSON.stringify(rows) });
  },
  upsert(table: string, rows: object | object[], onConflict?: string): Promise<any> {
    return db.insert(table, rows, 'resolution=merge-duplicates,return=minimal', onConflict);
  },
  async update(table: string, match: string, patch: object): Promise<any> {
    await ensureFresh();
    return call(`/rest/v1/${table}?${match}`, { method: 'PATCH', headers: { Prefer: 'return=minimal' }, body: JSON.stringify(patch) });
  },
  async remove(table: string, match: string): Promise<any> {
    await ensureFresh();
    return call(`/rest/v1/${table}?${match}`, { method: 'DELETE', headers: { Prefer: 'return=minimal' } });
  },
  async rpc<T = any>(fn: string, args: object = {}): Promise<T> {
    await ensureFresh();
    return call(`/rest/v1/rpc/${fn}`, { method: 'POST', body: JSON.stringify(args) });
  },
};
