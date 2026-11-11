// Tests de bout en bout : l'application construite (dist/) tourne dans Chromium face à un faux Supabase
// alimenté par supabase/seed/*.json. Usage : node build.mjs && node tests/e2e.mjs
import { createServer } from 'node:http';
import { readFileSync, readdirSync, existsSync, mkdirSync } from 'node:fs';
import { join, extname } from 'node:path';
import { randomUUID } from 'node:crypto';
import { chromium } from 'playwright';

const root = join(import.meta.dirname, '..');
const dist = join(root, 'dist');
const seedDir = join(root, '../../supabase/seed');
const shots = join(root, 'tests/screenshots');
mkdirSync(shots, { recursive: true });

// ───────────── Faux backend ─────────────
const DISC = { id: randomUUID(), slug: 'physiologie', title: { fr: 'Physiologie', en: 'Physiology' }, description: {}, icon: 'pulse', sort: 1, status: 'published' };
const EMPTY = { id: randomUUID(), slug: 'anatomie', title: { fr: 'Anatomie', en: 'Anatomy' }, description: {}, icon: 'bone', sort: 2, status: 'published' };
const chapters = readdirSync(seedDir).filter((f) => f.endsWith('.json')).map((f) => JSON.parse(readFileSync(join(seedDir, f), 'utf8'))).sort((a, b) => a.order - b.order)
  .map((c) => {
    const id = randomUUID();
    const terms = c.terms.map((t) => ({ id: randomUUID(), label: { fr: t.fr, en: t.en }, glossary_entries: { definition: t.definition } }));
    const questions = c.quiz.map((q, i) => ({ id: randomUUID(), type: q.type, difficulty: q.difficulty, stem: q.stem, sort: i, explanation: q.explanation, quiz_options: q.options.map((o, j) => ({ id: randomUUID(), label: { fr: o.fr, en: o.en }, sort: j, correct: o.correct })) }));
    return {
      row: { id, discipline_id: DISC.id, slug: c.slug, title: c.title, description: c.description, sort: c.order, is_free: c.order === 1, status: 'in_review', content_version: 1 },
      lessons: [{ title: c.title, summary: c.summary, key_points: c.key_points, source_refs: c.references, status: 'in_review' }],
      learning_objectives: c.objectives.map((body) => ({ body })),
      medical_terms: terms,
      word_search_puzzles: Object.entries(c.puzzles).map(([lang, p]) => ({ id: randomUUID(), language_code: lang, size: p.size, grid: p.grid, puzzle_words: p.words.map((w) => ({ term_id: terms[w.term_index].id, word: w.word, start_row: w.row, start_col: w.col, d_row: w.d_row, d_col: w.d_col })) })),
      quiz_questions: questions,
      open_questions: c.open_questions.map((q) => ({ id: randomUUID(), question: q.question, model_answer: q.model_answer })),
      flashcards: terms.map((t) => ({ id: randomUUID(), front: t.label, back: t.glossary_entries.definition })),
    };
  });
const refs = {
  languages: [{ code: 'fr', native_name: 'Français', is_content_language: true }, { code: 'en', native_name: 'English', is_content_language: true }],
  countries: [{ code: 'CM', name: { fr: 'Cameroun', en: 'Cameroon' }, currency_code: 'XAF', default_language: 'fr' }, { code: 'US', name: { fr: 'États-Unis', en: 'United States' }, currency_code: 'USD', default_language: 'en' }],
  currencies: [{ code: 'USD', name: 'US Dollar', symbol: '$', usd_rate: 1, decimals: 2, rounding: 0.01 }, { code: 'XAF', name: 'Franc CFA', symbol: 'FCFA', usd_rate: 574, decimals: 0, rounding: 50 }, { code: 'EUR', name: 'Euro', symbol: '€', usd_rate: 0.875, decimals: 2, rounding: 0.01 }],
  plans: [['monthly', 'month', 2.99, 'Mensuel', 'Monthly'], ['yearly', 'year', 19.99, 'Annuel', 'Yearly'], ['lifetime', 'lifetime', 49.99, 'À vie', 'Lifetime']].map(([code, billing_period, price_usd, fr, en], i) => ({ id: randomUUID(), code, billing_period, price_usd, name: { fr, en }, description: { fr: '', en: '' }, features: [], is_featured: i === 1, sort: i })),
  plan_prices: [],
};
const stats = { rpc: 0 };

