"""Convertit les livres extraits (content/books/<livre>/) en charges d'import pour public.admin_import_chapter.

Usage : python3 -I tools/books/to_payloads.py <dossier de sortie>

Sortie : un fichier <discipline>.json par livre, tableau de chapitres au format de admin_import_chapter
(voir supabase/migrations/20261111000300_functions.sql), plus manifest.json.

Règles :
- le texte des livres est repris tel quel ; rien n'est traduit ni complété ;
- une définition absente du livre reste vide (objet {}) : le terme reste dans la grille, sans fiche ;
- les vignettes deviennent des questions ouvertes avec leur réponse ; les questions de révision n'ont pas de corrigé ;
- pièges, signes d'alerte et corrélations cliniques gardent leur nature dans key_points[].kind ;
- la source de chaque chapitre est le livre lui-même (auteurs, titre, édition, année, pages).
Chaque grille est revérifiée ici avec les mêmes règles que app.puzzle_errors avant tout import.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOKS = ROOT / 'content' / 'books'

# livre extrait -> discipline de l'application
DISCIPLINES = {
    'physiologie-generale': 'physiologie',
    'anatomie-osteologie': 'anatomie-osteologie',
    'anatomie-myologie': 'anatomie-myologie',
    'anatomie-innervation': 'anatomie-innervation',
    'anatomie-vascularisation': 'anatomie-vascularisation',
    'anatomie-organes': 'anatomie-organes',
    'pharmacologie': 'pharmacologie',
    'semiologie': 'semiologie',
}
KINDS = (('key_points', 'key'), ('pitfalls', 'pitfall'), ('red_flags', 'red_flag'), ('clinical_correlations', 'clinical'))


def grid_form(text: str) -> str:
    """Même résultat que app.grid_form : majuscules, sans accents, sans espaces ni ponctuation."""
    s = text.upper().replace('Œ', 'OE').replace('Æ', 'AE')
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub('[^A-Z]', '', s)


def puzzle_errors(grid: list[str], size: int, words: list[dict], labels: list[str]) -> list[str]:
    errs = []
    if len(grid) != size:
        return ['hauteur de grille incorrecte']
    errs += [f'ligne {i + 1} invalide' for i, row in enumerate(grid) if not re.fullmatch(f'[A-Z]{{{size}}}', row)]
    if errs:
        return errs
    placed = set()
    for w in words:
        expected = grid_form(labels[w['term_index']])
        if expected != w['word']:
            errs.append(f"{w['word']} : ne correspond pas au terme ({expected})")
        for i, ch in enumerate(w['word']):
            r, c = w['row'] + i * w['d_row'], w['col'] + i * w['d_col']
            if not (0 <= r < size and 0 <= c < size) or grid[r][c] != ch:
                errs.append(f"{w['word']} : lettre {i + 1} absente aux coordonnées annoncées")
                break
        placed.add(w['term_index'])
    missing = [labels[i] for i in range(len(labels)) if i not in placed]
    if missing:
        errs.append('termes absents de la grille : ' + ', '.join(missing))
    return errs


def citation(book: dict, chapter: dict) -> str:
    authors = ', '.join(book.get('authors') or [])
    edition = (book.get('edition') or '').split(' (')[0]
    pages = chapter.get('source_pages') or {}
    where = f"chapitre {chapter['order']}"
    if pages.get('first'):
        where += f", p. {pages['first']}–{pages['last']}" if pages.get('last') else f", p. {pages['first']}"
    parts = [p for p in (authors, book['title']['fr'], edition, str(book.get('year') or '')) if p]
    return '. '.join(parts) + f'. {where[0].upper()}{where[1:]}.'


def convert(book_dir: Path) -> tuple[list[dict], list[str]]:
    book = json.loads((book_dir / 'book.json').read_text())
    out, problems = [], []
    for f in sorted(book_dir.glob('[0-9]*.json')):
        ch = json.loads(f.read_text())
        labels = [t['fr'] for t in ch['terms']]
        words = [{k: p[k] for k in ('term_index', 'word', 'row', 'col', 'd_row', 'd_col')} for p in ch['placements']]
        size = ch['grid']['size']
        errs = puzzle_errors(ch['grid']['rows'], size, words, labels)
        if errs:
            problems.append(f'{book_dir.name}/{f.name} : ' + ' ; '.join(errs))
        key_points = [{'fr': kp['fr'], 'kind': kind} for field, kind in KINDS for kp in ch.get(field) or []]
        open_questions = (
            [{'question': v['case'], 'model_answer': v['answer']} for v in ch.get('vignettes') or []]
            + [{'question': {'fr': q['fr']}, 'model_answer': None} for q in ch.get('questions') or []])
        out.append({
            'slug': ch['slug'],
            'order': ch['order'],
            'title': ch['title'],
            'description': ch.get('description') or {},
            'summary': ch['summary'],
            'objectives': [],
            'key_points': key_points,
            'terms': [{'fr': t['fr'],
                       'definition': t['definition'] if (t.get('definition') or {}).get('fr') else {}}
                      for t in ch['terms']],
            'quiz': [],
            'open_questions': open_questions,
            'references': [{'citation': citation(book, ch), 'url': ''}],
            'puzzles': {'fr': {'size': size, 'grid': ch['grid']['rows'], 'directions': 8, 'words': words}},
        })
    return out, problems


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    dest = Path(sys.argv[1])
    dest.mkdir(parents=True, exist_ok=True)
    manifest, all_problems = [], []
    for name, discipline in DISCIPLINES.items():
        chapters, problems = convert(BOOKS / name)
        all_problems += problems
        (dest / f'{discipline}.json').write_text(json.dumps(chapters, ensure_ascii=False, separators=(',', ':')))
        manifest.append({'book': name, 'discipline': discipline, 'chapters': len(chapters),
                         'terms': sum(len(c['terms']) for c in chapters),
                         'empty_definitions': sum(1 for c in chapters for t in c['terms'] if not t['definition'])})
    (dest / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    for m in manifest:
        print(f"{m['discipline']:26} {m['chapters']:3} chapitres {m['terms']:5} termes {m['empty_definitions']:3} définitions vides")
    for p in all_problems:
        print('ERREUR', p)
    return 1 if all_problems else 0


if __name__ == '__main__':
    sys.exit(main())
