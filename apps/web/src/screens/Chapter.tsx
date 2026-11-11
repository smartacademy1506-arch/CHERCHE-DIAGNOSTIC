// Chapitre : sommaire des activités, lecteur de cours, glossaire et questions ouvertes.
import { useEffect, useMemo, useState } from 'react';
import { useApp } from '../app';
import { downloadChapter, listDownloads, loadChapter, type Chapter, type ChapterBundle } from '../lib/data';
import { enqueue, updateHistory, uuid } from '../lib/store';
import { Button, Card, Header, Icon, Loader, Markdown, Notice, Tag } from '../ui';
import { chapterProgress, useStudyTimer } from './Home';

type Load = { state: 'loading' } | { state: 'error' } | { state: 'locked' } | { state: 'ready'; bundle: ChapterBundle; stale: boolean };

/** Charge le contenu d'un chapitre (copie locale si disponible, sinon réseau). */
export function useChapter(id: string): { chapter: Chapter | undefined; load: Load; reload: () => void } {
  const { chapters, canOpen, catalogState } = useApp();
  const chapter = chapters.find((c) => c.id === id);
  const [load, setLoad] = useState<Load>({ state: 'loading' });
  const [tick, setTick] = useState(0);
  const allowed = chapter ? canOpen(chapter) : false;
  useEffect(() => {
    let alive = true;
    if (!chapter) { if (catalogState !== 'loading') setLoad({ state: 'error' }); return; }
    if (!allowed) { setLoad({ state: 'locked' }); return; }
    setLoad({ state: 'loading' });
    loadChapter(chapter)
      .then(({ data, stale }) => { if (alive) setLoad({ state: 'ready', bundle: data, stale }); })
      .catch(() => { if (alive) setLoad({ state: 'error' }); });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapter?.id, chapter?.content_version, allowed, catalogState, tick]);
  return { chapter, load, reload: () => setTick((n) => n + 1) };
}

/** Enveloppe commune des écrans d'un chapitre : états de chargement, d'erreur et de verrouillage. */
export function ChapterFrame({ id, title, children }: { id: string; title?: string; children: (bundle: ChapterBundle, chapter: Chapter) => React.ReactNode }) {
  const { t, tr, go, back } = useApp();
  const { chapter, load, reload } = useChapter(id);
  return (
    <div className="page">
      <Header title={title ?? tr(chapter?.title)} onBack={back} />
      {load.state === 'loading' && <Loader text={t('loading')} />}
      {load.state === 'error' && <><Notice kind="warn">{t('ch.unavailable')}</Notice><Button onClick={reload}>{t('retry')}</Button></>}
      {load.state === 'locked' && <><Notice kind="info"><Icon name="lock" size={16} /> {t('ch.locked')}</Notice><Button onClick={() => go('plans')}>{t('ch.unlock')}</Button></>}
      {load.state === 'ready' && chapter && children(load.bundle, chapter)}
    </div>
  );
}

export function ChapterHub({ id }: { id: string }) {
  const { t, tr, go, history, cl, online, toast } = useApp();
  const [downloaded, setDownloaded] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { void listDownloads().then((l) => setDownloaded(l.includes(id))); }, [id]);
  const p = chapterProgress(history, id);

  return (
    <ChapterFrame id={id}>
      {(b, chapter) => {
        const hasPuzzle = b.puzzles.some((x) => x.language_code === cl);
        const items = [
          { path: 'lesson', icon: 'book', label: t('ch.lesson'), meta: p.lesson ? t('ch.read') : '', show: !!b.lesson },
          { path: 'ws', icon: 'grid', label: t('ch.wordsearch'), meta: `${Math.round(p.puzzle * 100)} %`, show: hasPuzzle },
          { path: 'glossary', icon: 'list', label: t('ch.glossary'), meta: String(b.terms.length), show: b.terms.length > 0 },
          { path: 'cards', icon: 'cards', label: t('ch.flashcards'), meta: String(b.flashcards.length), show: b.flashcards.length > 0 },
          { path: 'quiz', icon: 'quiz', label: t('ch.quiz'), meta: p.quizBest === null ? String(b.questions.length) : `${Math.round(p.quizBest * 100)} %`, show: b.questions.length > 0 },
          { path: 'open', icon: 'edit', label: t('ch.open'), meta: String(b.open_questions.length), show: b.open_questions.length > 0 },
        ].filter((x) => x.show);
        return (
          <>
            <p className="muted">{tr(chapter.description)}</p>
            <div className="row wrap">
              <Tag kind={chapter.is_free ? 'free' : 'premium'}>{t(chapter.is_free ? 'free' : 'premium')}</Tag>
              {chapter.status !== 'published' && <Tag kind="review">{t('in_review')}</Tag>}
              {downloaded && <Tag><Icon name="check" size={14} /> {t('ch.offline')}</Tag>}
            </div>
            {b.objectives.length > 0 && (
              <section>
                <h2>{t('ch.objectives')}</h2>
                <Card><ul className="bullets">{b.objectives.map((o, i) => <li key={i}>{tr(o)}</li>)}</ul></Card>
              </section>
            )}
            <div className="tiles">
              {items.map((it) => (
                <Card key={it.path} onClick={() => go(`c/${id}/${it.path}`)} className="tile tile-activity">
                  <span className="disc-icon"><Icon name={it.icon} /></span>
                  <strong>{it.label}</strong>
                  <span className="muted small">{it.meta}</span>
                </Card>
              ))}
            </div>
            <Button variant="soft" icon="download" disabled={busy || !online} onClick={async () => {
              setBusy(true);
              try { await downloadChapter(chapter); setDownloaded(true); toast(t('downloaded')); } catch { toast(t('error')); } finally { setBusy(false); }
            }}>{downloaded ? t('downloaded') : t('download')}</Button>
          </>
        );
      }}
    </ChapterFrame>
  );
}