function mock(url, method, body) {
  const u = new URL(url);
  const path = u.pathname.replace('/rest/v1/', '');
  const chapterId = (u.searchParams.get('chapter_id') || '').replace('eq.', '');
  const ch = chapters.find((c) => c.row.id === chapterId);
  if (path === 'disciplines') return [DISC, EMPTY];
  if (path === 'chapters') return chapters.map((c) => c.row);
  if (path in refs) return refs[path];
  if (ch && path in ch) {
    if (path !== 'quiz_questions') return ch[path];
    // comme en production : ni bonnes réponses ni explications dans la lecture publique
    return ch.quiz_questions.map(({ explanation, quiz_options, ...q }) => ({ ...q, quiz_options: quiz_options.map(({ correct, ...o }) => o) }));
  }
  if (path === 'rpc/submit_quiz_attempt' && method === 'POST') {
    stats.rpc++;
    const c = chapters.find((x) => x.row.id === body.p_chapter_id);
    if (!c.row.is_free) return { __status: 403, message: 'forbidden' };
    const results = c.quiz_questions.filter((q) => q.id in body.p_answers).map((q) => {
      const correct = q.quiz_options.filter((o) => o.correct).map((o) => o.id);
      const selected = body.p_answers[q.id];
      return { question_id: q.id, selected, correct, is_correct: selected.length === correct.length && selected.every((x) => correct.includes(x)), explanation: q.explanation };
    });
    return { attempt_id: body.p_attempt_id, score: results.filter((r) => r.is_correct).length, total: results.length, stored: false, results };
  }
  return { __status: 404, message: `mock: ${method} ${path}` };
}

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
const server = createServer((req, res) => {
  if (req.url.startsWith('/api/geo')) { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{"country":"CM"}'); return; }
  let file = join(dist, req.url.split('?')[0]);
  if (!existsSync(file) || req.url === '/') file = join(dist, 'index.html');
  res.writeHead(200, { 'Content-Type': TYPES[extname(file)] || 'application/octet-stream' });
  res.end(readFileSync(file));
});
await new Promise((r) => server.listen(0, r));
const base = `http://localhost:${server.address().port}`;

// ───────────── Scénarios ─────────────
const results = [];
let offline = false;
const browser = await chromium.launch();

async function newPage(viewport, locale = 'fr-FR') {
  const ctx = await browser.newContext({ viewport, locale, timezoneId: 'Africa/Douala', hasTouch: viewport.width < 600 });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push(m.text()); });
  await page.route('**/*.supabase.co/**', async (route) => {
    if (offline) return route.abort('internetdisconnected');
    const req = route.request();
    const out = mock(req.url(), req.method(), req.postDataJSON?.() ?? null);
    const status = out?.__status ?? 200;
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(out) });
  });
  return { page, errors, ctx };
}
async function step(name, fn) {
  try { await fn(); results.push([name, true]); console.log(`ok   ${name}`); }
  catch (e) { results.push([name, false]); console.log(`FAIL ${name}\n     ${String(e.message).split('\n')[0]}`); }
}
const expectText = async (page, text) => { await page.getByText(text, { exact: false }).first().waitFor({ timeout: 6000 }); };

const { page, errors } = await newPage({ width: 390, height: 844 });
const free = chapters[0];
const puzzle = free.word_search_puzzles.find((p) => p.language_code === 'fr');

