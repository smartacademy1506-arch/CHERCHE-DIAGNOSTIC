// Accueil (langue, pays), connexion, inscription, mot de passe oublié et réinitialisation.
import { useState, type FormEvent } from 'react';
import { useApp } from '../app';
import { UI_LANGS, type Lang } from '../lib/locale';
import { ApiError, auth } from '../lib/supabase';
import { Button, Header, Notice } from '../ui';

const LANG_NAMES: Record<Lang, string> = { fr: 'Français', en: 'English', es: 'Español', zh: '中文' };

export function LangCountryPickers() {
  const { lang, setLang, country, setCountry, setCurrency, refs, t, tr } = useApp();
  const countries = [...(refs?.countries ?? [])].sort((a, b) => (a.name[lang] ?? a.name.en).localeCompare(b.name[lang] ?? b.name.en, lang));
  return (
    <div className="grid-2">
      <label className="field">
        <span>{t('onb.lang')}</span>
        <select value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
          {UI_LANGS.map((l) => <option key={l} value={l}>{LANG_NAMES[l]}</option>)}
        </select>
      </label>
      <label className="field">
        <span>{t('onb.country')}</span>
        <select value={country ?? ''} onChange={(e) => {
          const c = refs?.countries.find((x) => x.code === e.target.value);
          if (c) { setCountry(c.code); setCurrency(c.currency_code); }
        }}>
          <option value="" disabled>—</option>
          {countries.map((c) => <option key={c.code} value={c.code}>{c.name[lang] ?? tr(c.name)}</option>)}
        </select>
      </label>
    </div>
  );
}

export function Welcome({ onDone }: { onDone: () => void }) {
  const { t, go } = useApp();
  return (
    <div className="welcome">
      <img src="/icon.svg" alt="" width="88" height="88" />
      <h1>{t('onb.title')}</h1>
      <p className="lead">{t('tagline')}</p>
      <p className="muted">{t('onb.subtitle')}</p>
      <LangCountryPickers />
      <Button block onClick={onDone}>{t('start')}</Button>
      <Button block variant="ghost" onClick={() => { onDone(); go('auth'); }}>{t('onb.have_account')}</Button>
      <p className="small muted">{t('set.disclaimer')}</p>
    </div>
  );
}

type Mode = 'login' | 'signup' | 'forgot';

export function AuthScreen() {
  const { t, lang, country, go, back } = useApp();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const redirect = location.origin + '/';

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null); setInfo(null); setBusy(true);
    try {
      if (mode === 'login') { await auth.signIn(email.trim(), password); go(''); }
      else if (mode === 'signup') {
        const s = await auth.signUp(email.trim(), password, { full_name: name.trim(), language_code: lang, country_code: country ?? '', consent: String(consent) }, redirect);
        if (s) go(''); else { setInfo(t('auth.confirm_sent')); setMode('login'); }
      } else { await auth.recover(email.trim(), redirect); setInfo(t('auth.reset_sent')); }
    } catch (err) {
      const api = err instanceof ApiError ? err : null;
      setError(api?.status === 0 ? t('offline') : mode === 'login' && api?.status === 400 ? t('auth.bad') : api?.message || t('error'));
    } finally { setBusy(false); }
  }

  return (
    <div className="narrow">
      <Header title={t(mode === 'login' ? 'auth.login' : mode === 'signup' ? 'auth.signup' : 'auth.forgot')} onBack={back} />
      <form className="form" onSubmit={submit}>
        {info && <Notice kind="ok">{info}</Notice>}
        {error && <Notice kind="error">{error}</Notice>}
        {mode === 'signup' && (
          <label className="field"><span>{t('auth.name')}</span>
            <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" maxLength={120} required /></label>
        )}
        <label className="field"><span>{t('auth.email')}</span>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required /></label>
        {mode !== 'forgot' && (
          <label className="field"><span>{t('auth.password')}</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required />
            {mode === 'signup' && <small className="muted">{t('auth.pw_hint')}</small>}</label>
        )}
        {mode === 'signup' && (
          <label className="check"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required /><span>{t('auth.consent')}</span></label>
        )}
        <Button block type="submit" disabled={busy}>{busy ? t('loading') : t(mode === 'login' ? 'auth.login' : mode === 'signup' ? 'auth.signup' : 'auth.send_reset')}</Button>
      </form>
      <div className="stack center">
        {mode !== 'login' && <Button variant="ghost" onClick={() => setMode('login')}>{t('auth.login')}</Button>}
        {mode !== 'signup' && <Button variant="ghost" onClick={() => setMode('signup')}>{t('auth.signup')}</Button>}
        {mode === 'login' && <Button variant="ghost" onClick={() => setMode('forgot')}>{t('auth.forgot')}</Button>}
        <p className="small muted">{t('auth.guest')}</p>
      </div>
    </div>
  );
}

export function ResetPassword() {
  const { t, go, toast } = useApp();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    try { await auth.updatePassword(password); toast(t('auth.pw_updated')); go(''); }
    catch (err) { setError(err instanceof ApiError && err.message ? err.message : t('error')); }
    finally { setBusy(false); }
  }
  return (
    <div className="narrow">
      <Header title={t('auth.new_password')} />
      <form className="form" onSubmit={submit}>
        {error && <Notice kind="error">{error}</Notice>}
        <label className="field"><span>{t('auth.new_password')}</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} autoComplete="new-password" required />
          <small className="muted">{t('auth.pw_hint')}</small></label>
        <Button block type="submit" disabled={busy}>{t('save')}</Button>
      </form>
    </div>
  );
}
