// Flashcards d'un chapitre et révisions quotidiennes (répétition espacée).
import { useEffect, useState } from 'react';
import { useApp } from '../app';
import { loadChapter, type Flashcard } from '../lib/data';
import { isDue, NEW_CARD, review, type Rating } from '../lib/srs';
import { enqueue, updateHistory, uuid, type History } from '../lib/store';
import { Bar, Button, Card, Header, Loader, Notice } from '../ui';
import { ChapterFrame } from './Chapter';
import { useStudyTimer } from './Home';

interface Item { card: Flashcard; chapterId: string }
const SESSION_NEW = 15; // nouvelles cartes par séance

/** File d'une séance : d'abord les cartes dues, puis quelques nouvelles cartes. */
export function buildQueue(cards: Item[], h: History | null, now = new Date()): Item[] {
  const due = cards.filter((x) => h?.cards[x.card.id] && isDue(h.cards[x.card.id], now));
  const fresh = cards.filter((x) => !h?.cards[x.card.id]).slice(0, SESSION_NEW);
  return [...due, ...fresh];
}

function Session({ initial, onExit }: { initial: Item[]; onExit: () => void }) {
  const { t, tr, history } = useApp();
  const [queue, setQueue] = useState<Item[]>(initial);
  const [revealed, setRevealed] = useState(false);
  const [count, setCount] = useState(0);
  const total = initial.length;

  if (queue.length === 0) {
    return (
      <Card className="result">
        <h2>{t('fc.done')}</h2>
        <p className="score">{count}</p>
        <Button onClick={onExit}>{t('continue')}</Button>
      </Card>
    );
  }
  const { card, chapterId } = queue[0];

  function rate(rating: Rating) {
    const now = new Date();
    const prev = history?.cards[card.id];
    const next = review(prev ?? NEW_CARD, rating, now);
    const state = { flashcard_id: card.id, ...next, updated_at: now.toISOString() };
    void updateHistory((h) => { h.cards[card.id] = { ...state, chapter_id: chapterId }; });
    const reviewId = uuid();
    void enqueue('card', { state, review: { id: reviewId, flashcard_id: card.id, rating, reviewed_at: now.toISOString() } }, reviewId);
    setCount((n) => n + 1);
    setRevealed(false);
    setQueue((q) => (rating === 0 ? [...q.slice(1), q[0]] : q.slice(1))); // « à revoir » : la carte revient en fin de séance
  }

  return (
    <div className="stack">
      <div className="row"><span className="muted small">{queue.length} {t('fc.left')}</span></div>
      <Bar value={1 - queue.length / Math.max(total, queue.length)} />
      <Card className={`flash${revealed ? ' is-back' : ''}`}>
        <p className="flash-front">{tr(card.front)}</p>
        {revealed && <p className="flash-back">{tr(card.back)}</p>}
      </Card>
      {!revealed ? <Button block onClick={() => setRevealed(true)}>{t('fc.show')}</Button> : (
        <div className="rate">
          <Button variant="danger" onClick={() => rate(0)}>{t('fc.again')}</Button>
          <Button variant="soft" onClick={() => rate(1)}>{t('fc.hard')}</Button>
          <Button variant="soft" onClick={() => rate(2)}>{t('fc.good')}</Button>
          <Button onClick={() => rate(3)}>{t('fc.easy')}</Button>
        </div>
      )}
    </div>
  );
}

export function FlashcardsScreen({ id }: { id: string }) {
  const { t, back, history } = useApp();
  useStudyTimer('flashcards', id);
  return (
    <ChapterFrame id={id} title={t('ch.flashcards')}>
      {(b) => {
        const all = b.flashcards.map((card) => ({ card, chapterId: id }));
        const queue = buildQueue(all, history);
        // Tout est à jour : on propose quand même une séance libre sur l'ensemble des cartes.
        return <Session key={b.fetched_at} initial={queue.length ? queue : all.slice(0, SESSION_NEW)} onExit={back} />;
      }}
    </ChapterFrame>
  );
}

export function DailyReview() {
  const { t, tr, go, history, chapters, canOpen } = useApp();
  useStudyTimer('flashcards', null);
  const [items, setItems] = useState<Item[] | null>(null);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    if (!history || started) return;
    let alive = true;
    const dueByChapter = new Map<string, string[]>();
    for (const c of Object.values(history.cards)) if (isDue(c) && c.chapter_id) dueByChapter.set(c.chapter_id, [...(dueByChapter.get(c.chapter_id) ?? []), c.flashcard_id]);
    void (async () => {
      const out: Item[] = [];
      for (const [chapterId, ids] of dueByChapter) {
        const chapter = chapters.find((c) => c.id === chapterId);
        if (!chapter || !canOpen(chapter)) continue;
        try {
          const { data } = await loadChapter(chapter);
          for (const card of data.flashcards) if (ids.includes(card.id)) out.push({ card, chapterId });
        } catch { /* chapitre indisponible hors ligne : ses cartes seront proposées plus tard */ }
      }
      if (alive) setItems(out);
    })();
    return () => { alive = false; };
  }, [history, chapters, canOpen, started]);

  if (!items) return <div className="page"><Header title={t('home.today')} /><Loader text={t('loading')} /></div>;
  const started_chapters = chapters.filter((c) => canOpen(c));
  return (
    <div className="page">
      <Header title={t('home.today')} />
      {items.length > 0 ? (
        started ? <Session initial={items} onExit={() => { setStarted(false); setItems(null); }} /> : (
          <Card className="result">
            <p className="score">{items.length}</p>
            <p className="muted">{t('home.due')}</p>
            <Button icon="play" onClick={() => setStarted(true)}>{t('start')}</Button>
          </Card>
        )
      ) : (
        <>
          <Notice kind="ok">{t('home.none_due')}</Notice>
          <h2>{t('ch.flashcards')}</h2>
          <div className="stack">
            {started_chapters.map((c) => <Card key={c.id} onClick={() => go(`c/${c.id}/cards`)} className="row"><strong className="grow">{tr(c.title)}</strong></Card>)}
          </div>
        </>
      )}
    </div>
  );
}
