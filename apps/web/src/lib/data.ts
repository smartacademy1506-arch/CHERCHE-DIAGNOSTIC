// Accès aux données pédagogiques (réseau d'abord, copie locale en secours).
import { cached, kv } from './store';
import { db, getSession } from './supabase';
import type { Placement } from './wordsearch/generator';

export type I18n = Record<string, string>;
export interface Discipline { id: string; slug: string; title: I18n; description: I18n; icon: string; sort: number; status: string }
export interface Chapter { id: string; discipline_id: string; slug: string; title: I18n; description: I18n; sort: number; is_free: boolean; status: string; content_version: number }
export interface Term { id: string; label: I18n; definition: I18n }
export interface PuzzleData { id: string; language_code: string; size: number; grid: string[]; words: (Placement & { term_id: string })[] }
export interface Question { id: string; type: 'single' | 'multiple'; difficulty: number; stem: I18n; options: { id: string; label: I18n }[] }
export interface OpenQuestion { id: string; question: I18n; model_answer: I18n | null }
export interface Flashcard { id: string; front: I18n; back: I18n }
export interface AnswerKey { correct: string[]; explanation: I18n }
export interface ChapterBundle {
  chapter_id: string; content_version: number; fetched_at: string;
  lesson: { title: I18n; summary: I18n; key_points: I18n[]; source_refs: { citation: string; url: string }[]; status: string } | null;
  objectives: I18n[];
  terms: Term[];
  puzzles: PuzzleData[];
  questions: Question[];
  open_questions: OpenQuestion[];
  flashcards: Flashcard[];
  keys?: Record<string, AnswerKey>; // corrigés téléchargés pour le mode hors ligne (utilisateurs connectés)
}

export const loadCatalog = () => cached('catalog', async () => {
  const [disciplines, chapters] = await Promise.all([
    db.select<Discipline>('disciplines', 'select=id,slug,title,description,icon,sort,status&order=sort'),
    db.select<Chapter>('chapters', 'select=id,discipline_id,slug,title,description,sort,is_free,status,content_version&order=sort'),
  ]);
  return { disciplines, chapters };
});

export const loadRefs = () => cached('refs', async () => {
  const [languages, countries, currencies, plans, planPrices] = await Promise.all([
    db.select('languages', 'select=code,native_name,is_content_language&is_active=eq.true&order=sort'),
    db.select('countries', 'select=code,name,currency_code,default_language&is_active=eq.true'),
    db.select('currencies', 'select=code,name,symbol,usd_rate,decimals,rounding&is_active=eq.true&order=code'),
    db.select('plans', 'select=id,code,name,description,features,billing_period,price_usd,is_featured,sort&is_active=eq.true&order=sort'),
    db.select('plan_prices', 'select=plan_id,currency_code,amount'),
  ]);
  return { languages, countries, currencies, plans, planPrices };
});

const bundleKey = (id: string) => `chapter:${id}`;

async function fetchBundle(chapter: Chapter, withKeys: boolean): Promise<ChapterBundle> {
  const f = `chapter_id=eq.${chapter.id}`;
  const [lessons, objectives, terms, puzzles, questions, open, cards] = await Promise.all([
    db.select('lessons', `select=title,summary,key_points,source_refs,status&${f}&order=sort&limit=1`),
    db.select('learning_objectives', `select=body&${f}&order=sort`),
    db.select('medical_terms', `select=id,label,glossary_entries(definition)&${f}&order=sort`),
    db.select('word_search_puzzles', `select=id,language_code,size,grid,puzzle_words(term_id,word,start_row,start_col,d_row,d_col)&${f}&validated_at=not.is.null`),
    db.select('quiz_questions', `select=id,type,difficulty,stem,quiz_options(id,label,sort)&${f}&order=sort`),
    db.select('open_questions', `select=id,question,model_answer&${f}&order=sort`),
    db.select('flashcards', `select=id,front,back&${f}&order=sort`),
  ]);
  const bundle: ChapterBundle = {
    chapter_id: chapter.id, content_version: chapter.content_version, fetched_at: new Date().toISOString(),
    lesson: lessons[0] ?? null,
    objectives: objectives.map((o: any) => o.body),
    terms: terms.map((t: any) => {
      const g = Array.isArray(t.glossary_entries) ? t.glossary_entries[0] : t.glossary_entries;
      return { id: t.id, label: t.label, definition: g?.definition ?? {} };
    }),
    puzzles: puzzles.map((p: any) => ({
      id: p.id, language_code: p.language_code, size: p.size, grid: p.grid,
      words: p.puzzle_words.map((w: any, i: number) => ({ term_index: i, term_id: w.term_id, word: w.word, row: w.start_row, col: w.start_col, d_row: w.d_row, d_col: w.d_col })),
    })),
    questions: questions.map((q: any) => ({ id: q.id, type: q.type, difficulty: q.difficulty, stem: q.stem, options: [...q.quiz_options].sort((a, b) => a.sort - b.sort).map((o: any) => ({ id: o.id, label: o.label })) })),
    open_questions: open,
    flashcards: cards,
  };
  if (withKeys && getSession()) {
    try { bundle.keys = await db.rpc('get_offline_keys', { p_chapter_id: chapter.id }); } catch { /* corrigés indisponibles : QCM en ligne seulement */ }
  }
  return bundle;
}

/** Contenu d'un chapitre. Une copie locale à jour est utilisée directement (lecture hors ligne, moins de données). */
export async function loadChapter(chapter: Chapter): Promise<{ data: ChapterBundle; stale: boolean }> {
  const local = await kv.get<ChapterBundle>(bundleKey(chapter.id));
  if (local && local.content_version === chapter.content_version && local.terms.length > 0) return { data: local, stale: false };
  return cached(bundleKey(chapter.id), () => fetchBundle(chapter, !!local?.keys));
}

/** Téléchargement explicite pour le mode hors ligne (avec les corrigés si l'utilisateur est connecté). */
export async function downloadChapter(chapter: Chapter): Promise<ChapterBundle> {
  const bundle = await fetchBundle(chapter, true);
  await kv.set(bundleKey(chapter.id), bundle);
  const list = new Set((await kv.get<string[]>('downloads')) ?? []);
  list.add(chapter.id);
  await kv.set('downloads', [...list]);
  return bundle;
}
export async function removeDownload(chapterId: string): Promise<void> {
  await kv.del(bundleKey(chapterId));
  await kv.set('downloads', ((await kv.get<string[]>('downloads')) ?? []).filter((x) => x !== chapterId));
}
export const listDownloads = async () => (await kv.get<string[]>('downloads')) ?? [];
