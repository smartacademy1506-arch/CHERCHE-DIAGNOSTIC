import type { Placement, Puzzle } from './generator';

export const DIRECTIONS: ReadonlyArray<readonly [number, number]> = [
  [0, 1], [1, 0], [1, 1], [-1, 1], [0, -1], [-1, 0], [-1, -1], [1, -1],
];

/** Lit `length` lettres dans la grille à partir de (row, col) ; null si l'on sort de la grille. */
export function readWord(grid: string[], row: number, col: number, dRow: number, dCol: number, length: number): string | null {
  const size = grid.length;
  let out = '';
  for (let i = 0; i < length; i++) {
    const r = row + i * dRow;
    const c = col + i * dCol;
    if (r < 0 || c < 0 || r >= size || c >= size) return null;
    out += grid[r][c];
  }
  return out;
}

/** Nombre d'endroits où `word` peut être lu dans la grille, toutes directions confondues. */
export function countOccurrences(grid: string[], word: string): number {
  const size = grid.length;
  let n = 0;
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      if (grid[r][c] !== word[0]) continue;
      for (const [dr, dc] of DIRECTIONS) {
        if (readWord(grid, r, c, dr, dc, word.length) === word) n++;
      }
    }
  }
  return n;
}

/**
 * Vérifie une grille. Renvoie la liste des erreurs (vide = grille valide) :
 * grille carrée en A-Z, chaque mot attendu présent une seule fois dans la liste, lisible
 * aux coordonnées annoncées, dans une direction valide, et présent à un seul endroit de la grille.
 */
export function validatePuzzle(puzzle: Pick<Puzzle, 'size' | 'grid' | 'words'>, expectedWords: string[]): string[] {
  const errors: string[] = [];
  const { size, grid, words } = puzzle;
  if (grid.length !== size) errors.push(`hauteur ${grid.length} ≠ ${size}`);
  grid.forEach((line, i) => {
    if (line.length !== size || !/^[A-Z]+$/.test(line)) errors.push(`ligne ${i + 1} invalide`);
  });
  if (errors.length) return errors;

  const placed = new Map<string, Placement>();
  for (const w of words) {
    if (placed.has(w.word)) errors.push(`${w.word} : en double dans la liste`);
    placed.set(w.word, w);
  }
  for (const e of expectedWords) if (!placed.has(e)) errors.push(`${e} : absent de la grille`);
  for (const w of words) if (!expectedWords.includes(w.word)) errors.push(`${w.word} : mot inattendu`);

  for (const w of words) {
    const validDir = DIRECTIONS.some(([dr, dc]) => dr === w.d_row && dc === w.d_col);
    if (!validDir) { errors.push(`${w.word} : direction invalide`); continue; }
    const read = readWord(grid, w.row, w.col, w.d_row, w.d_col, w.word.length);
    if (read === null) errors.push(`${w.word} : sort de la grille`);
    else if (read !== w.word) errors.push(`${w.word} : la grille contient « ${read} » aux coordonnées annoncées`);
    else if (countOccurrences(grid, w.word) !== 1) errors.push(`${w.word} : lisible à plusieurs endroits`);
  }
  return errors;
}
