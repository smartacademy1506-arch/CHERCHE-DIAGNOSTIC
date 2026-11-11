// Mots mêlés : sélection tactile (glisser ou toucher début/fin), détection, définitions, pause, reprise, résultats.
import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent } from 'react';
import { useApp } from '../app';
import type { ChapterBundle, PuzzleData, Term } from '../lib/data';
import { enqueue, updateHistory, uuid } from '../lib/store';
import { Bar, Button, Card, Icon, Notice, formatTime } from '../ui';
import { ChapterFrame } from './Chapter';
import { useStudyTimer } from './Home';

interface Cell { r: number; c: number }
const key = (r: number, c: number) => `${r},${c}`;

/** Cases entre deux cellules si elles sont alignées (ligne, colonne ou diagonale) ; sinon aligne sur la direction la plus proche. */
export function lineCells(a: Cell, b: Cell, size: number): Cell[] {
  const dr = b.r - a.r, dc = b.c - a.c;
  if (dr === 0 && dc === 0) return [a];
  const angle = Math.atan2(dr, dc);
  const step = Math.round(angle / (Math.PI / 4));
  const ur = Math.round(Math.sin(step * Math.PI / 4)), uc = Math.round(Math.cos(step * Math.PI / 4));
  const len = Math.max(Math.abs(dr), Math.abs(dc));
  const out: Cell[] = [];
  for (let i = 0; i <= len; i++) {
    const r = a.r + i * ur, c = a.c + i * uc;
    if (r < 0 || c < 0 || r >= size || c >= size) break;
    out.push({ r, c });
  }
  return out;
}

/** Mot de la grille correspondant exactement à la sélection (dans un sens ou dans l'autre). */
export function matchSelection(puzzle: PuzzleData, cells: Cell[]): PuzzleData['words'][number] | null {
  if (cells.length < 2) return null;
  const first = cells[0], last = cells[cells.length - 1];
  for (const w of puzzle.words) {
    if (w.word.length !== cells.length) continue;
    const endR = w.row + (w.word.length - 1) * w.d_row, endC = w.col + (w.word.length - 1) * w.d_col;
    const forward = w.row === first.r && w.col === first.c && endR === last.r && endC === last.c;
    const backward = w.row === last.r && w.col === last.c && endR === first.r && endC === first.c;
    if (forward || backward) return w;
  }
  return null;
}

export function WordSearchScreen({ id }: { id: string }) {
  const { t, cl } = useApp();
  useStudyTimer('word_search', id);
  return (
    <ChapterFrame id={id} title={t('ch.wordsearch')}>
      {(b) => {
        const puzzle = b.puzzles.find((p) => p.language_code === cl);
        return puzzle ? <Game key={puzzle.id} puzzle={puzzle} bundle={b} chapterId={id} /> : <Notice>{t('ws.none')}</Notice>;
      }}
    </ChapterFrame>
  );
}

