#!/usr/bin/env python3
"""Vérificateur des contenus extraits des livres « Cherche et Diagnostique ».

Contrôle chaque chapitre (content/books/<livre>/<NN>-<slug>.json) et chaque
book.json : JSON strict en UTF-8, champs obligatoires, grille carrée en A–Z,
relecture de chaque placement dans la grille (8 directions), un placement par
terme, forme grille de "fr" égale à "word", nombre de termes, définitions,
questions, vignettes, cohérence avec book.json.

Usage :
    python3 -I tools/books/check_books.py                 # tout content/books/
    python3 -I tools/books/check_books.py content/books/anatomie-myologie [...]

Un argument peut être un dossier de livre (contient book.json), un dossier
parent de livres, ou un fichier JSON de chapitre.
Code de sortie : 0 si aucune erreur bloquante, 1 sinon.
Les définitions vides sont des AVERTISSEMENTS (à signaler, jamais à inventer).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "content" / "books"
EXPECTED_TERMS = 60
DIRECTIONS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FILE_RE = re.compile(r"^(\d{2})-([a-z0-9-]+)\.json$")
CHAPTER_KEYS = [
    "book", "order", "slug", "title", "description", "summary", "key_points",
    "pitfalls", "red_flags", "figures", "terms", "grid", "placements",
    "questions", "vignettes", "references",
]
BOOK_KEYS = [
    "slug", "title", "authors", "edition", "year", "chapter_count",
    "word_count", "bibliography", "credits", "notes",
]


def grid_form(text: str) -> str:
    """Majuscules, accents retirés (É→E, Ç→C, Œ→OE, Æ→AE), tout sauf A–Z retiré."""
    text = (text.replace("Œ", "OE").replace("œ", "oe")
                .replace("Æ", "AE").replace("æ", "ae"))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z]", "", text.upper())


def find_all(rows: list[str], word: str) -> list[tuple[int, int, int, int]]:
    n = len(rows)
    out = []
    for r in range(n):
        for c in range(len(rows[r])):
            if rows[r][c] != word[0]:
                continue
            for dr, dc in DIRECTIONS:
                rr, cc = r + dr * (len(word) - 1), c + dc * (len(word) - 1)
                if not (0 <= rr < n and 0 <= cc < len(rows[r])):
                    continue
                if all(rows[r + dr * k][c + dc * k] == ch for k, ch in enumerate(word)):
                    out.append((r, c, dr, dc))
    return out


def load_json(path: Path, errors: list[str]):
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"lecture/UTF-8 impossible : {exc}")
        return None
    def reject_constant(name):        # NaN, Infinity : hors JSON strict
        raise ValueError(f"constante non JSON : {name}")

    try:
        return json.loads(text, parse_constant=reject_constant)
    except ValueError as exc:
        errors.append(f"JSON invalide : {exc}")
        return None


def is_i18n(value, key: str, errors: list[str], *, allow_empty: bool = False) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("fr"), str):
        errors.append(f"{key} : objet {{\"fr\": texte}} attendu")
        return False
    if not allow_empty and not value["fr"].strip():
        errors.append(f"{key}.fr est vide")
        return False
    return True


def check_text_list(data, key, errors):
    items = data.get(key)
    if not isinstance(items, list):
        errors.append(f"{key} : liste attendue")
        return
    for i, item in enumerate(items):
        is_i18n(item, f"{key}[{i}]", errors)


def check_chapter(path: Path, book_dir_name: str | None, expected_terms: int):
    errors: list[str] = []
    warnings: list[str] = []
    data = load_json(path, errors)
    if data is None:
        return errors, warnings, None
    if not isinstance(data, dict):
        return ["la racine doit être un objet"], warnings, None
    missing = [k for k in CHAPTER_KEYS if k not in data]
    if missing:
        errors.append("champs manquants : " + ", ".join(missing))
        return errors, warnings, None

    # Identité du chapitre
    if book_dir_name is not None and data["book"] != book_dir_name:
        errors.append(f"book = {data['book']!r} ≠ dossier {book_dir_name!r}")
    if not isinstance(data["order"], int) or isinstance(data["order"], bool) or data["order"] < 1:
        errors.append("order : entier ≥ 1 attendu")
    if not isinstance(data["slug"], str) or not SLUG_RE.match(data["slug"]):
        errors.append(f"slug non kebab-case ASCII : {data['slug']!r}")
    m = FILE_RE.match(path.name)
    if not m:
        errors.append("nom de fichier attendu : NN-slug.json")
    elif isinstance(data["order"], int) and (int(m.group(1)) != data["order"] or m.group(2) != data["slug"]):
        errors.append(f"nom de fichier incohérent avec order/slug ({data['order']}, {data['slug']})")
    is_i18n(data["title"], "title", errors)
    is_i18n(data["description"], "description", errors, allow_empty=True)
    if is_i18n(data["summary"], "summary", errors, allow_empty=True) and not data["summary"]["fr"].strip():
        warnings.append("summary.fr est vide")
    for key in ("key_points", "pitfalls", "red_flags"):
        check_text_list(data, key, errors)

    # Figures et références
    if not isinstance(data["figures"], list):
        errors.append("figures : liste attendue")
    else:
        for i, fig in enumerate(data["figures"]):
            if not isinstance(fig, dict) or not isinstance(fig.get("caption"), str) or not fig["caption"].strip():
                errors.append(f"figures[{i}].caption vide ou absente")
            elif not isinstance(fig.get("source", ""), str):
                errors.append(f"figures[{i}].source : texte attendu")
    if not isinstance(data["references"], list):
        errors.append("references : liste attendue")
    else:
        for i, ref in enumerate(data["references"]):
            if not isinstance(ref, dict) or not isinstance(ref.get("citation"), str) or not ref["citation"].strip():
                errors.append(f"references[{i}].citation vide ou absente")
            elif not isinstance(ref.get("url", ""), str):
                errors.append(f"references[{i}].url : texte attendu")

    # Grille
    grid = data["grid"]
    rows: list[str] = []
    grid_ok = False
    if not isinstance(grid, dict) or not isinstance(grid.get("rows"), list) or not isinstance(grid.get("size"), int):
        errors.append("grid : {\"size\": entier, \"rows\": [...]} attendu")
    else:
        rows = grid["rows"]
        size = grid["size"]
        bad = [i for i, r in enumerate(rows) if not isinstance(r, str) or not re.fullmatch(r"[A-Z]+", r)]
        if bad:
            errors.append(f"grid.rows : lignes hors A–Z : {bad[:5]}")
        elif len(rows) != size or any(len(r) != size for r in rows):
            errors.append(f"grille non carrée ou taille ≠ {size} : {len(rows)} lignes, longueurs {sorted({len(r) for r in rows})}")
        else:
            grid_ok = True

    # Termes
    terms = data["terms"]
    words: list[str] = []
    if not isinstance(terms, list):
        errors.append("terms : liste attendue")
        terms = []
    for i, t in enumerate(terms):
        if not isinstance(t, dict):
            errors.append(f"terms[{i}] : objet attendu")
            words.append("")
            continue
        w = t.get("word")
        if not isinstance(w, str) or not re.fullmatch(r"[A-Z]+", w):
            errors.append(f"terms[{i}].word hors A–Z : {w!r}")
            words.append("")
            continue
        words.append(w)
        fr = t.get("fr")
        if not isinstance(fr, str) or not fr.strip():
            errors.append(f"terms[{i}].fr vide ({w})")
        elif grid_form(fr) != w:
            errors.append(f"terms[{i}] : forme grille de fr {fr!r} = {grid_form(fr)!r} ≠ {w!r}")
        d = t.get("definition")
        if not isinstance(d, dict) or not isinstance(d.get("fr"), str):
            errors.append(f"terms[{i}].definition : objet {{\"fr\"}} attendu ({w})")
        elif not d["fr"].strip():
            warnings.append(f"définition manquante dans le glossaire : {w}")
    if len(terms) != expected_terms:
        errors.append(f"{len(terms)} termes (attendu : {expected_terms})")
    dup = sorted({w for w in words if w and words.count(w) > 1})
    if dup:
        errors.append("termes en double : " + ", ".join(dup))

    # Placements
    placements = data["placements"]
    if not isinstance(placements, list):
        errors.append("placements : liste attendue")
        placements = []
    placed: dict[int, int] = {}
    for i, p in enumerate(placements):
        if not isinstance(p, dict):
            errors.append(f"placements[{i}] : objet attendu")
            continue
        ti = p.get("term_index")
        if not isinstance(ti, int) or not (0 <= ti < len(words)):
            errors.append(f"placements[{i}].term_index invalide : {ti!r}")
            continue
        placed[ti] = placed.get(ti, 0) + 1
        w = words[ti]
        if p.get("word") != w:
            errors.append(f"placements[{i}].word {p.get('word')!r} ≠ terms[{ti}].word {w!r}")
        r, c, dr, dc = (p.get(k) for k in ("row", "col", "d_row", "d_col"))
        if not all(isinstance(v, int) for v in (r, c, dr, dc)) or dr not in (-1, 0, 1) or dc not in (-1, 0, 1) or (dr, dc) == (0, 0):
            errors.append(f"placements[{i}] ({w}) : row/col/d_row/d_col invalides")
            continue
        if not grid_ok or not w:
            continue
        n = len(rows)
        cells = [(r + dr * k, c + dc * k) for k in range(len(w))]
        if not all(0 <= rr < n and 0 <= cc < n for rr, cc in cells):
            errors.append(f"placements[{i}] ({w}) sort de la grille")
            continue
        read = "".join(rows[rr][cc] for rr, cc in cells)
        if read != w:
            errors.append(f"placements[{i}] : la grille donne {read!r} au lieu de {w!r} en ({r},{c}) dir ({dr},{dc})")
        occ = p.get("occurrences")
        real = len(find_all(rows, w))
        if occ != real:
            errors.append(f"placements[{i}] ({w}) : occurrences = {occ!r}, recherche = {real}")
    for ti, w in enumerate(words):
        if not w:
            continue
        if placed.get(ti, 0) == 0:
            hits = find_all(rows, w) if grid_ok else []
            errors.append(f"aucun placement pour {w}" + ("" if hits else " (introuvable dans la grille)"))
        elif placed[ti] > 1:
            errors.append(f"{placed[ti]} placements pour {w}")

    # Questions et vignettes
    qs = data["questions"]
    if not isinstance(qs, list) or not qs:
        errors.append("au moins 1 question attendue")
    else:
        for i, q in enumerate(qs):
            is_i18n(q, f"questions[{i}]", errors)
    vg = data["vignettes"]
    if not isinstance(vg, list):
        errors.append("vignettes : liste attendue")
    else:
        for i, v in enumerate(vg):
            if not isinstance(v, dict):
                errors.append(f"vignettes[{i}] : objet attendu")
                continue
            is_i18n(v.get("case"), f"vignettes[{i}].case", errors)
            is_i18n(v.get("answer"), f"vignettes[{i}].answer", errors)

    stats = {
        "order": data.get("order"),
        "terms": len(terms),
        "questions": len(qs) if isinstance(qs, list) else 0,
        "vignettes": len(vg) if isinstance(vg, list) else 0,
        "missing_defs": sum(1 for t in terms if isinstance(t, dict) and isinstance(t.get("definition"), dict) and not str(t["definition"].get("fr", "")).strip()),
        "multi": sum(1 for p in placements if isinstance(p, dict) and isinstance(p.get("occurrences"), int) and p["occurrences"] > 1),
    }
    return errors, warnings, stats


def check_book_json(path: Path, dir_name: str, chapters: list[dict]):
    errors: list[str] = []
    warnings: list[str] = []
    data = load_json(path, errors)
    if data is None:
        return errors, warnings, None
    if not isinstance(data, dict):
        return ["la racine doit être un objet"], warnings, None
    missing = [k for k in BOOK_KEYS if k not in data]
    if missing:
        errors.append("champs manquants : " + ", ".join(missing))
        return errors, warnings, data
    if data["slug"] != dir_name:
        errors.append(f"slug {data['slug']!r} ≠ dossier {dir_name!r}")
    is_i18n(data["title"], "title", errors)
    if not isinstance(data["authors"], list) or not all(isinstance(a, str) and a.strip() for a in data["authors"]):
        errors.append("authors : liste de textes attendue")
    for key in ("bibliography", "credits", "notes"):
        if not isinstance(data[key], list):
            errors.append(f"{key} : liste attendue")
    if isinstance(data["bibliography"], list):
        for i, ref in enumerate(data["bibliography"]):
            if not isinstance(ref, dict) or not isinstance(ref.get("citation"), str) or not ref["citation"].strip():
                errors.append(f"bibliography[{i}].citation vide ou absente")
    if data["chapter_count"] != len(chapters):
        errors.append(f"chapter_count = {data['chapter_count']} mais {len(chapters)} fichiers de chapitre")
    total = sum(c["terms"] for c in chapters)
    if data["word_count"] != total:
        errors.append(f"word_count = {data['word_count']} mais {total} termes dans les chapitres")
    orders = sorted(c["order"] for c in chapters if isinstance(c.get("order"), int))
    if orders != list(range(1, len(chapters) + 1)):
        errors.append(f"numéros de chapitre non consécutifs : {orders}")
    return errors, warnings, data


def collect_targets(args: list[str]) -> list[tuple[Path, list[Path], bool]]:
    """Renvoie [(dossier_livre, [fichiers chapitres], livre_complet)]."""
    targets: list[tuple[Path, list[Path], bool]] = []
    roots = [Path(a) for a in args] or [DEFAULT_ROOT]
    for root in roots:
        if root.is_file():
            targets.append((root.parent, [root], False))
            continue
        if not root.is_dir():
            targets.append((root, [], False))
            continue
        is_book = (root / "book.json").exists() or any(FILE_RE.match(p.name) for p in root.glob("*.json"))
        book_dirs = [root] if is_book else sorted(p for p in root.iterdir() if p.is_dir())
        for bd in book_dirs:
            files = sorted(p for p in bd.glob("*.json") if p.name != "book.json")
            targets.append((bd, files, True))
    return targets


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="dossiers de livres, dossier parent ou fichiers de chapitre")
    ap.add_argument("--quiet", action="store_true", help="n'affiche pas le détail des avertissements")
    ns = ap.parse_args(argv)

    n_files = n_ok = n_err = n_warn = 0
    for book_dir, files, whole_book in collect_targets(ns.paths):
        book_json = book_dir / "book.json"
        if not book_dir.is_dir():
            n_files += 1
            n_err += 1
            print(f"ERREUR  {book_dir} : introuvable")
            continue
        expected = EXPECTED_TERMS
        if book_json.exists():
            try:
                bj = json.loads(book_json.read_text(encoding="utf-8"))
                expected = int(bj.get("terms_per_chapter", EXPECTED_TERMS))
            except (ValueError, OSError, TypeError):
                pass
        chapter_stats = []
        print(f"== {book_dir}")
        for f in files:
            n_files += 1
            errs, warns, stats = check_chapter(f, book_dir.name, expected)
            if stats:
                chapter_stats.append(stats)
            label = "ERREUR" if errs else "OK"
            extra = ""
            if stats:
                extra = (f" ({stats['terms']} termes, {stats['questions']} questions, {stats['vignettes']} vignettes"
                         f", {stats['multi']} mots à plusieurs occurrences"
                         + (f", {stats['missing_defs']} définitions manquantes" if stats['missing_defs'] else "") + ")")
            print(f"{label:7s} {f.name}{extra}")
            for e in errs:
                print(f"          ERREUR : {e}")
            if not ns.quiet:
                for w in warns:
                    print(f"          AVERTISSEMENT : {w}")
            n_err += bool(errs)
            n_ok += not errs
            n_warn += len(warns)
        if not whole_book:
            continue
        n_files += 1
        if not book_json.exists():
            n_err += 1
            print("ERREUR  book.json absent")
            continue
        errs, warns, _ = check_book_json(book_json, book_dir.name, chapter_stats)
        if not files:
            errs.append("aucun fichier de chapitre")
        print(f"{'ERREUR' if errs else 'OK':7s} book.json")
        for e in errs:
            print(f"          ERREUR : {e}")
        n_err += bool(errs)
        n_ok += not errs
        n_warn += len(warns)
    print(f"Total : {n_files} fichiers, {n_ok} OK, {n_err} en erreur, {n_warn} avertissements")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
