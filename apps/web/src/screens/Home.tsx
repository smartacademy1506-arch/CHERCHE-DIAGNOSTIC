// Tableau de bord, catalogue des disciplines, liste des chapitres et statistiques.
import { useEffect, useRef } from 'react';
import { useApp } from '../app';
import type { Chapter } from '../lib/data';
import { isDue } from '../lib/srs';
import { enqueue, updateHistory, uuid, type History } from '../lib/store';
import { Bar, Button, Card, Header, Icon, Loader, Notice, Ring, Tag } from '../ui';

const today = () => new Date().toISOString().slice(0, 10);

/** Compte le temps passé sur une activité et l'enregistre en quittant l'écran. */
export function useStudyTimer(activity: 'lesson' | 'word_search' | 'quiz' | 'open_question' | 'flashcards' | 'glossary', chapterId: string | null) {
  const start = useRef(Date.now());
  useEffect(() => {
    start.current = Date.now();
    return () => {
      const s = Math.min(3 * 3600, Math.round((Date.now() - start.current) / 1000));
      if (s < 5) return;
      void updateHistory((h) => { h.minutes[today()] = (h.minutes[today()] ?? 0) + s; });
      void enqueue('time', { id: uuid(), chapter_id: chapterId, activity, duration_s: s, started_at: new Date(start.current).toISOString() });
    };
  }, [activity, chapterId]);
}

export interface ChapterProgress { lesson: boolean; puzzle: number; quizBest: number | null; quizCount: number; cards: number; due: number; mastery: number; active: boolean; last: string; hasQuiz: boolean; hasOpen: boolean }

/**
 * Indicateur de maîtrise PÉDAGOGIQUE d'un chapitre (0 à 1) : cours lu 15 %, grille 25 %, cartes apprises 20 %,
 * évaluation 40 %. L'évaluation est le meilleur QCM ; un chapitre sans QCM (les livres de la collection) est évalué
 * par ses vignettes et questions ouvertes (auto-évaluation sur 3, réponse écrite sans corrigé = faite) ; un chapitre
 * sans aucune évaluation répartit les 40 % sur les trois autres activités.
 */
export function chapterProgress(h: History | null, chapterId: string, chapter?: Chapter): ChapterProgress {
  const hasQuiz = chapter?.quiz_count === undefined ? true : chapter.quiz_count > 0;
  const openTotal = chapter?.open_count ?? 0;
  const empty: ChapterProgress = { lesson: false, puzzle: 0, quizBest: null, quizCount: 0, cards: 0, due: 0, mastery: 0, active: false, last: '', hasQuiz, hasOpen: openTotal > 0 };
  if (!h) return empty;
  const quizzes = Object.values(h.quiz).filter((q) => q.chapter_id === chapterId);
  const puzzles = Object.values(h.puzzles).filter((p) => p.chapter_id === chapterId);
  const cards = Object.values(h.cards).filter((c) => c.chapter_id === chapterId);
  const lesson = !!h.lessons[chapterId];
  const puzzle = puzzles.reduce((m, p) => Math.max(m, p.found.length / Math.max(1, p.total)), 0);
  const quizBest = quizzes.length ? Math.max(...quizzes.map((q) => q.score / q.total)) : null;
  const learned = cards.filter((c) => c.repetitions >= 2).length;
  const opens = Object.values(h.open).filter((o) => o.chapter_id === chapterId);
  const openScore = openTotal > 0 ? Math.min(1, opens.reduce((s, o) => s + (o.self_score === null ? 1 : o.self_score / 3), 0) / openTotal) : null;
  const evaluation = hasQuiz ? quizBest ?? 0 : openScore;
  const base = (lesson ? 0.15 : 0) + puzzle * 0.25 + Math.min(1, learned / 30) * 0.2;
  const mastery = evaluation === null ? base / 0.6 : base + evaluation * 0.4;
  const last = [h.lessons[chapterId] ?? '', ...quizzes.map((q) => q.at), ...puzzles.map((p) => p.updated_at), ...cards.map((c) => c.updated_at), ...opens.map((o) => o.updated_at)].sort().pop() ?? '';
  return { lesson, puzzle, quizBest, quizCount: quizzes.length, cards: learned, due: cards.filter((c) => isDue(c)).length, mastery, active: !!last, last, hasQuiz, hasOpen: openTotal > 0 };
}

function nextStep(p: ChapterProgress): { key: string; path: string } {
  if (!p.lesson) return { key: 'reco.lesson', path: 'lesson' };
  if (p.puzzle < 1) return { key: 'reco.puzzle', path: 'ws' };
  if (p.due > 0 || p.cards < 10) return { key: 'reco.cards', path: 'cards' };
  if (!p.hasQuiz && p.hasOpen) return { key: 'reco.open', path: 'open' };
  return { key: 'reco.quiz', path: 'quiz' };
}