await step('accueil : choix de langue et de pays, puis tableau de bord', async () => {
  await page.goto(base);
  await expectText(page, 'Bienvenue sur CHERCHE & DIAGNOSTIC');
  await page.screenshot({ path: join(shots, '01-accueil.png') });
  await page.getByRole('button', { name: 'Commencer' }).click();
  await expectText(page, 'Continuer mes révisions');
  await expectText(page, 'Physiologie');
  await expectText(page, 'Contenu en cours de validation pédagogique');
  await page.screenshot({ path: join(shots, '02-tableau-de-bord.png') });
});

await step('catalogue : discipline sans chapitre marquée « bientôt », chapitre premium verrouillé', async () => {
  await page.goto(`${base}/#/learn`);
  await expectText(page, 'Bientôt disponible');
  await page.goto(`${base}/#/d/physiologie`);
  await expectText(page, free.row.title.fr);
  await page.screenshot({ path: join(shots, '03-chapitres.png') });
  await page.goto(`${base}/#/c/${chapters[1].row.id}`);
  await expectText(page, 'Ce chapitre fait partie de l\'offre Premium.');
});

await step('cours : résumé, points essentiels, références, marquage « lu »', async () => {
  await page.goto(`${base}/#/c/${free.row.id}`);
  await expectText(page, 'Objectifs pédagogiques');
  await page.screenshot({ path: join(shots, '04-chapitre.png') });
  await page.goto(`${base}/#/c/${free.row.id}/lesson`);
  await expectText(page, 'Points essentiels');
  await expectText(page, 'Références');
  await page.getByRole('button', { name: 'J\'ai lu ce cours' }).click();
  await expectText(page, 'Cours lu');
  await page.screenshot({ path: join(shots, '05-cours.png') });
});

async function cellCenter(p, r, c) {
  const box = await p.getByTestId('ws-grid').boundingBox();
  const inner = box.width - 10; // bordure + marge intérieure
  return { x: box.x + 5 + (c + 0.5) * (inner / puzzle.size), y: box.y + 5 + (r + 0.5) * (inner / puzzle.size) };
}
async function dragWord(p, w) {
  const a = await cellCenter(p, w.start_row, w.start_col);
  const b = await cellCenter(p, w.start_row + (w.word.length - 1) * w.d_row, w.start_col + (w.word.length - 1) * w.d_col);
  await p.mouse.move(a.x, a.y); await p.mouse.down(); await p.mouse.move((a.x + b.x) / 2, (a.y + b.y) / 2); await p.mouse.move(b.x, b.y); await p.mouse.up();
}

await step('mots mêlés : glisser sur un mot le valide et affiche sa définition', async () => {
  await page.goto(`${base}/#/c/${free.row.id}/ws`);
  await page.getByTestId('ws-grid').waitFor();
  await expectText(page, `0 / ${puzzle.puzzle_words.length} trouvés`);
  await dragWord(page, puzzle.puzzle_words[0]);
  await expectText(page, `1 / ${puzzle.puzzle_words.length} trouvés`);
  const term = free.medical_terms.find((t) => t.id === puzzle.puzzle_words[0].term_id);
  await expectText(page, term.glossary_entries.definition.fr.slice(0, 40));
  await page.screenshot({ path: join(shots, '06-mots-meles.png') });
});

await step('mots mêlés : une sélection fausse ne valide rien ; toucher début puis fin valide un mot', async () => {
  const w = puzzle.puzzle_words[1];
  const a = await cellCenter(page, 0, 0), b = await cellCenter(page, 0, 1);
  await page.mouse.move(a.x, a.y); await page.mouse.down(); await page.mouse.move(b.x, b.y); await page.mouse.up();
  await expectText(page, `1 / ${puzzle.puzzle_words.length} trouvés`);
  const s = await cellCenter(page, w.start_row, w.start_col);
  const e = await cellCenter(page, w.start_row + (w.word.length - 1) * w.d_row, w.start_col + (w.word.length - 1) * w.d_col);
  await page.mouse.click(s.x, s.y); await page.mouse.click(e.x, e.y);
  await expectText(page, `2 / ${puzzle.puzzle_words.length} trouvés`);
});