export function Lesson({ id }: { id: string }) {
  const { t, tr, history, go } = useApp();
  useStudyTimer('lesson', id);
  const read = !!history?.lessons[id];
  return (
    <ChapterFrame id={id}>
      {(b) => b.lesson && (
        <article className="lesson">
          {b.lesson.status !== 'published' && <Tag kind="review">{t('in_review')}</Tag>}
          <Markdown text={tr(b.lesson.summary)} />
          {b.lesson.key_points.length > 0 && (
            <section>
              <h2>{t('ch.key_points')}</h2>
              <Card className="keypoints"><ul className="bullets">{b.lesson.key_points.map((k, i) => <li key={i}>{tr(k)}</li>)}</ul></Card>
            </section>
          )}
          {b.lesson.source_refs.length > 0 && (
            <section>
              <h2>{t('ch.references')}</h2>
              <ol className="refs">
                {b.lesson.source_refs.map((r, i) => <li key={i}>{r.citation}{/^https:\/\//.test(r.url) && <> — <a href={r.url} target="_blank" rel="noopener noreferrer">{new URL(r.url).hostname}</a></>}</li>)}
              </ol>
            </section>
          )}
          <div className="row wrap">
            <Button variant={read ? 'soft' : 'primary'} icon="check" disabled={read} onClick={() => {
              const at = new Date().toISOString();
              void updateHistory((h) => { h.lessons[id] = at; });
              void enqueue('lesson', { chapter_id: id, lesson_read_at: at, updated_at: at }, id);
            }}>{read ? t('ch.read') : t('ch.mark_read')}</Button>
            <Button variant="ghost" icon="grid" onClick={() => go(`c/${id}/ws`)}>{t('ch.wordsearch')}</Button>
          </div>
        </article>
      )}
    </ChapterFrame>
  );
}

export function Glossary({ id }: { id: string }) {
  const { t, tr } = useApp();
  const [q, setQ] = useState('');
  useStudyTimer('glossary', id);
  return (
    <ChapterFrame id={id} title={t('ch.glossary')}>
      {(b) => <GlossaryList bundle={b} q={q} setQ={setQ} tr={tr} />}
    </ChapterFrame>
  );
}
function GlossaryList({ bundle, q, setQ, tr }: { bundle: ChapterBundle; q: string; setQ: (s: string) => void; tr: (v: any) => string }) {
  const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const terms = useMemo(() => [...bundle.terms].sort((a, b) => tr(a.label).localeCompare(tr(b.label))), [bundle, tr]);
  const shown = terms.filter((x) => !q || norm(tr(x.label)).includes(norm(q)) || norm(tr(x.definition)).includes(norm(q)));
  return (
    <>
      <input className="search" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="🔍" aria-label="Rechercher" />
      <dl className="glossary">
        {shown.map((x) => (<div key={x.id}><dt>{tr(x.label)}</dt><dd>{tr(x.definition)}</dd></div>))}
      </dl>
    </>
  );
}

export function OpenQuestions({ id }: { id: string }) {
  const { t, tr, history, toast } = useApp();
  useStudyTimer('open_question', id);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [shown, setShown] = useState<Record<string, boolean>>({});

  function save(questionId: string, answer: string, selfScore: number | null) {
    const prev = history?.open[questionId];
    const now = new Date().toISOString();
    const rec = { id: prev?.id ?? uuid(), question_id: questionId, chapter_id: id, answer, self_score: selfScore, updated_at: now };
    void updateHistory((h) => { h.open[questionId] = rec; });
    void enqueue('open', { id: rec.id, question_id: questionId, answer, self_score: selfScore, updated_at: now }, questionId);
    toast(t('saved'));
  }

  return (
    <ChapterFrame id={id} title={t('ch.open')}>
      {(b) => (
        <div className="stack">
          {b.open_questions.map((q, i) => {
            const saved = history?.open[q.id];
            const text = drafts[q.id] ?? saved?.answer ?? '';
            const reveal = shown[q.id];
            return (
              <Card key={q.id} className="open-q">
                <strong>{i + 1}. {tr(q.question)}</strong>
                <label className="field"><span>{t('open.answer')}</span>
                  <textarea rows={5} maxLength={6000} value={text} onChange={(e) => setDrafts((d) => ({ ...d, [q.id]: e.target.value }))} /></label>
                <div className="row wrap">
                  <Button disabled={!text.trim()} onClick={() => save(q.id, text.trim(), saved?.self_score ?? null)}>{t('save')}</Button>
                  <Button variant="ghost" disabled={!text.trim()} onClick={() => { save(q.id, text.trim(), saved?.self_score ?? null); setShown((s) => ({ ...s, [q.id]: true })); }}>{t('open.show')}</Button>
                </div>
                {reveal && (q.model_answer ? (
                  <div className="model">
                    <h3>{t('open.model')}</h3>
                    <p>{tr(q.model_answer)}</p>
                    <p className="small muted">{t('open.self')}</p>
                    <div className="row wrap">
                      {[0, 1, 2, 3].map((s) => (
                        <button key={s} type="button" className={`chip${saved?.self_score === s ? ' chip-on' : ''}`} onClick={() => save(q.id, text.trim(), s)}>{t(`open.s${s}`)}</button>
                      ))}
                    </div>
                  </div>
                ) : <Notice>{t('open.no_model')}</Notice>)}
              </Card>
            );
          })}
        </div>
      )}
    </ChapterFrame>
  );
}
