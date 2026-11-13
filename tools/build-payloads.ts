// Prépare les chapitres pour l'import : valide le contenu, génère et vérifie une grille par langue,
// puis écrit supabase/seed/<slug>.json (format attendu par public.admin_import_chapter).
// Usage : tsx tools/build-payloads.ts content/physiologie
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { validateChapter } from './validate-content.mjs';
import { gridForm } from '../apps/web/src/lib/wordsearch/normalize';
import { generatePuzzle } from '../apps/web/src/lib/wordsearch/generator';
import { validatePuzzle } from '../apps/web/src/lib/wordsearch/validator';

const srcDir = process.argv[2];
if (!srcDir) { console.error('Usage : tsx tools/build-payloads.ts <dossier de contenu>'); process.exit(1); }
const outDir = join(import.meta.dirname, '../supabase/seed');
mkdirSync(outDir, { recursive: true });

let failed = false;
for (const file of readdirSync(srcDir).filter((f) => f.endsWith('.json')).sort()) {
  const chapter = JSON.parse(readFileSync(join(srcDir, file), 'utf8'));
  const errors: string[] = validateChapter(chapter);
  if (errors.length) { failed = true; console.error(`ERREUR ${file}\n  - ${errors.join('\n  - ')}`); continue; }

  const puzzles: Record<string, unknown> = {};
  for (const lang of ['fr', 'en']) {
    const words: string[] = chapter.terms.map((t: Record<string, string>) => gridForm(t[lang]));
    const puzzle = generatePuzzle(words, { seed: 2026 + chapter.order });
    const check = validatePuzzle(puzzle, words);
    if (check.length) { failed = true; console.error(`ERREUR grille ${file} ${lang} : ${check.join(' ; ')}`); continue; }
    puzzles[lang] = puzzle;
    console.log(`OK ${file} ${lang} : grille ${puzzle.size}×${puzzle.size}, ${puzzle.words.length} mots`);
  }
  writeFileSync(join(outDir, `${chapter.slug}.json`), JSON.stringify({ ...chapter, puzzles }));
}
process.exit(failed ? 1 : 0);
