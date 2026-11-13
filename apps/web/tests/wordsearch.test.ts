import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { gridForm } from '../src/lib/wordsearch/normalize';
import { generatePuzzle } from '../src/lib/wordsearch/generator';
import { countOccurrences, readWord, validatePuzzle } from '../src/lib/wordsearch/validator';

const WORDS = ['SODIUM', 'POTASSIUM', 'OSMOSE', 'DIFFUSION', 'MEMBRANE', 'SYNAPSE', 'AXONE', 'MYELINE', 'CALCIUM', 'DEPOLARISATION'];

test('gridForm retire accents, espaces et ligatures', () => {
  assert.equal(gridForm('Débit cardiaque'), 'DEBITCARDIAQUE');
  assert.equal(gridForm('NŒUD DE RANVIER'), 'NOEUDDERANVIER');
  assert.equal(gridForm("Trou anionique-d'un"), 'TROUANIONIQUEDUN');
});

test('chaque mot est lisible aux coordonnées annoncées et à un seul endroit', () => {
  const p = generatePuzzle(WORDS, { seed: 42 });
  assert.equal(p.words.length, WORDS.length);
  for (const w of p.words) {
    assert.equal(readWord(p.grid, w.row, w.col, w.d_row, w.d_col, w.word.length), w.word);
    assert.equal(countOccurrences(p.grid, w.word), 1);
  }
  assert.deepEqual(validatePuzzle(p, WORDS), []);
});

test('même graine, même grille', () => {
  assert.deepEqual(generatePuzzle(WORDS, { seed: 7 }), generatePuzzle(WORDS, { seed: 7 }));
});

test('le validateur détecte une lettre altérée, un mot manquant et des coordonnées fausses', () => {
  const p = generatePuzzle(WORDS, { seed: 3 });
  const w = p.words[0];
  const broken = p.grid.map((line, r) => (r === w.row ? line.slice(0, w.col) + (line[w.col] === 'Z' ? 'Q' : 'Z') + line.slice(w.col + 1) : line));
  assert.ok(validatePuzzle({ ...p, grid: broken }, WORDS).length > 0);
  assert.ok(validatePuzzle({ ...p, words: p.words.slice(1) }, WORDS).some((e) => e.includes('absent')));
  const moved = p.words.map((x, i) => (i === 0 ? { ...x, row: (x.row + 1) % p.size } : x));
  assert.ok(validatePuzzle({ ...p, words: moved }, WORDS).length > 0);
});

test('le générateur refuse doublons et mots inclus', () => {
  assert.throws(() => generatePuzzle(['SODIUM', 'SODIUM']));
  assert.throws(() => generatePuzzle(['SYSTOLE', 'EXTRASYSTOLE']));
});

test('directions limitées respectées', () => {
  const p = generatePuzzle(WORDS, { seed: 5, directions: 2 });
  for (const w of p.words) assert.ok((w.d_row === 0 && w.d_col === 1) || (w.d_row === 1 && w.d_col === 0));
});

test('les chapitres réels produisent des grilles valides dans les deux langues', () => {
  const dir = join(import.meta.dirname, '../../../content/physiologie');
  for (const f of readdirSync(dir).filter((x) => x.endsWith('.json'))) {
    const ch = JSON.parse(readFileSync(join(dir, f), 'utf8'));
    for (const lang of ['fr', 'en'] as const) {
      const words = ch.terms.map((t: Record<string, string>) => gridForm(t[lang]));
      const p = generatePuzzle(words, { seed: 2026 });
      assert.deepEqual(validatePuzzle(p, words), [], `${f} ${lang}`);
      assert.ok(p.size <= 24, `${f} ${lang} : taille ${p.size}`);
    }
  }
});
