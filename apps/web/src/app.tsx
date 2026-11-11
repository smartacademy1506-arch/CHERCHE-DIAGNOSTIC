// État global, routage (par fragment d'URL : fonctionne hors ligne sans configuration serveur) et mise en page.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { loadCatalog, loadRefs, type Chapter, type Discipline, type I18n } from './lib/data';
import { translate } from './lib/i18n';
import { browserLang, contentLang, detectCountry, UI_LANGS, type Lang } from './lib/locale';
import type { Currency, Plan } from './lib/pricing';
import { flushOutbox, getHistory, onHistoryChange, pullHistory, type History } from './lib/store';
import { auth, db, getSession, onSessionChange, type Session } from './lib/supabase';
import { Icon } from './ui';

export interface Refs {
  languages: { code: string; native_name: string; is_content_language: boolean }[];
  countries: { code: string; name: I18n; currency_code: string; default_language: string }[];
  currencies: Currency[];
  plans: Plan[];
  planPrices: { plan_id: string; currency_code: string; amount: number }[];
}
export interface Access { roles: string[]; premium: boolean; subscription: { plan_code: string; ends_at: string | null } | null; pilot: boolean }
export interface Profile { id: string; full_name: string | null; country_code: string | null; language_code: string; currency_code: string | null; study_field: string | null; study_level: string | null; daily_goal_minutes: number }

interface Ctx {
  lang: Lang; setLang: (l: Lang) => void;
  t: (key: string) => string;
  /** Texte d'un contenu pédagogique dans la langue de contenu (fr ou en). */
  tr: (v: I18n | null | undefined) => string;
  cl: 'fr' | 'en';
  country: string | null; setCountry: (c: string) => void;
  currency: string; setCurrency: (c: string) => void;
  session: Session | null; profile: Profile | null; access: Access;
  refreshAccount: () => Promise<void>;
  refs: Refs | null;
  disciplines: Discipline[]; chapters: Chapter[]; catalogState: 'loading' | 'ready' | 'stale' | 'error';
  reloadCatalog: () => Promise<void>;
  canOpen: (c: Chapter) => boolean;
  history: History | null;
  online: boolean;
  route: string[]; go: (path: string) => void; back: () => void;
  toast: (msg: string) => void;
}
const AppCtx = createContext<Ctx>(null as unknown as Ctx);
export const useApp = () => useContext(AppCtx);

