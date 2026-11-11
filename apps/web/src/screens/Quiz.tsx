// QCM : réponse unique ou multiple, chronomètre facultatif, correction détaillée.
// La correction est faite par le serveur ; hors ligne, elle se fait avec les corrigés téléchargés
// et le résultat est mis en file d'attente (même identifiant de tentative => aucun doublon).
import { useEffect, useRef, useState } from 'react';
import { useApp } from '../app';
import type { AnswerKey, ChapterBundle, I18n, Question } from '../lib/data';
import { enqueue, updateHistory, uuid } from '../lib/store';
import { ApiError, db } from '../lib/supabase';
import { Bar, Button, Card, Icon, Notice, Tag, formatTime } from '../ui';
import { ChapterFrame } from './Chapter';
import { useStudyTimer } from './Home';

interface Result { question_id: string; selected: string[]; correct: string[]; is_correct: boolean; explanation: I18n }
interface Outcome { score: number; total: number; results: Result[]; queued: boolean }

/** Correction locale, identique à la règle du serveur : la sélection doit être exactement l'ensemble des bonnes réponses. */
export function gradeLocally(questions: Question[], answers: Record<string, string[]>, keys: Record<string, AnswerKey>): Outcome | null {
  const results: Result[] = [];
  for (const q of questions) {
    const k = keys[q.id];
    if (!k) return null;
    const sel = (answers[q.id] ?? []).filter((id) => q.options.some((o) => o.id === id));
    const ok = sel.length > 0 && sel.length === k.correct.length && sel.every((id) => k.correct.includes(id));
    results.push({ question_id: q.id, selected: sel, correct: k.correct, is_correct: ok, explanation: k.explanation });
  }
  return { score: results.filter((r) => r.is_correct).length, total: results.length, results, queued: true };
}

export function QuizScreen({ id }: { id: string }) {
  const { t } = useApp();
  useStudyTimer('quiz', id);
  return <ChapterFrame id={id} title={t('ch.quiz')}>{(b) => <QuizRun key={b.fetched_at} bundle={b} chapterId={id} />}</ChapterFrame>;
}

