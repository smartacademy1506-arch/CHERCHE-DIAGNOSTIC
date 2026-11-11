// Stockage local (IndexedDB) : cache des contenus, historique des résultats et file de synchronisation.
// L'interface lit toujours le stockage local ; le réseau ne sert qu'à le remplir et à le synchroniser.
import { ApiError, db, getSession } from './supabase';

const DB_NAME = 'cherche-diagnostic';
let dbp: Promise<IDBDatabase> | null = null;

function open(): Promise<IDBDatabase> {
  dbp ??= new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore('kv');
      req.result.createObjectStore('outbox', { keyPath: 'id' });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbp;
}
function tx<T>(store: string, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return open().then((d) => new Promise<T>((resolve, reject) => {
    const req = fn(d.transaction(store, mode).objectStore(store));
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  }));
}

export const kv = {
  get: <T = any>(key: string) => tx<T | undefined>('kv', 'readonly', (s) => s.get(key)),
  set: (key: string, value: unknown) => tx('kv', 'readwrite', (s) => s.put(value, key)),
  del: (key: string) => tx('kv', 'readwrite', (s) => s.delete(key)),
  keys: () => tx<IDBValidKey[]>('kv', 'readonly', (s) => s.getAllKeys()),
};

/** Réseau d'abord ; en cas d'échec, dernière copie locale. `stale` indique une copie hors ligne. */
export async function cached<T>(key: string, fetcher: () => Promise<T>): Promise<{ data: T; stale: boolean }> {
  try {
    const data = await fetcher();
    await kv.set(key, data);
    return { data, stale: false };
  } catch (e) {
    const local = await kv.get<T>(key);
    if (local !== undefined) return { data: local, stale: true };
    throw e;
  }
}

// ───────────── Historique local des résultats (invités et utilisateurs connectés) ─────────────
export interface History {
  quiz: Record<string, { id: string; chapter_id: string; score: number; total: number; at: string }>;
  puzzles: Record<string, { id: string; puzzle_id: string; chapter_id: string; found: string[]; total: number; elapsed_s: number; completed: boolean; updated_at: string }>;
  cards: Record<string, { flashcard_id: string; chapter_id: string; ease: number; interval_days: number; repetitions: number; due_at: string; updated_at: string }>;
  open: Record<string, { id: string; question_id: string; chapter_id: string; answer: string; self_score: number | null; updated_at: string }>;
  lessons: Record<string, string>; // chapter_id -> date de lecture
  minutes: Record<string, number>; // jour (AAAA-MM-JJ) -> secondes d'étude
}
const emptyHistory = (): History => ({ quiz: {}, puzzles: {}, cards: {}, open: {}, lessons: {}, minutes: {} });
const historyKey = () => `history:${getSession()?.user.id ?? 'guest'}`;
const historyListeners = new Set<() => void>();
export const onHistoryChange = (l: () => void) => { historyListeners.add(l); return () => { historyListeners.delete(l); }; };

export async function getHistory(): Promise<History> {
  return { ...emptyHistory(), ...((await kv.get<History>(historyKey())) ?? {}) };
}
export async function updateHistory(fn: (h: History) => void): Promise<History> {
  const h = await getHistory();
  fn(h);
  await kv.set(historyKey(), h);
  historyListeners.forEach((l) => l());
  return h;
}

// ───────────── File de synchronisation ─────────────
// Chaque résultat porte un identifiant généré sur l'appareil : le rejouer ne crée jamais de doublon.
export type OutboxKind = 'quiz' | 'puzzle' | 'open' | 'card' | 'lesson' | 'time';
interface OutboxItem { id: string; kind: OutboxKind; payload: any; created_at: string; user_id: string; error?: string }

export const uuid = (): string => crypto.randomUUID();

export async function enqueue(kind: OutboxKind, payload: any, id: string = uuid()): Promise<void> {
  const s = getSession();
  if (!s) return; // invité : le résultat reste dans l'historique local uniquement
  await tx('outbox', 'readwrite', (st) => st.put({ id: `${kind}:${id}`, kind, payload, created_at: new Date().toISOString(), user_id: s.user.id }));
  void flushOutbox();
}