const GUEST: Access = { roles: [], premium: false, subscription: null, pilot: true };
const ls = {
  get: (k: string) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v); } catch { /* ignore */ } },
};
const parseRoute = () => (location.hash.replace(/^#\/?/, '').split('?')[0] || '').split('/').filter(Boolean);

export function AppProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const saved = ls.get('cd.lang') as Lang | null;
    return saved && UI_LANGS.includes(saved) ? saved : browserLang() ?? 'fr';
  });
  const [country, setCountryState] = useState<string | null>(() => ls.get('cd.country'));
  const [currency, setCurrencyState] = useState<string>(() => ls.get('cd.currency') || 'USD');
  const [session, setSessionState] = useState<Session | null>(getSession());
  const [profile, setProfile] = useState<Profile | null>(null);
  const [access, setAccess] = useState<Access>(GUEST);
  const [refs, setRefs] = useState<Refs | null>(null);
  const [catalog, setCatalog] = useState<{ disciplines: Discipline[]; chapters: Chapter[] }>({ disciplines: [], chapters: [] });
  const [catalogState, setCatalogState] = useState<Ctx['catalogState']>('loading');
  const [history, setHistory] = useState<History | null>(null);
  const [online, setOnline] = useState(navigator.onLine);
  const [route, setRoute] = useState<string[]>(parseRoute());
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const setLang = useCallback((l: Lang) => { setLangState(l); ls.set('cd.lang', l); document.documentElement.lang = l === 'zh' ? 'zh-CN' : l; }, []);
  const setCurrency = useCallback((c: string) => { setCurrencyState(c); ls.set('cd.currency', c); }, []);
  const setCountry = useCallback((c: string) => { setCountryState(c); ls.set('cd.country', c); }, []);
  const toast = useCallback((msg: string) => { setToastMsg(msg); window.setTimeout(() => setToastMsg((m) => (m === msg ? null : m)), 3500); }, []);
  const go = useCallback((path: string) => { location.hash = '#/' + path.replace(/^\//, ''); window.scrollTo(0, 0); }, []);
  const back = useCallback(() => { if (window.history.length > 1) window.history.back(); else location.hash = '#/'; }, []);

  const reloadCatalog = useCallback(async () => {
    try {
      const { data, stale } = await loadCatalog();
      setCatalog(data); setCatalogState(stale ? 'stale' : 'ready');
    } catch { setCatalogState('error'); }
  }, []);

  const refreshAccount = useCallback(async () => {
    const s = getSession();
    if (!s) { setProfile(null); setAccess(GUEST); setHistory(await getHistory()); return; }
    try {
      const [p, a] = await Promise.all([
        db.select<Profile>('profiles', `select=id,full_name,country_code,language_code,currency_code,study_field,study_level,daily_goal_minutes&id=eq.${s.user.id}`),
        db.rpc<Access>('my_access'),
      ]);
      setProfile(p[0] ?? null); setAccess(a);
      ls.set('cd.access', JSON.stringify(a));
      await pullHistory();
    } catch {
      // Hors ligne : on garde les derniers droits connus pour ne pas bloquer les contenus déjà téléchargés.
      try { setAccess(JSON.parse(ls.get('cd.access') || 'null') ?? GUEST); } catch { setAccess(GUEST); }
    }
    setHistory(await getHistory());
    void flushOutbox();
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : lang;
    const onHash = () => setRoute(parseRoute());
    const onOnline = () => { setOnline(true); void flushOutbox(); void reloadCatalog(); };
    const onOffline = () => setOnline(false);
    window.addEventListener('hashchange', onHash);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    const offSession = onSessionChange((s) => { setSessionState(s); void refreshAccount().then(reloadCatalog); });
    const offHistory = onHistoryChange(() => { void getHistory().then(setHistory); });

    void (async () => {
      const kind = await auth.consumeUrlSession();
      if (kind) location.hash = kind === 'recovery' ? '#/reset' : '#/';
      void reloadCatalog();
      void refreshAccount();
      try { setRefs((await loadRefs()).data as Refs); } catch { /* référentiels indisponibles hors ligne au premier lancement */ }
    })();
    return () => { window.removeEventListener('hashchange', onHash); window.removeEventListener('online', onOnline); window.removeEventListener('offline', onOffline); offSession(); offHistory(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Pays, devise et langue par défaut : détectés une fois, puis laissés au choix de l'utilisateur.
  useEffect(() => {
    if (!refs) return;
    void (async () => {
      let c = country;
      if (!c) { c = await detectCountry(); if (c && refs.countries.some((x) => x.code === c)) setCountry(c); }
      const row = refs.countries.find((x) => x.code === c);
      if (!ls.get('cd.currency')) setCurrency(row?.currency_code ?? 'USD');
      if (!ls.get('cd.lang') && row && !browserLang() && UI_LANGS.includes(row.default_language as Lang)) setLang(row.default_language as Lang);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refs]);

  const cl = contentLang(lang);
  const value = useMemo<Ctx>(() => {
    const staff = access.roles.some((r) => r !== 'student');
    return {
      lang, setLang, t: (k) => translate(lang, k),
      tr: (v) => (v ? v[cl] ?? v.en ?? v.fr ?? '' : ''), cl,
      country, setCountry, currency, setCurrency,
      session, profile, access, refreshAccount, refs,
      disciplines: catalog.disciplines, chapters: catalog.chapters, catalogState, reloadCatalog,
      canOpen: (c) => c.is_free || access.premium || staff,
      history, online, route, go, back, toast,
    };
  }, [lang, cl, country, currency, session, profile, access, refs, catalog, catalogState, history, online, route, setLang, setCountry, setCurrency, refreshAccount, reloadCatalog, go, back, toast]);

  return (
    <AppCtx.Provider value={value}>
      {children}
      {toastMsg && <div className="toast" role="status">{toastMsg}</div>}
    </AppCtx.Provider>
  );
}

const TABS: { path: string; key: string; icon: string }[] = [
  { path: '', key: 'nav.home', icon: 'home' },
  { path: 'learn', key: 'nav.learn', icon: 'book' },
  { path: 'review', key: 'nav.review', icon: 'repeat' },
  { path: 'stats', key: 'nav.stats', icon: 'chart' },
  { path: 'me', key: 'nav.me', icon: 'user' },
];

export function Shell({ children }: { children: ReactNode }) {
  const { t, route, go, online, access, lang } = useApp();
  const active = route[0] === 'd' || route[0] === 'c' ? 'learn' : route[0] === 'plans' || route[0] === 'admin' ? 'me' : route[0] ?? '';
  return (
    <div className="shell">
      <nav className="nav" aria-label="Navigation">
        <button type="button" className="brand" onClick={() => go('')}>
          <img src="/icon.svg" alt="" width="32" height="32" />
          <span>CHERCHE &amp; DIAGNOSTIC</span>
        </button>
        {TABS.map((tab) => (
          <button key={tab.path} type="button" className={`nav-item${active === tab.path ? ' active' : ''}`} onClick={() => go(tab.path)} aria-current={active === tab.path ? 'page' : undefined}>
            <Icon name={tab.icon} size={22} />
            <span>{t(tab.key)}</span>
          </button>
        ))}
      </nav>
      <main className="main">
        {!online && <div className="banner banner-offline">{t('offline')}</div>}
        {access.pilot && <div className="banner banner-review"><Icon name="alert" size={16} /> {t('in_review')}</div>}
        {lang !== 'fr' && lang !== 'en' && <div className="banner banner-note">{t('content_lang_note')}</div>}
        {children}
      </main>
    </div>
  );
}