await step('mots mêlés : la partie interrompue reprend avec les mots déjà trouvés', async () => {
  // La reprise suppose la progression écrite sur l'appareil : on attend la fin de l'écriture avant de recharger.
  await page.waitForFunction(async (pid) => {
    const idb = await new Promise((r) => { const q = indexedDB.open('cherche-diagnostic'); q.onsuccess = () => r(q.result); });
    const h = await new Promise((r) => { const q = idb.transaction('kv').objectStore('kv').get('history:guest'); q.onsuccess = () => r(q.result); });
    idb.close();
    return h?.puzzles?.[pid]?.found?.length === 2;
  }, puzzle.id, { timeout: 5000 });
  await page.reload();
  await page.getByTestId('ws-grid').waitFor();
  await expectText(page, `2 / ${puzzle.puzzle_words.length} trouvés`);
  await page.getByRole('button', { name: 'Pause' }).click();
  await expectText(page, 'Partie en pause');
  await page.getByRole('button', { name: 'Reprendre' }).first().click();
  await page.getByRole('button', { name: 'Arrêter et voir le résultat' }).click();
  await expectText(page, 'Termes non retrouvés');
  await page.screenshot({ path: join(shots, '07-resultat-grille.png') });
});

await step('QCM : la lecture publique ne contient aucune bonne réponse ; correction détaillée après envoi', async () => {
  await page.goto(`${base}/#/c/${free.row.id}/quiz`);
  await page.getByRole('button', { name: 'Commencer' }).click();
  for (let i = 0; i < free.quiz_questions.length; i++) {
    const q = free.quiz_questions[i];
    for (const o of q.quiz_options.filter((x) => x.correct)) await page.getByRole(q.type === 'single' ? 'radio' : 'checkbox', { name: o.label.fr, exact: true }).click();
    if (i === 0) await page.screenshot({ path: join(shots, '08-qcm.png') });
    await page.getByRole('button', { name: i === free.quiz_questions.length - 1 ? 'Valider mes réponses' : 'Suivant' }).click();
  }
  await expectText(page, `${free.quiz_questions.length} / ${free.quiz_questions.length}`);
  await expectText(page, free.quiz_questions[0].explanation.fr.slice(0, 40));
  await page.screenshot({ path: join(shots, '09-correction.png') });
});

await step('flashcards : révéler puis noter fait avancer la séance', async () => {
  await page.goto(`${base}/#/c/${free.row.id}/cards`);
  await expectText(page, '15 restantes');
  await page.getByRole('button', { name: 'Voir la définition' }).click();
  await page.screenshot({ path: join(shots, '10-flashcard.png') });
  await page.getByRole('button', { name: 'Bien', exact: true }).click();
  await expectText(page, '14 restantes');
});

await step('questions ouvertes : réponse enregistrée, éléments de réponse et auto-évaluation', async () => {
  await page.goto(`${base}/#/c/${free.row.id}/open`);
  await page.locator('textarea').first().fill('Ma réponse de test.');
  await page.getByRole('button', { name: 'Voir les éléments de réponse' }).first().click();
  await expectText(page, free.open_questions[0].model_answer.fr.slice(0, 40));
  await page.getByRole('button', { name: 'Correct', exact: true }).click();
  await page.reload();
  await expectText(page, 'Ma réponse de test.');
});

