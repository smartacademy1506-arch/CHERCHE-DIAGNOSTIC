import { DIRECTIONS, validatePuzzle } from './validator';

export interface Placement {
  term_index: number; // position du terme dans la liste d'origine
  word: string;       // forme grille
  row: number;
  col: number;
  d_row: number;
  d_col: number;
}

export interface Puzzle {
  size: number;
  seed: number;
  directions: 2 | 4 | 8;
  grid: string[];
  words: Placement[];
}

/** Générateur pseudo-aléatoire déterministe (mulberry32) : même graine => même grille. */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function tryBuild(words: string[], size: number, dirs: ReadonlyArray<readonly [number, number]>, rand: () => number): Puzzle['words'] | null {
  const cells: string[][] = Array.from({ length: size }, () => Array<string>(size).fill(''));
  const order = words.map((word, term_index) => ({ word, term_index })).sort((a, b) => b.word.length - a.word.length);
  const placements: Placement[] = [];

  for (const { word, term_index } of order) {
    let best: { row: number; col: number; dr: number; dc: number; score: number } | null = null;
    for (let attempt = 0; attempt < 220; attempt++) {
      const [dr, dc] = dirs[Math.floor(rand() * dirs.length)];
      const row = Math.floor(rand() * size);
      const col = Math.floor(rand() * size);
      const endR = row + dr * (word.length - 1);
      const endC = col + dc * (word.length - 1);
      if (endR < 0 || endC < 0 || endR >= size || endC >= size) continue;
      let overlap = 0;
      let ok = true;
      for (let i = 0; i < word.length; i++) {
        const ch = cells[row + i * dr][col + i * dc];
        if (ch === '') continue;
        if (ch !== word[i]) { ok = false; break; }
        overlap++;
      }
      if (!ok || overlap === word.length) continue;
      const score = overlap + rand() * 0.5; // les croisements rendent la grille plus dense
      if (!best || score > best.score) best = { row, col, dr, dc, score };
      if (overlap >= 2) break;
    }
    if (!best) return null;
    for (let i = 0; i < word.length; i++) cells[best.row + i * best.dr][best.col + i * best.dc] = word[i];
    placements.push({ term_index, word, row: best.row, col: best.col, d_row: best.dr, d_col: best.dc });
  }

  // Remplissage : lettres tirées parmi celles des mots, pour que les cases vides ne se repèrent pas.
  const pool = words.join('');
  for (let r = 0; r < size; r++) for (let c = 0; c < size; c++) {
    if (cells[r][c] === '') cells[r][c] = pool[Math.floor(rand() * pool.length)];
  }
  (placements as Placement[] & { grid?: string[] }).grid = cells.map((line) => line.join(''));
  return placements;
}

export interface GenerateOptions {
  seed?: number;
  directions?: 2 | 4 | 8;
  minSize?: number;
  maxSize?: number;
}

/**
 * Génère une grille contenant tous les mots, puis la vérifie.
 * Ne renvoie jamais une grille non validée : lève une erreur si aucune grille valide n'est trouvée.
 */
export function generatePuzzle(words: string[], opts: GenerateOptions = {}): Puzzle {
  if (words.length === 0) throw new Error('Aucun mot à placer');
  for (const w of words) if (!/^[A-Z]{3,}$/.test(w)) throw new Error(`Mot invalide : ${w}`);
  if (new Set(words).size !== words.length) throw new Error('Mots en double');
  words.forEach((a, i) => words.forEach((b, j) => {
    if (i !== j && b.includes(a)) throw new Error(`« ${a} » est contenu dans « ${b} »`);
  }));

  const directions = opts.directions ?? 8;
  const dirs = DIRECTIONS.slice(0, directions);
  const longest = Math.max(...words.map((w) => w.length));
  const letters = words.reduce((n, w) => n + w.length, 0);
  const start = Math.max(opts.minSize ?? 10, longest, Math.ceil(Math.sqrt(letters * 1.15)));
  const maxSize = opts.maxSize ?? 30;
  const baseSeed = opts.seed ?? Math.floor(Math.random() * 2 ** 31);

  for (let size = start; size <= maxSize; size++) {
    for (let attempt = 0; attempt < 40; attempt++) {
      const seed = (baseSeed + size * 1000 + attempt) >>> 0;
      const placed = tryBuild(words, size, dirs, rng(seed)) as (Placement[] & { grid?: string[] }) | null;
      if (!placed || !placed.grid) continue;
      const puzzle: Puzzle = {
        size, seed, directions, grid: placed.grid,
        words: [...placed].sort((a, b) => a.term_index - b.term_index),
      };
      if (validatePuzzle(puzzle, words).length === 0) return puzzle;
    }
  }
  throw new Error('Impossible de générer une grille valide avec ces mots');
}
