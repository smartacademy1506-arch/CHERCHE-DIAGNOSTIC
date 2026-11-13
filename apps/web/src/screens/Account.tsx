// Offres (prix dans la devise locale) et profil / réglages.
import { useEffect, useState } from 'react';
import { useApp } from '../app';
import { listDownloads, removeDownload } from '../lib/data';
import { formatPrice, localAmount } from '../lib/pricing';
import { flushOutbox, outboxCount } from '../lib/store';
import { auth, db } from '../lib/supabase';
import { APP_VERSION } from '../lib/config';
import { Button, Card, Circled, Header, Icon, Loader, Notice } from '../ui';
import { LangCountryPickers } from './Auth';

export function Plans() {
  const { t, lang, refs, currency, setCurrency, session, access, go, back } = useApp();
  const [busy, setBusy] = useState<string | null>(null);
  const [intent, setIntent] = useState<{ reference: string; amount: number; currency_code: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (!refs) return <div className="page"><Header title={t('plans.title')} onBack={back} /><Loader text={t('loading')} /></div>;
  const cur = refs.currencies.find((c) => c.code === currency) ?? refs.currencies.find((c) => c.code === 'USD')!;
  const usd = refs.currencies.find((c) => c.code === 'USD')!;
  const period: Record<string, string> = { month: t('plans.month'), year: t('plans.year'), lifetime: t('plans.lifetime') };
  const priceIn = (code: string) => {
    const p = refs.plans.find((x) => x.code === code);
    if (!p) return null;
    const override = refs.planPrices.find((x) => x.plan_id === p.id && x.currency_code === cur.code)?.amount;
    return localAmount(Number(p.price_usd), cur, override);
  };
  const monthly = priceIn('monthly');

  async function choose(code: string) {
    if (!session) { go('auth'); return; }
    setBusy(code); setError(null);
    try { setIntent(await db.rpc('create_payment_intent', { p_plan_code: code, p_currency: cur.code })); }
    catch { setError(t('error')); }
    finally { setBusy(null); }
  }

  return (
    <div className="page wide">
      <Header title={t('plans.title')} onBack={back} right={
        <label className="field inline"><span className="sr-only">{t('plans.currency')}</span>
          <select value={cur.code} onChange={(e) => setCurrency(e.target.value)} aria-label={t('plans.currency')}>
            {refs.currencies.map((c) => <option key={c.code} value={c.code}>{c.code} — {c.name}</option>)}
          </select></label>} />
      <p className="lead" style={{ color: 'var(--navy)' }}>{t('plans.subtitle')}</p>
      {access.subscription && (
        <Notice kind="ok">{t('plans.current')} : <strong>{refs.plans.find((p) => p.code === access.subscription!.plan_code)?.name[lang] ?? access.subscription.plan_code}</strong>
          {' — '}{access.subscription.ends_at ? `${t('plans.until')} ${new Date(access.subscription.ends_at).toLocaleDateString(lang)}` : t('plans.forever')}</Notice>
      )}
      {intent && (
        <Notice kind="ok"><strong>{t('plans.pay_title')}</strong><br />{t('plans.pay_text')}<br />
          <strong className="ref">{intent.reference}</strong> — {formatPrice(Number(intent.amount), { code: intent.currency_code, decimals: refs.currencies.find((c) => c.code === intent.currency_code)?.decimals ?? 2 }, lang)}</Notice>
      )}
      {error && <Notice kind="error">{error}</Notice>}
      <div className="plans">
        {refs.plans.map((p) => {
          const amount = priceIn(p.code) ?? 0;
          const months = p.billing_period === 'year' ? 12 : 0;
          const saving = months && monthly ? Math.round((1 - amount / (monthly * months)) * 100) : 0;
          const current = access.subscription?.plan_code === p.code;
          return (
            <article key={p.id} className={`card plan${p.is_featured ? ' plan-featured' : ''}`}>
              <div className="row wrap" style={{ justifyContent: 'space-between' }}>
                <h2>{p.name[lang] ?? p.name.en}</h2>
              </div>
              <p className="price" data-testid={`price-${p.code}`}>{formatPrice(amount, cur, lang)}</p>
              <p className="per">
                {period[p.billing_period]}
                {months > 0 && <> · {t('plans.equiv').replace('{x}', formatPrice(amount / months, { ...cur, decimals: Math.max(cur.decimals, cur.code === 'USD' ? 2 : 0) }, lang))}</>}
                {cur.code !== 'USD' && <> · {formatPrice(Number(p.price_usd), usd, lang)}</>}
              </p>
              {saving > 0 && <p><Circled>{t('plans.save').replace('{n}', String(saving))}</Circled></p>}
              <p>{p.description[lang] ?? p.description.en}</p>
              <ul className="bullets">{p.features.map((f, i) => <li key={i}>{f[lang] ?? f.en}</li>)}</ul>
              <Button block variant="primary" disabled={busy === p.code || current} onClick={() => void choose(p.code)}>{current ? t('plans.current') : t('plans.choose')}</Button>
            </article>
          );
        })}
      </div>
      <section>
        <h2>{t('plans.free_title')}</h2>
        <p>{t('plans.free_text')}</p>
      </section>
      <section>
        <h2>{t('plans.how_title')}</h2>
        <p>{t('plans.how_text')}</p>
        {!session && <p className="small muted" style={{ marginTop: '.5rem' }}>{t('plans.login')}</p>}
        {cur.code !== 'USD' && <p className="small muted" style={{ marginTop: '.5rem' }}>{t('plans.converted')}</p>}
      </section>
    </div>
  );
}

export function Settings() {
  const { t, tr, go, session, profile, access, chapters, refreshAccount, toast, online } = useApp();
  const [form, setForm] = useState({ full_name: '', study_field: '', study_level: '', daily_goal_minutes: 20 });
  const [downloads, setDownloads] = useState<string[]>([]);
  const [pending, setPending] = useState(0);
  const staff = access.roles.some((r) => r !== 'student');

  useEffect(() => { if (profile) setForm({ full_name: profile.full_name ?? '', study_field: profile.study_field ?? '', study_level: profile.study_level ?? '', daily_goal_minutes: profile.daily_goal_minutes }); }, [profile]);
  useEffect(() => { void listDownloads().then(setDownloads); void outboxCount().then(setPending); }, []);

  async function saveProfile() {
    if (!session) return;
    try {
      await db.update('profiles', `id=eq.${session.user.id}`, { ...form, daily_goal_minutes: Math.max(5, Math.min(240, Number(form.daily_goal_minutes) || 20)) });
      await refreshAccount(); toast(t('saved'));
    } catch { toast(t('error')); }
  }
  async function exportData() {
    try {
      const data = await db.rpc('export_my_data');
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
      const a = Object.assign(document.createElement('a'), { href: url, download: 'cherche-diagnostic-donnees.json' });
      a.click(); URL.revokeObjectURL(url);
    } catch { toast(t('error')); }
  }
  async function deleteAccount() {
    if (!window.confirm(t('set.delete_confirm'))) return;
    try { await db.rpc('delete_my_account'); await auth.signOut(); go(''); } catch { toast(t('error')); }
  }

  return (
    <div className="page">
      <Header title={t('set.title')} />
      {session ? (
        <Card>
          <p className="muted small">{session.user.email}</p>
          <div className="form">
            <label className="field"><span>{t('auth.name')}</span><input value={form.full_name} maxLength={120} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
            <div className="grid-2">
              <label className="field"><span>{t('set.field')}</span><input value={form.study_field} maxLength={60} onChange={(e) => setForm({ ...form, study_field: e.target.value })} /></label>
              <label className="field"><span>{t('set.level')}</span><input value={form.study_level} maxLength={60} onChange={(e) => setForm({ ...form, study_level: e.target.value })} /></label>
            </div>
            <label className="field"><span>{t('set.goal')}</span><input type="number" min={5} max={240} value={form.daily_goal_minutes} onChange={(e) => setForm({ ...form, daily_goal_minutes: Number(e.target.value) })} /></label>
            <Button onClick={() => void saveProfile()} disabled={!online}>{t('save')}</Button>
          </div>
        </Card>
      ) : (
        <Card><p>{t('auth.guest')}</p><Button onClick={() => go('auth')}>{t('auth.login')}</Button></Card>
      )}

      <Card><LangCountryPickers /></Card>

      <Card onClick={() => go('plans')} className="row">
        <span className="disc-icon"><Icon name="star" /></span>
        <div className="grow"><strong>{t('plans.title')}</strong><p className="muted small">{access.premium ? t('premium') : t('free')}</p></div>
      </Card>
      {staff && <Card onClick={() => go('admin')} className="row"><span className="disc-icon"><Icon name="shield" /></span><strong className="grow">{t('set.admin')}</strong></Card>}

      <section>
        <h2>{t('set.downloads')}</h2>
        <Card>
          {downloads.length === 0 ? <p className="muted">{t('set.no_downloads')}</p> : (
            <ul className="plain">
              {downloads.map((id) => (
                <li key={id} className="row">
                  <span className="grow">{tr(chapters.find((c) => c.id === id)?.title) || id}</span>
                  <Button variant="ghost" onClick={async () => { await removeDownload(id); setDownloads(await listDownloads()); }}>{t('remove')}</Button>
                </li>
              ))}
            </ul>
          )}
          {pending > 0 && (
            <div className="row"><span className="grow">{pending} {t('set.pending')}</span>
              <Button variant="soft" disabled={!online} onClick={async () => setPending(await flushOutbox())}>{t('set.sync')}</Button></div>
          )}
        </Card>
      </section>

      <Card>
        <p className="small">{t('set.disclaimer')}</p>
        <p className="small muted">{t('set.privacy')}</p>
        <p className="small muted">{t('set.version')} {APP_VERSION}</p>
      </Card>
      {session && (
        <div className="stack">
          <Button variant="soft" icon="download" onClick={() => void exportData()}>{t('set.export')}</Button>
          <Button variant="ghost" onClick={async () => { await auth.signOut(); go(''); }}>{t('auth.logout')}</Button>
          <Button variant="danger" onClick={() => void deleteAccount()}>{t('set.delete')}</Button>
        </div>
      )}
    </div>
  );
}
