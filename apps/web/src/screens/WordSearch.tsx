// Mots mêlés : sélection tactile (glisser ou toucher début/fin), détection, définitions, pause, reprise, résultats.
// Design system : chaque mot trouvé est surligné d'une pastille (ciel, rouge, ambre, marine en alternance) sous les lettres,
// qui restent à l'encre du texte ; la sélection en cours prend la couleur primaire.
import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent } from 'react';
import { useApp } from '../app';
import type { ChapterBundle, PuzzleData, Term } from '../lib/data';
import { enqueue, updateHistory, uuid } from '../lib/store';
import { Bar, Button, Card, Icon, Notice, formatTime } from '../ui';
import { ChapterFrame } from './Chapter';
import { useStudyTimer } from './Home';

interface Cell { r: number; c: number }
type Path = [Cell, Cell];
type Placement = PuzzleData['words'][number];
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

const endOf = (w: Placement): Cell => ({ r: w.row + (w.word.length - 1) * w.d_row, c: w.col + (w.word.length - 1) * w.d_col });
const canonicalPath = (w: Placement): Path => [{ r: w.row, c: w.col }, endOf(w)];

/**
 * Mot correspondant à la sélection, dans un sens ou dans l'autre. On accepte l'emplacement enregistré
 * et, dans les grilles des livres où un mot court peut se lire à deux endroits, toute suite de lettres identique.
 */
export function matchSelection(puzzle: PuzzleData, cells: Cell[], found: string[] = []): Placement | null {
  if (cells.length < 2) return null;
  const first = cells[0], last = cells[cells.length - 1];
  for (const w of puzzle.words) {
    if (w.word.length !== cells.length) continue;
    const end = endOf(w);
    const forward = w.row === first.r && w.col === first.c && end.r === last.r && end.c === last.c;
    const backward = w.row === last.r && w.col === last.c && end.r === first.r && end.c === first.c;
    if (forward || backward) return w;
  }
  const letters = cells.map(({ r, c }) => puzzle.grid[r][c]).join('');
  const reversed = [...letters].reverse().join('');
  return puzzle.words.find((w) => !found.includes(w.term_id) && (w.word === letters || w.word === reversed)) ?? null;
}

/** Couleurs de surlignage du design system, dans l'ordre où les mots sont trouvés. */
export const HIGHLIGHTS = ['ciel', 'rouge', 'ambre', 'marine'] as const;

/** Pastille d'un mot : capsule de 0,8 case de haut alignée sur le mot, en unités de case. */
function loopGeometry([a, b]: Path) {
  const x1 = a.c + .5, y1 = a.r + .5, x2 = b.c + .5, y2 = b.r + .5;
  const h = .8;
  const w = Math.hypot(x2 - x1, y2 - y1) + h;
  const angle = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;
  return { cx: (x1 + x2) / 2, cy: (y1 + y2) / 2, w, h, angle };
}

function Ink({ size, loops, selection, lastId }: { size: number; loops: { id: string; path: Path; seed: number }[]; selection: Cell[]; lastId: string | null }) {
  const sel = selection.length ? loopGeometry([selection[0], selection[selection.length - 1]]) : null;
  return (
    <svg className="ws-ink" viewBox={`0 0 ${size} ${size}`} preserveAspectRatio="none" aria-hidden="true">
      {loops.map(({ id, path }, i) => {
        const g = loopGeometry(path);
        return (
          <rect key={id} className={`ws-hl ws-hl-${HIGHLIGHTS[i % HIGHLIGHTS.length]}${id === lastId ? ' is-new' : ''}`} x={-g.w / 2} y={-g.h / 2} width={g.w} height={g.h} rx={g.h / 2}
            transform={`translate(${g.cx} ${g.cy}) rotate(${g.angle})`} />
        );
      })}
      {sel && <rect className="ws-select" x={-sel.w / 2} y={-sel.h / 2} width={sel.w} height={sel.h} rx={sel.h / 2} transform={`translate(${sel.cx} ${sel.cy}) rotate(${sel.angle})`} />}
    </svg>
  );
}

export function WordSearchScreen({ id }: { id: string }) {
  const { t, tr, cl, chapters } = useApp();
  useStudyTimer('word_search', id);
  const ch = chapters.find((c) => c.id === id);
  useEffect(() => {
    const prev = document.title;
    document.title = `${t('ch.wordsearch')} — CHERCHE & DIAGNOSTIC`;
    return () => { document.title = prev; };
  }, [t]);
  return (
    <ChapterFrame id={id} wide title={ch ? `${String(ch.sort).padStart(2, '0')} · ${tr(ch.title)}` : t('ch.wordsearch')}>
      {(b) => {
        // Grille dans la langue du contenu, sinon la grille d'origine en français (traduction en cours de validation).
        const puzzle = b.puzzles.find((p) => p.language_code === cl) ?? b.puzzles.find((p) => p.language_code === 'fr');
        return puzzle ? <Game key={puzzle.id} puzzle={puzzle} bundle={b} chapterId={id} /> : <Notice>{t('ws.none')}</Notice>;
      }}
    </ChapterFrame>
  );
}

