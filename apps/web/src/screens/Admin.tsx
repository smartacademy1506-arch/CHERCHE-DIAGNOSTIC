// Espace administrateur : statistiques, contenus (statuts, import, glossaire), offres et devises, utilisateurs, paiements.
// Chaque action est revérifiée côté serveur (RLS et fonctions) : masquer un onglet ici n'est pas une protection.
import { useCallback, useEffect, useState } from 'react';
import { useApp } from '../app';
import { gridForm } from '../lib/wordsearch/normalize';
import { generatePuzzle } from '../lib/wordsearch/generator';
import { ApiError, db } from '../lib/supabase';
import { Button, Card, Header, Loader, Notice, Tag } from '../ui';

type Tab = 'overview' | 'content' | 'pricing' | 'users' | 'payments';
const STATUSES = ['draft', 'in_review', 'published', 'archived'];
const CONTENT_TABLES = ['lessons', 'medical_terms', 'quiz_questions', 'open_questions', 'flashcards', 'word_search_puzzles'];
const ROLES = ['admin', 'pedagogy_lead', 'contributor', 'moderator'];

export function Admin() {
  const { lang, access, back } = useApp();
  const L = useCallback((fr: string, en: string) => (lang === 'fr' ? fr : en), [lang]);
  const [tab, setTab] = useState<Tab>('overview');
  const [msg, setMsg] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
  const isAdmin = access.roles.some((r) => r === 'admin' || r === 'super_admin');
  const staff = access.roles.some((r) => r !== 'student');
  const run = useCallback(async (fn: () => Promise<unknown>, ok: string) => {
    try { await fn(); setMsg({ kind: 'ok', text: ok }); return true; }
    catch (e) { setMsg({ kind: 'error', text: e instanceof ApiError ? `${e.status} — ${e.message}` : String(e) }); return false; }
  }, []);

  if (!staff) return <div className="page"><Header title="Administration" onBack={back} /><Notice kind="error">{L('Accès réservé à l\'équipe.', 'Staff only.')}</Notice></div>;
  const tabs: [Tab, string, boolean][] = [
    ['overview', L('Vue d\'ensemble', 'Overview'), true], ['content', L('Contenus', 'Content'), true],
    ['pricing', L('Offres et devises', 'Plans and currencies'), isAdmin], ['users', L('Utilisateurs', 'Users'), isAdmin], ['payments', L('Paiements', 'Payments'), isAdmin],
  ];
  return (
    <div className="page wide">
      <Header title="Administration" onBack={back} />
      <div className="tabs" role="tablist">
        {tabs.filter((x) => x[2]).map(([k, label]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={`tab${tab === k ? ' active' : ''}`} onClick={() => { setTab(k); setMsg(null); }}>{label}</button>)}
      </div>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}
      {tab === 'overview' && <Overview L={L} />}
      {tab === 'content' && <Content L={L} run={run} />}
      {tab === 'pricing' && <Pricing L={L} run={run} />}
      {tab === 'users' && <Users L={L} run={run} />}
      {tab === 'payments' && <Payments L={L} run={run} />}
    </div>
  );
}

type P = { L: (fr: string, en: string) => string; run: (fn: () => Promise<unknown>, ok: string) => Promise<boolean> };

function Overview({ L }: Pick<P, 'L'>) {
  const [s, setS] = useState<any>(null);
  useEffect(() => { db.rpc('admin_stats').then(setS).catch(() => setS({})); }, []);
  if (!s) return <Loader text="…" />;
  const cells: [string, unknown][] = [
    [L('Utilisateurs', 'Users'), s.users], [L('Nouveaux (7 j)', 'New (7 d)'), s.users_7d], [L('Abonnés actifs', 'Active subscribers'), s.active_subscriptions],
    [L('Paiements en attente', 'Pending payments'), s.pending_payments], [L('QCM (7 j)', 'Quizzes (7 d)'), s.quiz_attempts_7d], [L('Grilles jouées (7 j)', 'Puzzles played (7 d)'), s.puzzle_sessions_7d],
    [L('Termes', 'Terms'), s.terms], [L('Questions', 'Questions'), s.questions], [L('Grilles vérifiées', 'Verified puzzles'), s.puzzles_validated],
  ];
  return (
    <>
      <div className="grid-3">{cells.map(([k, v]) => <Card key={k} className="stat"><span className="stat-num">{String(v ?? '—')}</span><span className="stat-label">{k}</span></Card>)}</div>
      <Card><strong>{L('Chapitres par statut', 'Chapters by status')}</strong><p>{Object.entries(s.chapters ?? {}).map(([k, v]) => `${k} : ${v}`).join(' · ') || '—'}</p></Card>
    </>
  );
}