function QuizRun({ bundle, chapterId }: { bundle: ChapterBundle; chapterId: string }) {
  const { t, tr, session } = useApp();
  const questions = bundle.questions;
  const [phase, setPhase] = useState<'intro' | 'run' | 'done'>('intro');
  const [timed, setTimed] = useState(false);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [elapsed, setElapsed] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const attemptId = useRef(uuid());
  const limit = questions.length * 75; // 75 secondes par question en mode chronométré

  useEffect(() => {
    if (phase !== 'run') return;
    const timer = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => window.clearInterval(timer);
  }, [phase]);
  useEffect(() => { if (phase === 'run' && timed && elapsed >= limit && !busy) void submit(); /* temps écoulé */ // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elapsed]);

  function toggle(q: Question, optionId: string) {
    setAnswers((a) => {
      const cur = a[q.id] ?? [];
      if (q.type === 'single') return { ...a, [q.id]: [optionId] };
      return { ...a, [q.id]: cur.includes(optionId) ? cur.filter((x) => x !== optionId) : [...cur, optionId] };
    });
  }

  async function submit() {
    setBusy(true); setError(null);
    const full: Record<string, string[]> = Object.fromEntries(questions.map((q) => [q.id, answers[q.id] ?? []]));
    const args = { p_attempt_id: attemptId.current, p_chapter_id: chapterId, p_answers: full, p_duration_s: elapsed, p_mode: timed ? 'timed' : 'practice', p_client_ts: new Date().toISOString() };
    let result: Outcome | null = null;
    try {
      const r = await db.rpc<{ score: number; total: number; results: Result[] }>('submit_quiz_attempt', args);
      result = { ...r, queued: false };
    } catch (e) {
      if (e instanceof ApiError && !e.retryable) { setError(e.message || t('error')); setBusy(false); return; }
      result = bundle.keys ? gradeLocally(questions, full, bundle.keys) : null;
      if (result && session) void enqueue('quiz', args, attemptId.current);
    }
    setBusy(false);
    if (!result) { setError(t('quiz.need_online')); return; }
    setOutcome(result); setPhase('done');
    const rec = { id: attemptId.current, chapter_id: chapterId, score: result.score, total: result.total, at: new Date().toISOString() };
    void updateHistory((h) => { h.quiz[rec.id] = rec; });
  }

  function restart() {
    attemptId.current = uuid();
    setAnswers({}); setIndex(0); setElapsed(0); setOutcome(null); setError(null); setPhase('intro');
  }

  if (phase === 'intro') {
    return (
      <Card className="result">
        <span className="disc-icon"><Icon name="quiz" /></span>
        <p className="score">{questions.length} {t('quiz.intro')}</p>
        <label className="check center"><input type="checkbox" checked={timed} onChange={(e) => setTimed(e.target.checked)} /><span>{t('quiz.timed')} ({formatTime(limit)})</span></label>
        <Button icon="play" onClick={() => setPhase('run')}>{t('start')}</Button>
      </Card>
    );
  }

  if (phase === 'done' && outcome) {
    const byId = new Map(outcome.results.map((r) => [r.question_id, r]));
    return (
      <div className="stack">
        <Card className="result">
          <h2>{t('quiz.result')}</h2>
          <p className="score">{outcome.score} / {outcome.total}</p>
          <p className="muted">{Math.round((outcome.score / outcome.total) * 100)} % · {formatTime(elapsed)}</p>
          {outcome.queued && session && <Notice>{t('quiz.queued')}</Notice>}
          <Button icon="repeat" onClick={restart}>{t('quiz.again')}</Button>
        </Card>
        {questions.map((q, i) => {
          const r = byId.get(q.id);
          if (!r) return null;
          return (
            <Card key={q.id} className="correction">
              <div className="row"><Tag kind={r.is_correct ? 'free' : 'review'}>{t(r.is_correct ? 'quiz.correct' : r.selected.length ? 'quiz.wrong' : 'quiz.unanswered')}</Tag></div>
              <strong>{i + 1}. {tr(q.stem)}</strong>
              <ul className="options">
                {q.options.map((o) => {
                  const good = r.correct.includes(o.id), picked = r.selected.includes(o.id);
                  return (
                    <li key={o.id} className={`option is-static${good ? ' is-good' : picked ? ' is-bad' : ''}`}>
                      <span className="mark">{good ? <Icon name="check" size={16} /> : picked ? <Icon name="x" size={16} /> : null}</span>
                      <span>{tr(o.label)}</span>
                    </li>
                  );
                })}
              </ul>
              <p className="explain">{tr(r.explanation)}</p>
            </Card>
          );
        })}
      </div>
    );
  }

  const q = questions[index];
  const picked = answers[q.id] ?? [];
  const last = index === questions.length - 1;
  return (
    <div className="stack">
      <div className="row">
        <strong>{index + 1} / {questions.length}</strong>
        <span className="grow" />
        {timed && <span className={`ws-time${limit - elapsed < 30 ? ' is-late' : ''}`}><Icon name="clock" size={16} /> {formatTime(Math.max(0, limit - elapsed))}</span>}
      </div>
      <Bar value={(index + 1) / questions.length} />
      <Card>
        <p className="small muted">{t(q.type === 'single' ? 'quiz.one' : 'quiz.many')}</p>
        <p className="stem">{tr(q.stem)}</p>
        <ul className="options" role={q.type === 'single' ? 'radiogroup' : 'group'}>
          {q.options.map((o) => {
            const on = picked.includes(o.id);
            return (
              <li key={o.id}>
                <button type="button" className={`option${on ? ' is-on' : ''}`} role={q.type === 'single' ? 'radio' : 'checkbox'} aria-checked={on} onClick={() => toggle(q, o.id)}>
                  <span className={`mark ${q.type === 'single' ? 'mark-radio' : 'mark-box'}`}>{on && <Icon name="check" size={14} />}</span>
                  <span>{tr(o.label)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </Card>
      {error && <Notice kind="error">{error}</Notice>}
      <div className="row">
        <Button variant="ghost" disabled={index === 0} onClick={() => setIndex((i) => i - 1)}>{t('back')}</Button>
        <span className="grow" />
        {last ? <Button disabled={busy} onClick={() => void submit()}>{busy ? t('loading') : t('quiz.validate')}</Button> : <Button onClick={() => setIndex((i) => i + 1)}>{t('next')}</Button>}
      </div>
    </div>
  );
}