await step('offres : trois offres, prix en FCFA pour le Cameroun, puis en USD et en EUR', async () => {
  await page.goto(`${base}/#/plans`);
  const price = (code) => page.getByTestId(`price-${code}`).innerText();
  await page.getByTestId('price-monthly').waitFor();
  const digits = async (code) => (await price(code)).replace(/[^\d.,]/g, '').replace(/[\s  ]/g, '');
  if ((await digits('monthly')) !== '1700' || (await digits('yearly')) !== '11450' || (await digits('lifetime')) !== '28700') throw new Error(`prix XAF inattendus : ${await price('monthly')} / ${await price('yearly')} / ${await price('lifetime')}`);
  await page.screenshot({ path: join(shots, '11-offres-xaf.png') });
  await page.getByLabel('Devise').selectOption('USD');
  if (!/2,99/.test(await price('monthly')) || !/19,99/.test(await price('yearly')) || !/49,99/.test(await price('lifetime'))) throw new Error(`prix USD inattendus : ${await price('monthly')}`);
  await page.getByLabel('Devise').selectOption('EUR');
  if (!/2,62/.test(await price('monthly'))) throw new Error(`prix EUR inattendu : ${await price('monthly')}`);
});

await step('langues : l\'interface passe en anglais, espagnol et chinois ; le contenu suit en anglais', async () => {
  await page.goto(`${base}/#/me`);
  await page.getByLabel('Langue').selectOption('en');
  await expectText(page, 'Profile and settings');
  await page.getByLabel('Language').selectOption('es');
  await expectText(page, 'Perfil y ajustes');
  await page.getByLabel('Idioma').selectOption('zh');
  await expectText(page, '个人资料与设置');
  await page.goto(`${base}/#/d/physiologie`);
  await expectText(page, free.row.title.en);
  await page.screenshot({ path: join(shots, '12-chinois.png') });
  await page.goto(`${base}/#/me`);
  await page.getByLabel('语言').selectOption('fr');
  await expectText(page, 'Profil et réglages');
});

await step('progression : le tableau de bord et les statistiques reflètent l\'activité', async () => {
  await page.goto(`${base}/#/stats`);
  await expectText(page, '100 %');
  await expectText(page, 'Derniers résultats');
  await page.screenshot({ path: join(shots, '13-progres.png') });
});

await step('hors ligne : le chapitre déjà ouvert reste utilisable, sans perte de résultats', async () => {
  offline = true;
  await page.reload();
  await page.goto(`${base}/#/c/${free.row.id}/glossary`);
  await expectText(page, free.medical_terms[0].glossary_entries.definition.fr.slice(0, 30));
  await page.goto(`${base}/#/c/${free.row.id}/ws`);
  await page.getByTestId('ws-grid').waitFor();
  await page.goto(`${base}/#/stats`);
  await expectText(page, 'Derniers résultats');
  // QCM hors ligne sans corrigés téléchargés (invité) : message clair, réponses conservées
  await page.goto(`${base}/#/c/${free.row.id}/quiz`);
  await page.getByRole('button', { name: 'Commencer' }).click();
  for (let i = 0; i < free.quiz_questions.length - 1; i++) await page.getByRole('button', { name: 'Suivant' }).click();
  await page.getByRole('button', { name: 'Valider mes réponses' }).click();
  await expectText(page, 'La correction nécessite une connexion');
  offline = false;
});

const desk = await newPage({ width: 1280, height: 800 });
await step('ordinateur : navigation latérale et mise en page large', async () => {
  await desk.page.goto(base);
  await desk.page.getByRole('button', { name: 'Commencer' }).click();
  await expectText(desk.page, 'CHERCHE & DIAGNOSTIC');
  await desk.page.goto(`${base}/#/c/${free.row.id}/ws`);
  await desk.page.getByTestId('ws-grid').waitFor();
  await desk.page.screenshot({ path: join(shots, '14-ordinateur-grille.png') });
  await desk.page.goto(`${base}/#/admin`);
  await expectText(desk.page, 'Accès réservé à l\'équipe.');
});

await step('aucune erreur JavaScript pendant les scénarios', async () => {
  const all = [...errors, ...desk.errors];
  if (all.length) throw new Error(all.slice(0, 3).join(' | '));
});

await browser.close();
server.close();
const failed = results.filter(([, ok]) => !ok).length;
console.log(`\n${results.length - failed}/${results.length} scénarios réussis`);
process.exit(failed ? 1 : 0);