function Content({ L, run }: P) {
  const { disciplines, chapters, reloadCatalog, tr, access } = useApp();
  const canPublish = access.roles.some((r) => ['super_admin', 'admin', 'pedagogy_lead'].includes(r));
  const [discipline, setDiscipline] = useState('');
  const [free, setFree] = useState(false);
  const [replace, setReplace] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [terms, setTerms] = useState<any[]>([]);

  async function setStatus(chapterId: string, status: string) {
    const ok = await run(async () => {
      // Ordre : contenus d'abord, chapitre ensuite, pour ne jamais exposer un chapitre publié au contenu incomplet.
      for (const table of CONTENT_TABLES) await db.update(table, `chapter_id=eq.${chapterId}`, { status });
      await db.update('chapters', `id=eq.${chapterId}`, { status, ...(status === 'published' ? { last_verified_at: new Date().toISOString() } : {}) });
    }, L('Statut mis à jour.', 'Status updated.'));
    if (ok) await reloadCatalog();
  }
  async function importFile(file: File) {
    await run(async () => {
      const payload = JSON.parse(await file.text());
      // Les grilles sont générées ici puis revérifiées par la base avant d'être acceptées.
      payload.puzzles = {};
      for (const l of ['fr', 'en']) payload.puzzles[l] = generatePuzzle(payload.terms.map((x: any) => gridForm(x[l])), { seed: Date.now() % 2 ** 31 });
      await db.rpc('admin_import_chapter', { p_discipline_slug: discipline, p_payload: payload, p_is_free: free, p_replace: replace });
      await reloadCatalog();
    }, L('Chapitre importé (statut : en validation).', 'Chapter imported (status: in review).'));
  }
  async function openTerms(chapterId: string) {
    setEditing(chapterId);
    setTerms(await db.select('medical_terms', `select=id,label,glossary_entries(id,definition)&chapter_id=eq.${chapterId}&order=sort`));
  }
  const def = (x: any) => (Array.isArray(x.glossary_entries) ? x.glossary_entries[0] : x.glossary_entries);

  return (
    <>
      <Card>
        <strong>{L('Importer un chapitre (JSON au format content/SPEC.md)', 'Import a chapter (JSON in content/SPEC.md format)')}</strong>
        <div className="row wrap">
          <select value={discipline} onChange={(e) => setDiscipline(e.target.value)} aria-label="Discipline">
            <option value="">{L('Discipline…', 'Discipline…')}</option>
            {disciplines.map((d) => <option key={d.id} value={d.slug}>{tr(d.title)}</option>)}
          </select>
          <label className="check"><input type="checkbox" checked={free} onChange={(e) => setFree(e.target.checked)} /><span>{L('Gratuit', 'Free')}</span></label>
          <label className="check"><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} /><span>{L('Remplacer s\'il existe', 'Replace if it exists')}</span></label>
          <input type="file" accept="application/json" disabled={!discipline} onChange={(e) => { const f = e.target.files?.[0]; if (f) void importFile(f); e.target.value = ''; }} />
        </div>
        {replace && <Notice kind="warn">{L('Remplacer un chapitre supprime son contenu actuel et les résultats des étudiants qui y sont liés.', 'Replacing a chapter deletes its current content and the student results linked to it.')}</Notice>}
      </Card>
      <div className="table-wrap">
        <table>
          <thead><tr><th>{L('Chapitre', 'Chapter')}</th><th>{L('Accès', 'Access')}</th><th>{L('Statut', 'Status')}</th><th /></tr></thead>
          <tbody>
            {chapters.map((c) => (
              <tr key={c.id}>
                <td>{tr(c.title)}<br /><span className="muted small">{tr(disciplines.find((d) => d.id === c.discipline_id)?.title)}</span></td>
                <td><label className="check"><input type="checkbox" checked={c.is_free} onChange={async (e) => { if (await run(() => db.update('chapters', `id=eq.${c.id}`, { is_free: e.target.checked }), 'OK')) await reloadCatalog(); }} /><span>{L('Gratuit', 'Free')}</span></label></td>
                <td>
                  <select value={c.status} onChange={(e) => void setStatus(c.id, e.target.value)} aria-label={L('Statut', 'Status')}>
                    {STATUSES.map((s) => <option key={s} value={s} disabled={s === 'published' && !canPublish}>{s}</option>)}
                  </select>
                </td>
                <td><Button variant="ghost" onClick={() => void openTerms(c.id)}>{L('Glossaire', 'Glossary')}</Button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing && (
        <Card>
          <div className="row"><strong className="grow">{L('Définitions', 'Definitions')} — {tr(chapters.find((c) => c.id === editing)?.title)}</strong><Button variant="ghost" onClick={() => setEditing(null)}>{L('Fermer', 'Close')}</Button></div>
          <p className="small muted">{L('Le libellé d\'un terme ne se modifie pas ici : il est lié à la grille de mots mêlés, qui devrait être régénérée.', 'Term labels cannot be edited here: they are tied to the word-search grid, which would need regenerating.')}</p>
          {terms.map((x) => (
            <div key={x.id} className="term-edit">
              <strong>{x.label.fr} / {x.label.en}</strong>
              {(['fr', 'en'] as const).map((l) => (
                <label key={l} className="field"><span>{l.toUpperCase()}</span>
                  <textarea rows={2} defaultValue={def(x)?.definition?.[l] ?? ''} onBlur={(e) => {
                    const d = def(x); const v = e.target.value.trim();
                    if (!d || !v || v === d.definition[l]) return;
                    d.definition = { ...d.definition, [l]: v };
                    void run(() => db.update('glossary_entries', `id=eq.${d.id}`, { definition: d.definition, last_verified_at: new Date().toISOString() }), L('Définition enregistrée.', 'Definition saved.'));
                  }} /></label>
              ))}
            </div>
          ))}
        </Card>
      )}
    </>
  );
}

function Pricing({ L, run }: P) {
  const [plans, setPlans] = useState<any[]>([]);
  const [currencies, setCurrencies] = useState<any[]>([]);
  const load = useCallback(async () => {
    setPlans(await db.select('plans', 'select=id,code,price_usd,is_active,billing_period&order=sort'));
    setCurrencies(await db.select('currencies', 'select=code,name,usd_rate,rounding,is_active,rate_updated_at&order=code'));
  }, []);
  useEffect(() => { void load(); }, [load]);
  const num = (v: string) => Number(v.replace(',', '.'));
  return (
    <>
      <Card>
        <strong>{L('Offres (prix de référence en USD)', 'Plans (reference price in USD)')}</strong>
        <div className="table-wrap"><table><tbody>
          {plans.map((p) => (
            <tr key={p.id}>
              <td>{p.code}<br /><span className="muted small">{p.billing_period}</span></td>
              <td><input className="num" defaultValue={p.price_usd} inputMode="decimal" aria-label={`${p.code} USD`} onBlur={(e) => { const v = num(e.target.value); if (v >= 0 && v !== Number(p.price_usd)) void run(() => db.update('plans', `id=eq.${p.id}`, { price_usd: v }), L('Prix enregistré.', 'Price saved.')).then(load); }} /> USD</td>
              <td><label className="check"><input type="checkbox" defaultChecked={p.is_active} onChange={(e) => void run(() => db.update('plans', `id=eq.${p.id}`, { is_active: e.target.checked }), 'OK')} /><span>{L('Active', 'Active')}</span></label></td>
            </tr>
          ))}
        </tbody></table></div>
      </Card>
      <Card>
        <strong>{L('Devises (unités pour 1 USD, pas d\'arrondi)', 'Currencies (units per 1 USD, rounding step)')}</strong>
        <div className="table-wrap"><table>
          <thead><tr><th>{L('Devise', 'Currency')}</th><th>{L('Taux', 'Rate')}</th><th>{L('Arrondi', 'Rounding')}</th><th>{L('Mis à jour', 'Updated')}</th></tr></thead>
          <tbody>
            {currencies.map((c) => (
              <tr key={c.code}>
                <td>{c.code}<br /><span className="muted small">{c.name}</span></td>
                <td><input className="num" defaultValue={c.usd_rate} inputMode="decimal" disabled={c.code === 'USD'} aria-label={`${c.code} rate`} onBlur={(e) => { const v = num(e.target.value); if (v > 0 && v !== Number(c.usd_rate)) void run(() => db.update('currencies', `code=eq.${c.code}`, { usd_rate: v, rate_updated_at: new Date().toISOString() }), L('Taux enregistré.', 'Rate saved.')).then(load); }} /></td>
                <td><input className="num" defaultValue={c.rounding} inputMode="decimal" aria-label={`${c.code} rounding`} onBlur={(e) => { const v = num(e.target.value); if (v > 0 && v !== Number(c.rounding)) void run(() => db.update('currencies', `code=eq.${c.code}`, { rounding: v }), 'OK').then(load); }} /></td>
                <td className="muted small">{new Date(c.rate_updated_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </Card>
    </>
  );
}

function Users({ L, run }: P) {
  const { access } = useApp();
  const superAdmin = access.roles.includes('super_admin');
  const [q, setQ] = useState('');
  const [rows, setRows] = useState<any[] | null>(null);
  const load = useCallback(async () => { try { setRows(await db.rpc('admin_list_users', { p_search: q || null })); } catch { setRows([]); } }, [q]);
  useEffect(() => { void load(); }, [load]);
  return (
    <>
      <input className="search" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={L('Rechercher par nom ou e-mail', 'Search by name or email')} />
      {!rows ? <Loader text="…" /> : (
        <div className="table-wrap"><table>
          <thead><tr><th>{L('Utilisateur', 'User')}</th><th>{L('Rôles', 'Roles')}</th><th>{L('Abonnement', 'Subscription')}</th></tr></thead>
          <tbody>
            {rows.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name || '—'}<br /><span className="muted small">{u.email} · {u.country_code ?? '—'}</span></td>
                <td>
                  <div className="row wrap">{u.roles.map((r: string) => <Tag key={r}>{r}</Tag>)}</div>
                  <select value="" aria-label={L('Modifier un rôle', 'Change a role')} onChange={(e) => { const [op, role] = e.target.value.split(':'); if (role) void run(() => db.rpc('admin_set_role', { p_user_id: u.id, p_role: role, p_grant: op === '+' }), 'OK').then(load); }}>
                    <option value="">±</option>
                    {ROLES.filter((r) => r !== 'admin' || superAdmin).map((r) => <option key={r} value={`${u.roles.includes(r) ? '-' : '+'}:${r}`}>{u.roles.includes(r) ? '− ' : '+ '}{r}</option>)}
                  </select>
                </td>
                <td>
                  {u.plan_code ? <Tag kind="premium">{u.plan_code}{u.ends_at ? ` → ${new Date(u.ends_at).toLocaleDateString()}` : ''}</Tag> : '—'}
                  <select value="" aria-label={L('Accorder une offre', 'Grant a plan')} onChange={(e) => { if (e.target.value) void run(() => db.rpc('admin_grant_subscription', { p_user_id: u.id, p_plan_code: e.target.value }), L('Accès accordé.', 'Access granted.')).then(load); }}>
                    <option value="">{L('Accorder…', 'Grant…')}</option>
                    {['monthly', 'yearly', 'lifetime'].map((p) => <option key={p} value={p}>{p}</option>)}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
    </>
  );
}

function Payments({ L, run }: P) {
  const [rows, setRows] = useState<any[] | null>(null);
  const load = useCallback(async () => { setRows(await db.select('payments', 'select=id,reference,amount,currency_code,status,created_at,plans(code)&order=created_at.desc&limit=100').catch(() => [])); }, []);
  useEffect(() => { void load(); }, [load]);
  if (!rows) return <Loader text="…" />;
  return (
    <div className="table-wrap"><table>
      <thead><tr><th>{L('Référence', 'Reference')}</th><th>{L('Offre', 'Plan')}</th><th>{L('Montant', 'Amount')}</th><th>{L('Statut', 'Status')}</th><th /></tr></thead>
      <tbody>
        {rows.length === 0 && <tr><td colSpan={5} className="muted">{L('Aucun paiement.', 'No payments.')}</td></tr>}
        {rows.map((p) => (
          <tr key={p.id}>
            <td><strong>{p.reference}</strong><br /><span className="muted small">{new Date(p.created_at).toLocaleString()}</span></td>
            <td>{p.plans?.code}</td>
            <td>{p.amount} {p.currency_code}</td>
            <td><Tag kind={p.status === 'succeeded' ? 'free' : p.status === 'pending' ? 'review' : 'neutral'}>{p.status}</Tag></td>
            <td>{p.status === 'pending' && <Button variant="soft" onClick={() => { if (window.confirm(L(`Confirmer la réception du paiement ${p.reference} et activer l'abonnement ?`, `Confirm payment ${p.reference} was received and activate the subscription?`))) void run(() => db.rpc('admin_confirm_payment', { p_payment_id: p.id }), L('Paiement confirmé, abonnement activé.', 'Payment confirmed, subscription activated.')).then(load); }}>{L('Confirmer', 'Confirm')}</Button>}</td>
          </tr>
        ))}
      </tbody>
    </table></div>
  );
}