function Game({ puzzle, bundle, chapterId }: { puzzle: PuzzleData; bundle: ChapterBundle; chapterId: string }) {
  const { t, tr, go, history } = useApp();
  const saved = history?.puzzles[puzzle.id];
  const resume = saved && !saved.completed ? saved : undefined;
  const sessionId = useRef(resume?.id ?? uuid());
  const [found, setFound] = useState<string[]>(resume?.found ?? []);
  const [elapsed, setElapsed] = useState(resume?.elapsed_s ?? 0);
  const [paused, setPaused] = useState(false);
  const [done, setDone] = useState(false);
  const [showTimer, setShowTimer] = useState(true);
  const [zoom, setZoom] = useState(false);
  const [sel, setSel] = useState<Cell[]>([]);
  const [tapStart, setTapStart] = useState<Cell | null>(null);
  const [focus, setFocus] = useState<Term | null>(null);
  const dragStart = useRef<Cell | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);
  const elapsedRef = useRef(elapsed);
  elapsedRef.current = elapsed;

  const terms = useMemo(() => new Map(bundle.terms.map((x) => [x.id, x])), [bundle]);
  const total = puzzle.words.length;
  const foundCells = useMemo(() => {
    const s = new Set<string>();
    for (const w of puzzle.words) if (found.includes(w.term_id)) for (let i = 0; i < w.word.length; i++) s.add(key(w.row + i * w.d_row, w.col + i * w.d_col));
    return s;
  }, [found, puzzle]);
  // La définition s'efface d'elle-même pour ne pas masquer la grille.
  useEffect(() => {
    if (!focus) return;
    const timer = window.setTimeout(() => setFocus(null), 7000);
    return () => window.clearTimeout(timer);
  }, [focus]);
  const selCells = useMemo(() => new Set(sel.map((c) => key(c.r, c.c))), [sel]);

  const persist = useCallback((list: string[], completed: boolean) => {
    const now = new Date().toISOString();
    const rec = { id: sessionId.current, puzzle_id: puzzle.id, chapter_id: chapterId, found: list, total, elapsed_s: elapsedRef.current, completed, updated_at: now };
    void updateHistory((h) => { h.puzzles[puzzle.id] = rec; });
    void enqueue('puzzle', { id: rec.id, puzzle_id: puzzle.id, found_term_ids: list, words_total: total, elapsed_s: rec.elapsed_s, completed, updated_at: now }, rec.id);
  }, [puzzle.id, chapterId, total]);

  useEffect(() => {
    if (paused || done) return;
    const timer = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => window.clearInterval(timer);
  }, [paused, done]);
  // Sauvegarde périodique et en quittant l'écran : une partie interrompue se reprend là où elle s'est arrêtée.
  const foundRef = useRef(found); foundRef.current = found;
  const doneRef = useRef(done); doneRef.current = done;
  useEffect(() => {
    const save = () => { if (!doneRef.current && (foundRef.current.length > 0 || elapsedRef.current > 10)) persist(foundRef.current, false); };
    const timer = window.setInterval(save, 20000);
    const onHide = () => { if (document.visibilityState === 'hidden') { save(); setPaused(true); } };
    document.addEventListener('visibilitychange', onHide);
    return () => { window.clearInterval(timer); document.removeEventListener('visibilitychange', onHide); save(); };
  }, [persist]);

  function tryCells(cells: Cell[]) {
    const w = matchSelection(puzzle, cells);
    if (!w || found.includes(w.term_id)) return false;
    const next = [...found, w.term_id];
    setFound(next);
    setFocus(terms.get(w.term_id) ?? null);
    const complete = next.length === total;
    persist(next, complete);
    if (complete) setDone(true);
    return true;
  }

  function cellAt(e: PointerEvent | { clientX: number; clientY: number }): Cell | null {
    const el = gridRef.current; if (!el) return null;
    const box = el.getBoundingClientRect();
    const c = Math.floor(((e.clientX - box.left) / box.width) * puzzle.size);
    const r = Math.floor(((e.clientY - box.top) / box.height) * puzzle.size);
    return r >= 0 && c >= 0 && r < puzzle.size && c < puzzle.size ? { r, c } : null;
  }
  function tap(cell: Cell) {
    if (!tapStart) { setTapStart(cell); setSel([cell]); return; }
    const cells = lineCells(tapStart, cell, puzzle.size);
    const last = cells[cells.length - 1];
    if (last.r === cell.r && last.c === cell.c) tryCells(cells);
    setTapStart(null); setSel([]);
  }
  const onDown = (e: PointerEvent<HTMLDivElement>) => {
    if (zoom || paused) return;
    const cell = cellAt(e); if (!cell) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    dragStart.current = cell; setSel(tapStart ? lineCells(tapStart, cell, puzzle.size) : [cell]);
  };
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!dragStart.current) return;
    const cell = cellAt(e); if (cell) setSel(lineCells(tapStart ?? dragStart.current, cell, puzzle.size));
  };
  const onUp = (e: PointerEvent<HTMLDivElement>) => {
    const start = dragStart.current; dragStart.current = null;
    if (!start) return;
    const cell = cellAt(e) ?? start;
    if (cell.r === start.r && cell.c === start.c) { tap(cell); return; }
    tryCells(lineCells(start, cell, puzzle.size));
    setTapStart(null); setSel([]);
  };

  function restart() {
    sessionId.current = uuid();
    setFound([]); setElapsed(0); setDone(false); setPaused(false); setSel([]); setTapStart(null); setFocus(null);
  }

  if (done) {
    const missed = puzzle.words.filter((w) => !found.includes(w.term_id));
    const got = puzzle.words.filter((w) => found.includes(w.term_id));
    const List = ({ items }: { items: typeof puzzle.words }) => (
      <dl className="glossary">{items.map((w) => { const x = terms.get(w.term_id); return x ? <div key={w.term_id}><dt>{tr(x.label)}</dt><dd>{tr(x.definition)}</dd></div> : null; })}</dl>
    );
    return (
      <div className="stack">
        <Card className="result">
          <h2>{t('ws.done')}</h2>
          <p className="score">{found.length} / {total}</p>
          <p className="muted">{t('ws.rate')} : {Math.round((found.length / total) * 100)} % · {formatTime(elapsed)}</p>
          <div className="row wrap center">
            <Button icon="repeat" onClick={restart}>{t('ws.restart')}</Button>
            <Button variant="soft" icon="cards" onClick={() => go(`c/${chapterId}/cards`)}>{t('ch.flashcards')}</Button>
          </div>
        </Card>
        {missed.length > 0 && <section><h2>{t('ws.missed')} ({missed.length})</h2><List items={missed} /></section>}
        {got.length > 0 && <section><h2>{t('ws.all')} ({got.length})</h2><List items={got} /></section>}
      </div>
    );
  }

  return (
    <div className="ws">
      <div className="ws-bar">
        <strong>{found.length} / {total} {t('ws.found')}</strong>
        {showTimer && <span className="ws-time"><Icon name="clock" size={16} /> {formatTime(elapsed)}</span>}
        <span className="grow" />
        <button type="button" className="icon-btn" onClick={() => setShowTimer((v) => !v)} aria-label={t('ws.timer')} aria-pressed={showTimer}><Icon name="clock" /></button>
        <button type="button" className="icon-btn" onClick={() => { setZoom((z) => !z); setSel([]); setTapStart(null); }} aria-label={t('ws.zoom')} aria-pressed={zoom}><Icon name="zoom" /></button>
        <button type="button" className="icon-btn" onClick={() => { setPaused((p) => !p); if (!paused) persist(found, false); }} aria-label={t(paused ? 'ws.resume' : 'ws.pause')}><Icon name={paused ? 'play' : 'pause'} /></button>
      </div>
      <Bar value={found.length / total} />
      <p className="small muted">{t('ws.hint')}</p>

      <div className={`ws-scroll${zoom ? ' ws-zoom' : ''}`}>
        {paused ? (
          <div className="ws-paused"><p>{t('ws.paused')}</p><Button icon="play" onClick={() => setPaused(false)}>{t('ws.resume')}</Button></div>
        ) : (
          <div ref={gridRef} className="ws-grid" data-testid="ws-grid" style={{ gridTemplateColumns: `repeat(${puzzle.size}, 1fr)`, ['--n' as string]: puzzle.size }}
            onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={() => { dragStart.current = null; setSel([]); }}
            onClick={zoom ? (e) => { const c = cellAt(e); if (c) tap(c); } : undefined}>
            {puzzle.grid.map((line, r) => [...line].map((ch, c) => {
              const k = key(r, c);
              return <span key={k} className={`ws-cell${foundCells.has(k) ? ' is-found' : ''}${selCells.has(k) ? ' is-sel' : ''}`}>{ch}</span>;
            }))}
          </div>
        )}
      </div>

      {focus && (
        <Card className="ws-def">
          <button type="button" className="icon-btn" onClick={() => setFocus(null)} aria-label={t('close')}><Icon name="x" size={18} /></button>
          <strong>{tr(focus.label)}</strong>
          <p>{tr(focus.definition)}</p>
        </Card>
      )}

      <ul className="ws-words" aria-label={t('ch.glossary')}>
        {puzzle.words.map((w) => {
          const x = terms.get(w.term_id); const ok = found.includes(w.term_id);
          return (
            <li key={w.term_id}>
              <button type="button" className={`chip${ok ? ' chip-found' : ''}`} disabled={!ok} onClick={() => x && setFocus(x)}>{x ? tr(x.label) : w.word}</button>
            </li>
          );
        })}
      </ul>
      <Button variant="ghost" onClick={() => { persist(found, true); setDone(true); }}>{t('ws.end')}</Button>
    </div>
  );
}