function ChapterRow({ chapter }: { chapter: Chapter }) {
  const { tr, t, go, canOpen, history } = useApp();
  const p = chapterProgress(history, chapter.id, chapter);
  const open = canOpen(chapter);
  return (
    <Card onClick={() => go(open ? `c/${chapter.id}` : 'plans')} className="row">
      <span className="chapter-no">{String(chapter.sort).padStart(2, '0')}</span>
      <div className="grow">
        <strong>{tr(chapter.title)}</strong>
        <p className="muted small">{tr(chapter.description)}</p>
      </div>
      {p.active ? <Ring value={p.mastery} /> : open ? <Tag kind={chapter.is_free ? 'free' : 'premium'}>{t(chapter.is_free ? 'free' : 'premium')}</Tag> : <span className="lock" aria-label={t('premium')}><Icon name="lock" size={18} /></span>}
    </Card>
  );
}

export function Home() {
  const { t, tr, go, profile, session, chapters, disciplines, history, catalogState, canOpen, reloadCatalog } = useApp();
  if (catalogState === 'loading') return <Loader text={t('loading')} />;
  if (catalogState === 'error') return <div className="pad"><Notice kind="warn">{t('ch.unavailable')}</Notice><Button onClick={() => void reloadCatalog()}>{t('retry')}</Button></div>;

  const progress = chapters.map((c) => ({ c, p: chapterProgress(history, c.id, c) }));
  const current = progress.filter((x) => x.p.active && canOpen(x.c)).sort((a, b) => b.p.last.localeCompare(a.p.last))[0] ?? progress.find((x) => canOpen(x.c));
  const due = Object.values(history?.cards ?? {}).filter((c) => isDue(c)).length;
  const goal = (profile?.daily_goal_minutes ?? 20) * 60;
  const doneToday = history?.minutes[today()] ?? 0;
  const quizzes = Object.values(history?.quiz ?? {});
  const avg = quizzes.length ? quizzes.reduce((s, q) => s + q.score / q.total, 0) / quizzes.length : null;
  const withChapters = disciplines.filter((d) => chapters.some((c) => c.discipline_id === d.id));
  const firstName = profile?.full_name?.split(' ')[0];

  return (
    <div className="page">
      <section className="hero">
        <h1>{t('home.hello')}{firstName ? `, ${firstName}` : ''}</h1>
        {!session && <Button variant="soft" onClick={() => go('auth')}>{t('auth.login')}</Button>}
      </section>

      {current && (
        <section>
          <h2>{t('home.continue')}</h2>
          <Card onClick={() => go(`c/${current.c.id}/${current.p.active ? nextStep(current.p).path : ''}`.replace(/\/$/, ''))} className="row feature">
            <div className="grow">
              <strong>{tr(current.c.title)}</strong>
              <p className="small">{current.p.active ? t(nextStep(current.p).key) : t('home.empty')}</p>
            </div>
            {current.p.active ? <Ring value={current.p.mastery} /> : <Icon name="play" />}
          </Card>
        </section>
      )}

      <section className="grid-2">
        <Card onClick={() => go('review')} className="stat">
          <span className="stat-num">{due}</span>
          <span className="muted">{due ? t('home.due') : t('home.none_due')}</span>
          <span className="stat-label">{t('home.today')}</span>
        </Card>
        <Card className="stat">
          <span className="stat-num">{Math.round(doneToday / 60)}<small> / {Math.round(goal / 60)} min</small></span>
          <Bar value={doneToday / goal} />
          <span className="stat-label">{t('home.goal')}</span>
        </Card>
      </section>

      <section>
        <h2>{t('home.disciplines')}</h2>
        <div className="stack">
          {withChapters.map((d) => {
            const list = chapters.filter((c) => c.discipline_id === d.id);
            const m = list.reduce((s, c) => s + chapterProgress(history, c.id, c).mastery, 0) / list.length;
            return (
              <Card key={d.id} onClick={() => go(`d/${d.slug}`)} className="row">
                <span className="disc-icon"><Icon name={d.icon} /></span>
                <div className="grow"><strong>{tr(d.title)}</strong><Bar value={m} /></div>
                <span className="muted small">{list.length} {t('cat.chapters')}</span>
              </Card>
            );
          })}
        </div>
      </section>

      <section>
        <h2>{t('home.results')}</h2>
        <Card onClick={() => go('stats')} className="row">
          {avg === null ? <p className="muted grow">{t('stats.empty')}</p> : <><Ring value={avg} /><div className="grow"><strong>{t('stats.quiz')}</strong><p className="muted small">{quizzes.length} {t('ch.quiz')}</p></div></>}
          <Icon name="chart" />
        </Card>
      </section>
    </div>
  );
}

