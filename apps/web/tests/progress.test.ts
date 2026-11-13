import { test } from 'node:test';
import assert from 'node:assert/strict';
import { chapterProgress } from '../src/screens/Home.tsx';
import type { Chapter } from '../src/lib/data.ts';
import type { History } from '../src/lib/store.ts';

const ID = 'ch-1';
const chapter = (quiz_count?: number, open_count?: number): Chapter => ({
  id: ID, discipline_id: 'd', slug: 's', title: { fr: 'T' }, description: {}, sort: 1, is_free: true, status: 'in_review',
  content_version: 1, quiz_count, open_count,
});
const at = '2026-11-13T08:00:00Z';
function history(opts: { quiz?: number; open?: (number | null)[] } = {}): History {
  const cards = Object.fromEntries(Array.from({ length: 30 }, (_, i) => [`f${i}`,
    { flashcard_id: `f${i}`, chapter_id: ID, ease: 2.5, interval_days: 6, repetitions: 2, due_at: '2099-01-01T00:00:00Z', updated_at: at }]));
  return {
    lessons: { [ID]: at },
    puzzles: { p: { id: 'p', puzzle_id: 'g', chapter_id: ID, found: Array(60).fill('X'), total: 60, elapsed_s: 600, completed: true, updated_at: at } },
    cards,
    quiz: opts.quiz === undefined ? {} : { q: { id: 'q', chapter_id: ID, score: opts.quiz, total: 10, at } },
    open: Object.fromEntries((opts.open ?? []).map((s, i) => [`o${i}`, { id: `o${i}`, question_id: `oq${i}`, chapter_id: ID, answer: 'réponse', self_score: s, updated_at: at }])),
    minutes: {},
  };
}
const close = (a: number, b: number) => assert.ok(Math.abs(a - b) < 1e-9, `${a} ≠ ${b}`);

test('chapitre avec QCM : le meilleur QCM compte pour 40 %', () => {
  close(chapterProgress(history({ quiz: 5 }), ID, chapter(10, 4)).mastery, 0.6 + 0.2);
  close(chapterProgress(history({ quiz: 10 }), ID, chapter(10, 4)).mastery, 1);
});

test('chapitre de livre sans QCM : les vignettes et questions remplacent le QCM', () => {
  const open = [3, 3, 3, null, null, null, null, null, null, null, null]; // 3 vignettes réussies + 8 questions rédigées
  const p = chapterProgress(history({ open }), ID, chapter(0, 11));
  close(p.mastery, 1);
  assert.equal(p.hasQuiz, false);
  close(chapterProgress(history({ open: [3] }), ID, chapter(0, 11)).mastery, 0.6 + 0.4 / 11);
});

test('chapitre sans aucune évaluation : 100 % atteignable avec cours, grille et cartes', () => {
  close(chapterProgress(history(), ID, chapter(0, 0)).mastery, 1);
});

test('catalogue sans décompte (ancien cache) : formule d’origine', () => {
  close(chapterProgress(history({ quiz: 10 }), ID).mastery, 1);
  close(chapterProgress(history(), ID).mastery, 0.6);
});