function Game({ puzzle, bundle, chapterId }: { puzzle: PuzzleData; bundle: ChapterBundle; chapterId: string }) {
  const { t, tr, go, history, lang } = useApp();
  const saved = history?.puzzles[puzzle.id];
  const resume = saved && !saved.completed ? saved : undefined;
  const sessionId = useRef(resume?.id ?? uuid());
  const [found, setFound] = useState<string[]>(resume?.found ?? []);
  const [paths, setPaths] = useState<Record<string, Path>>(resume?.paths ?? {});
  const pathsRef = useRef(paths); pathsRef.current = paths;
  const [defOpen, setDefOpen] = useState(false);
  const [lastId, setLastId] = useState<string | null>(null);
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
  const byTerm = useMemo(() => new Map(puzzle.words.map((w) => [w.term_id, w])), [puzzle]);
  const total = puzzle.words.length;
  const loops = useMemo(() => found.map((id, i) => {
    const w = byTerm.get(id);
    return w ? { id, path: paths[id] ?? canonicalPath(w), seed: i + 1 } : null;
  }).filter((x): x is { id: string; path: Path; seed: number } => !!x), [found, paths, byTerm]);
  const foundCells = useMemo(() => {
    const s = new Set<string>();
    for (const l of loops) for (const c of lineCells(l.path[0], l.path[1], puzzle.size)) s.add(key(c.r, c.c));
    return s;
  }, [loops, puzzle.size]);
  const selCells = useMemo(() => new Set(sel.map((c) => key(c.r, c.c))), [sel]);

  const persist = useCallback((list: string[], completed: boolean, circled: Record<string, Path> = pathsRef.current) => {
    const now = new Date().toISOString();
    const rec = { id: sessionId.current, puzzle_id: puzzle.id, chapter_id: chapterId, found: list, total, elapsed_s: elapsedRef.current, completed, updated_at: now, paths: circled };
    void updateHistory((h) => { h.puzzles[puzzle.id] = rec; });
    void enqueue('puzzle', { id: rec.id, puzzle_id: puzzle.id, found_term_ids: list, words_total: total, elapsed_s: rec.elapsed_s, completed, updated_at: now }, rec.id);
  }, [puzzle.id, chapterId, total]);

  useEffect(() => {
    if (paused || done) return;
    const timer = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => window.clearInterval(timer);
  }, [paused, done]);
  // La définition s'efface d'elle-même pour ne pas masquer la grille.
  useEffect(() => { setDefOpen(false); }, [focus]);
  useEffect(() => {
    if (!focus || defOpen) return;
    const ms = Math.min(20000, Math.max(7000, tr(focus.definition).length * 70));
    const timer = window.setTimeout(() => setFocus(null), ms);
    return () => window.clearTimeout(timer);
  }, [focus, defOpen, tr]);
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
    const w = matchSelection(puzzle, cells, found);
    if (!w || found.includes(w.term_id)) return false;
    const next = [...found, w.term_id];
    const circled: Record<string, Path> = { ...pathsRef.current, [w.term_id]: [cells[0], cells[cells.length - 1]] };
    setFound(next);
    setPaths(circled);
    setLastId(w.term_id);
    setFocus(terms.get(w.term_id) ?? null);
    const complete = next.length === total;
    persist(next, complete, circled);
    if (complete) { setDone(true); setFocus(null); }
    return true;
  }

  function tryLine(start: Cell, end: Cell) {
    const cells = lineCells(start, end, puzzle.size);
    if (tryCells(cells) || cells.length < 2) return;
    const dr = cells[1].r - cells[0].r, dc = cells[1].c - cells[0].c, last = cells[cells.length - 1];
    const longer = { r: last.r + dr, c: last.c + dc };
    if (cells.length > 2 && tryCells(cells.slice(0, -1))) return;
    if (longer.r >= 0 && longer.c >= 0 && longer.r < puzzle.size && longer.c < puzzle.size) tryCells([...cells, longer]);
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
    if (last.r === cell.r && last.c === cell.c) tryLine(tapStart, cell);
    setTapStart(null); setSel([]);
  }
  const onDown = (e: PointerEvent<HTMLDivElement>) => {
    if (zoom || paused || done) return;
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
    tryLine(start, cell);
    setTapStart(null); setSel([]);
  };

  function restart() {
    sessionId.current = uuid();
    setFound([]); setPaths({}); setLastId(null); setElapsed(0); setDone(false); setPaused(false); setSel([]); setTapStart(null); setFocus(null);
  }

  const missed = puzzle.words.filter((w) => !found.includes(w.term_id));
  const DefList = ({ items }: { items: Placement[] }) => (
    <dl className="glossary">{items.map((w) => { const x = terms.get(w.term_id); return x ? <div key={w.term_id}><dt>{tr(x.label)}</dt><dd>{tr(x.definition) || <em className="def-missing">{t('def.missing')}</em>}</dd></div> : null; })}</dl>
  );

  return (
    <div className="ws">
      <div className="ws-bar">
        <span className="ws-count" aria-live="polite">{found.length}<small>/ {total} {t('ws.found')}</small></span>
        {showTimer && <span className="ws-time"><Icon name="clock" size={16} /> {formatTime(elapsed)}</span>}
        <span className="grow" />
        {!done && <>
          <button type="button" className="icon-btn" onClick={() => setShowTimer((v) => !v)} aria-label={t('ws.timer')} aria-pressed={showTimer}><Icon name="clock" /></button>
          <button type="button" className="icon-btn" onClick={() => { setZoom((z) => !z); setSel([]); setTapStart(null); }} aria-label={t('ws.zoom')} aria-pressed={zoom}><Icon name="zoom" /></button>
          <button type="button" className="icon-btn" onClick={() => { setPaused((p) => !p); if (!paused) persist(found, false); }} aria-label={t(paused ? 'ws.resume' : 'ws.pause')}><Icon name={paused ? 'play' : 'pause'} /></button>
        </>}
      </div>
      <Bar value={found.length / total} />
      {/* Zone réservée au-dessus de la grille : consigne, puis définition du dernier mot trouvé. Hauteur fixe : la grille ne bouge pas. */}
      {!done && (
        <div className="ws-note" aria-live="polite">
          {sel.length > 1 ? (
            <p className="ws-live" aria-hidden="true">{sel.map((c) => puzzle.grid[c.r][c.c]).join('')}</p>
          ) : focus ? (
            <div className={`ws-def${defOpen ? ' is-open' : ''}`}>
              <button type="button" className="ws-def-text" aria-expanded={defOpen} onClick={() => setDefOpen((o) => !o)}>
                <strong>{tr(focus.label)}</strong> — {tr(focus.definition) || <em className="def-missing">{t('def.missing')}</em>}
              </button>
              <button type="button" className="icon-btn" onClick={() => setFocus(null)} aria-label={t('close')}><Icon name="x" size={18} /></button>
            </div>
          ) : <p className="ws-hint">{t('ws.hint')}</p>}
        </div>
      )}

      <div className={`ws-scroll${zoom && !done ? ' ws-zoom' : ''}`}>
        {paused ? (
          <div className="ws-sheet"><div className="ws-paused"><p>{t('ws.paused')}</p><Button icon="play" onClick={() => setPaused(false)}>{t('ws.resume')}</Button></div></div>
        ) : (
          <div className="ws-sheet">
            <div ref={gridRef} className="ws-grid" data-testid="ws-grid" lang={lang} style={{ gridTemplateColumns: `repeat(${puzzle.size}, 1fr)`, ['--n' as string]: puzzle.size }}
              onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={() => { dragStart.current = null; setSel([]); }}
              onClick={zoom && !done ? (e) => { const c = cellAt(e); if (c) tap(c); } : undefined}>
              {puzzle.grid.map((line, r) => [...line].map((ch, c) => {
                const k = key(r, c);
                return <span key={k} className={`ws-cell${foundCells.has(k) ? ' is-found' : ''}${selCells.has(k) ? ' is-sel' : ''}`}>{ch}</span>;
              }))}
              <Ink size={puzzle.size} loops={loops} selection={sel} lastId={lastId} />
            </div>
          </div>
        )}
      </div>

      <div className="ws-side">
      {done ? (
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
          {missed.length > 0 && <section><h2>{t('ws.missed')} ({missed.length})</h2><DefList items={missed} /></section>}
          {found.length > 0 && <section><h2>{t('ws.all')} ({found.length})</h2><DefList items={puzzle.words.filter((w) => found.includes(w.term_id))} /></section>}
        </div>
      ) : (
        <>
          <ol className="ws-list" aria-label={t('ch.glossary')} lang={puzzle.language_code}>
            {puzzle.words.map((w) => {
              const x = terms.get(w.term_id); const ok = found.includes(w.term_id);
              const n = found.indexOf(w.term_id);
              const dot = <span className={`ws-dot${ok ? ` ws-dot-${HIGHLIGHTS[n % HIGHLIGHTS.length]}` : ''}`} aria-hidden="true">{ok && <Icon name="check" size={12} />}</span>;
              const label = <span className="ws-label">{x ? tr(x.label) : w.word}</span>;
              return (
                <li key={w.term_id} className={ok ? 'is-found' : undefined}>
                  {ok ? <button type="button" className="ws-item" onClick={() => x && setFocus(x)}>{dot}{label}<span className="sr-only"> ({t('ws.found_one')})</span></button> : <span className="ws-item">{dot}{label}</span>}
                </li>
              );
            })}
          </ol>
          <Button variant="diagnostic" icon="check" onClick={() => { persist(found, true); setDone(true); setFocus(null); }}>{t('ws.end')}</Button>
        </>
      )}
      </div>
    </div>
  );
}