export function Catalog() {
  const { t, tr, go, disciplines, chapters, catalogState } = useApp();
  if (catalogState === 'loading') return <Loader text={t('loading')} />;
  return (
    <div className="page">
      <Header title={t('cat.title')} />
      <div className="tiles">
        {disciplines.map((d) => {
          const n = chapters.filter((c) => c.discipline_id === d.id).length;
          return (
            <Card key={d.id} onClick={n ? () => go(`d/${d.slug}`) : undefined} className={`tile${n ? '' : ' tile-soon'}`}>
              <strong>{tr(d.title)}</strong>
              <span className="muted small">{n ? `${n} ${t('cat.chapters')}` : t('soon')}</span>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export function DisciplineScreen({ slug }: { slug: string }) {
  const { t, tr, back, disciplines, chapters, catalogState } = useApp();
  const d = disciplines.find((x) => x.slug === slug);
  if (catalogState === 'loading') return <Loader text={t('loading')} />;
  if (!d) return <div className="pad"><Notice kind="warn">{t('ch.unavailable')}</Notice></div>;
  const list = chapters.filter((c) => c.discipline_id === d.id);
  return (
    <div className="page">
      <Header title={tr(d.title)} onBack={back} />
      <div className="stack">{list.map((c) => <ChapterRow key={c.id} chapter={c} />)}</div>
    </div>
  );
}

export function Stats() {
  const { t, tr, go, history, chapters } = useApp();
  const quizzes = Object.values(history?.quiz ?? {}).sort((a, b) => b.at.localeCompare(a.at));
  const puzzlesDone = Object.values(history?.puzzles ?? {}).filter((p) => p.completed).length;
  const cards = Object.values(history?.cards ?? {}).filter((c) => c.repetitions >= 2).length;
  const days = Array.from({ length: 7 }, (_, i) => new Date(Date.now() - (6 - i) * 86_400_000).toISOString().slice(0, 10));
  const secs = days.map((d) => history?.minutes[d] ?? 0);
  const max = Math.max(600, ...secs);
  const prog = chapters.map((c) => ({ c, p: chapterProgress(history, c.id, c) })).filter((x) => x.p.active);
  const strong = prog.filter((x) => x.p.mastery >= 0.7);
  const weak = prog.filter((x) => x.p.mastery < 0.7).sort((a, b) => a.p.mastery - b.p.mastery);
  const avg = quizzes.length ? quizzes.reduce((s, q) => s + q.score / q.total, 0) / quizzes.length : 0;
  const empty = !quizzes.length && !prog.length;

  return (
    <div className="page">
      <Header title={t('stats.title')} />
      {empty && <Notice>{t('stats.empty')}</Notice>}
      <section className="grid-3">
        <Card className="stat"><span className="stat-num">{quizzes.length ? `${Math.round(avg * 100)} %` : '—'}</span><span className="stat-label">{t('stats.quiz')}</span></Card>
        <Card className="stat"><span className="stat-num">{puzzlesDone}</span><span className="stat-label">{t('stats.puzzles')}</span></Card>
        <Card className="stat"><span className="stat-num">{cards}</span><span className="stat-label">{t('stats.cards')}</span></Card>
      </section>
      <section>
        <h2>{t('stats.time')}</h2>
        <Card>
          <div className="chart" role="img" aria-label={t('stats.time')}>
            {secs.map((s, i) => (
              <div key={days[i]} className="chart-col">
                <span className="small muted">{Math.round(s / 60)}</span>
                <div className="chart-bar" style={{ height: `${(s / max) * 100}%` }} />
                <span className="small muted">{days[i].slice(8)}</span>
              </div>
            ))}
          </div>
        </Card>
      </section>
      {weak.length > 0 && (
        <section>
          <h2>{t('stats.weak')}</h2>
          <div className="stack">
            {weak.map(({ c, p }) => {
              const step = nextStep(p);
              return (
                <Card key={c.id} onClick={() => go(`c/${c.id}/${step.path}`)} className="row">
                  <Ring value={p.mastery} size={48} />
                  <div className="grow"><strong>{tr(c.title)}</strong><p className="small muted">{t('stats.reco')} : {t(step.key)}</p></div>
                </Card>
              );
            })}
          </div>
        </section>
      )}
      {strong.length > 0 && (
        <section>
          <h2>{t('stats.strong')}</h2>
          <div className="stack">{strong.map(({ c, p }) => <Card key={c.id} onClick={() => go(`c/${c.id}`)} className="row"><Ring value={p.mastery} size={48} /><strong className="grow">{tr(c.title)}</strong></Card>)}</div>
        </section>
      )}
      {quizzes.length > 0 && (
        <section>
          <h2>{t('stats.history')}</h2>
          <Card>
            <ul className="plain">
              {quizzes.slice(0, 10).map((q) => (
                <li key={q.id} className="row">
                  <span className="grow">{tr(chapters.find((c) => c.id === q.chapter_id)?.title)}</span>
                  <span className="muted small">{new Date(q.at).toLocaleDateString()}</span>
                  <strong>{q.score}/{q.total}</strong>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      )}
    </div>
  );
}