async function send(item: OutboxItem, userId: string): Promise<void> {
  const p = item.payload;
  switch (item.kind) {
    case 'quiz':
      await db.rpc('submit_quiz_attempt', p); break;
    case 'puzzle':
      await db.upsert('puzzle_sessions', { ...p, user_id: userId }); break;
    case 'open':
      await db.upsert('open_question_submissions', { ...p, user_id: userId }, 'user_id,question_id'); break;
    case 'card':
      await db.upsert('flashcard_states', { ...p.state, user_id: userId });
      await db.insert('flashcard_reviews', { ...p.review, user_id: userId }, 'resolution=ignore-duplicates,return=minimal'); break;
    case 'lesson':
      await db.upsert('user_progress', { ...p, user_id: userId }); break;
    case 'time':
      await db.insert('learning_sessions', { ...p, user_id: userId }, 'resolution=ignore-duplicates,return=minimal'); break;
  }
}

let flushing: Promise<number> | null = null;
/** Envoie les résultats en attente. Renvoie le nombre d'éléments restants. */
export function flushOutbox(): Promise<number> {
  flushing ??= (async () => {
    try {
      const s = getSession();
      const items = await tx<OutboxItem[]>('outbox', 'readonly', (st) => st.getAll());
      if (!s || !navigator.onLine) return items.length;
      let left = 0;
      for (const item of items.sort((a, b) => a.created_at.localeCompare(b.created_at))) {
        if (item.user_id !== s.user.id || item.error) { left++; continue; } // autre compte ou erreur définitive : conservé, jamais supprimé en silence
        try {
          await send(item, s.user.id);
          await tx('outbox', 'readwrite', (st) => st.delete(item.id));
        } catch (e) {
          left++;
          if (e instanceof ApiError && !e.retryable && e.status !== 409) {
            await tx('outbox', 'readwrite', (st) => st.put({ ...item, error: `${e.status} ${e.message}` }));
          } else if (e instanceof ApiError && e.status === 409) {
            await tx('outbox', 'readwrite', (st) => st.delete(item.id)); left--; // déjà enregistré
          } else break; // réseau indisponible : on réessaiera
        }
      }
      return left;
    } finally { flushing = null; }
  })();
  return flushing;
}
export const outboxCount = () => tx<number>('outbox', 'readonly', (st) => st.count());

/** À la connexion : fusionne l'historique du serveur dans l'historique local (le plus récent l'emporte). */
export async function pullHistory(): Promise<void> {
  const s = getSession();
  if (!s) return;
  const [attempts, sessions, states, subs, progress] = await Promise.all([
    db.select('quiz_attempts', 'select=id,chapter_id,score,total,submitted_at&order=submitted_at.desc&limit=500'),
    db.select('puzzle_sessions', 'select=id,puzzle_id,found_term_ids,words_total,elapsed_s,completed,updated_at,word_search_puzzles(chapter_id)&limit=500'),
    db.select('flashcard_states', 'select=flashcard_id,ease,interval_days,repetitions,due_at,updated_at,flashcards(chapter_id)&limit=5000'),
    db.select('open_question_submissions', 'select=id,question_id,answer,self_score,updated_at,open_questions(chapter_id)&limit=1000'),
    db.select('user_progress', 'select=chapter_id,lesson_read_at'),
  ]);
  const newer = (a?: string, b?: string) => !a || (b ?? '') > a;
  await updateHistory((h) => {
    for (const a of attempts) h.quiz[a.id] ??= { id: a.id, chapter_id: a.chapter_id, score: a.score, total: a.total, at: a.submitted_at };
    for (const p of sessions) if (newer(h.puzzles[p.puzzle_id]?.updated_at, p.updated_at))
      h.puzzles[p.puzzle_id] = { id: p.id, puzzle_id: p.puzzle_id, chapter_id: p.word_search_puzzles?.chapter_id, found: p.found_term_ids, total: p.words_total, elapsed_s: p.elapsed_s, completed: p.completed, updated_at: p.updated_at };
    for (const c of states) if (newer(h.cards[c.flashcard_id]?.updated_at, c.updated_at))
      h.cards[c.flashcard_id] = { flashcard_id: c.flashcard_id, chapter_id: c.flashcards?.chapter_id, ease: Number(c.ease), interval_days: c.interval_days, repetitions: c.repetitions, due_at: c.due_at, updated_at: c.updated_at };
    for (const o of subs) if (newer(h.open[o.question_id]?.updated_at, o.updated_at))
      h.open[o.question_id] = { id: o.id, question_id: o.question_id, chapter_id: o.open_questions?.chapter_id, answer: o.answer, self_score: o.self_score, updated_at: o.updated_at };
    for (const p of progress) if (p.lesson_read_at) h.lessons[p.chapter_id] ??= p.lesson_read_at;
  });
}
