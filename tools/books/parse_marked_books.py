#!/usr/bin/env python3
"""Extraction fidèle des livres « Cherche et Diagnostique » balisés (@@MK:…@@) vers JSON.

Livres pris en charge : volumes dont les sections sont délimitées par des repères
invisibles « @@MK:legal@@ », « @@MK:toc@@ », « @@MK:chN@@ », « @@MK:gridN@@ »,
« @@MK:glossary@@ », « @@MK:annex@@ », « @@MK:solutions@@ », « @@MK:catalogue@@ »,
« @@MK:biblio@@ », « @@MK:credits@@ » (Physiologie générale, Anatomie : Ostéologie,
Myologie, Innervation).

Principe
--------
* Le PDF est lu avec `pdftotext -bbox-layout` (poppler) : chaque mot arrive avec ses
  coordonnées. Deux mots séparés de moins de 0,6 pt sont recollés (indices, exposants,
  ponctuation après un italique) ; sinon un espace est inséré.
* Les paragraphes du résumé sont les blocs de pdftotext composés de lignes du corps de
  texte (marge gauche et hauteur de ligne du corps). Un paragraphe interrompu par une
  figure ou un saut de page (dernière ligne justifiée pleine largeur) est recollé.
  Les libellés des schémas (autre position, autre corps) sont écartés.
* La grille (20 lignes de lettres) et la liste « MOTS À TROUVER » (lue colonne par
  colonne) sont relues sur la page de l'exercice ; chaque mot est recherché dans les
  8 directions. Les bandes de surlignage des « Solutions des grilles » (XObjects du
  PDF, lus avec pypdf) servent à choisir l'emplacement voulu par les auteurs quand un
  mot apparaît plusieurs fois, et à vérifier la grille imprimée en solution.
* Le glossaire (2 ou 3 colonnes) est relu mot à mot : l'intitulé, la pastille de
  chapitre et la définition ont chacun leur corps de police.
* Les coupures de fin de ligne après un trait d'union sont recollées en gardant le
  trait d'union, sauf si le mot sans trait d'union est attesté ailleurs dans le livre
  et la forme avec trait d'union jamais (coupure typographique) ; les cas incertains
  sont listés.

Le texte n'est ni reformulé, ni corrigé, ni complété, ni traduit. Toute anomalie est
consignée dans book.json → "notes" et affichée à l'écran.

Glossaire → termes
------------------
Chaque mot de « MOTS À TROUVER » reçoit la définition de l'entrée du glossaire qui porte
la pastille du chapitre et lui correspond le mieux (affectation optimale par chapitre) :
intitulé entier, intitulé sans sa parenthèse (« BOCHDALEK (HERNIE DE) »), contenu de la
parenthèse (« BOL ALIMENTAIRE (BOLUS) »), segment de l'intitulé (« CELLULE SATELLITE »),
forme fléchie d'un segment (« LOMBRICAUX » pour LOMBRICAL), début/fin d'un mot
(« WALLÉRIENNE »). "fr" reprend le segment imprimé dont la forme grille est le mot, sinon
le mot lui-même. Un rapprochement approximatif (sous-chaîne commune) est signalé
« À VALIDER » dans les notes.

Champs ajoutés au schéma de chapitre
------------------------------------
  clinical_correlations  puces « Corrélations cliniques » sans vignette (Ostéologie)
  source_pages           pages du PDF couvertes par le chapitre (1re et dernière)
  terms[].glossary_term  intitulé complet du glossaire quand il diffère de "fr"
  terms[].glossary_match type de correspondance utilisé (voir ci-dessus)
  placements[].solution_band  vrai si l'emplacement correspond à une bande surlignée
                         des « Solutions des grilles »
book.json ajoute : terms_per_chapter, glossary_entry_count, bibliography_note,
credits_note, source_pdf, extraction.

Usage
-----
  python3 -I tools/books/parse_marked_books.py                      # les 4 livres par défaut
  python3 -I tools/books/parse_marked_books.py --book anatomie-myologie
  python3 -I tools/books/parse_marked_books.py --pdf autre.pdf --slug mon-livre [--txt autre.txt]
  python3 -I tools/books/parse_marked_books.py --dry-run --verbose  # analyse sans écrire

Le .txt facultatif (pdftotext -layout) sert de contre-vérification des grilles et des
listes de mots. Dépendances : python3, pdftotext (poppler-utils), pypdf.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO / "content" / "books"
UPLOADS = Path("/mnt/user-data/uploads")
TXT_DIR = Path("/home/claude/books/txt")
DEFAULT_BOOKS = {
    "physiologie-generale": ("df103a4d-Cherche_et_Diagnostique_Physiologie_Generale.pdf", "Physiologie_Generale.txt"),
    "anatomie-osteologie": ("7fb9ef72-Cherche_et_Diagnostique_Anatomie_Osteologie.pdf", "Anatomie_Osteologie.txt"),
    "anatomie-myologie": ("8d1034f4-Cherche_et_Diagnostique_Anatomie_Myologie.pdf", "Anatomie_Myologie.txt"),
    "anatomie-innervation": ("235ba73f-Cherche_et_Diagnostique_Anatomie_Innervation.pdf", "Anatomie_Innervation.txt"),
}
JOIN_GAP = 0.6          # pt : en dessous, deux mots pdftotext forment un seul mot typographique
DIRECTIONS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
FIG_RE = re.compile(r"^Figure\s+\d+(?:\.\d+)?\s*—")
MARK_RE = re.compile(r"@@MK:([a-z0-9]+)@@")


# --------------------------------------------------------------------------- modèle

@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str

    @property
    def h(self) -> float:
        return self.y1 - self.y0


@dataclass
class Line:
    page: int          # index 0
    block: int
    words: list

    @property
    def x0(self): return min(w.x0 for w in self.words)
    @property
    def x1(self): return max(w.x1 for w in self.words)
    @property
    def y0(self): return min(w.y0 for w in self.words)
    @property
    def y1(self): return max(w.y1 for w in self.words)
    @property
    def h(self): return self.y1 - self.y0
    @property
    def text(self): return words_text(self.words)


def words_text(words) -> str:
    words = sorted(words, key=lambda w: w.x0)
    out = ""
    prev = None
    for w in words:
        if prev is not None and w.x0 - prev.x1 >= JOIN_GAP:
            out += " "
        out += w.text
        prev = w
    return out.strip()


def despace(s: str) -> str:
    return re.sub(r"\s+", "", s)


def grid_form(text: str) -> str:
    """Majuscules, accents retirés (É→E, Ç→C, Œ→OE, Æ→AE), tout sauf A–Z retiré."""
    text = (text.replace("Œ", "OE").replace("œ", "oe")
                .replace("Æ", "AE").replace("æ", "ae"))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z]", "", text.upper())


def slugify(text: str) -> str:
    text = text.replace("Œ", "OE").replace("œ", "oe").replace("Æ", "AE").replace("æ", "ae")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def find_all(rows, word):
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


def occ_box(occ, length):
    r, c, dr, dc = occ
    r2, c2 = r + dr * (length - 1), c + dc * (length - 1)
    return (min(r, r2), max(r, r2), min(c, c2), max(c, c2))


class Notes:
    def __init__(self):
        self.items: list[str] = []

    def add(self, msg: str):
        if msg not in self.items:
            self.items.append(msg)
            print("   ! " + msg)


# --------------------------------------------------------------------------- lecture PDF

def load_bbox(pdf: Path):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "bbox.html"
        subprocess.run(["pdftotext", "-bbox-layout", str(pdf), str(out)], check=True)
        data = out.read_text(encoding="utf-8")
    data = re.sub(r"<!DOCTYPE[^>]*>", "", data).replace(' xmlns="http://www.w3.org/1999/xhtml"', "")
    root = ET.fromstring(data)
    pages, sizes = [], []
    for pi, pg in enumerate(root.iter("page")):
        sizes.append((float(pg.get("width")), float(pg.get("height"))))
        lines = []
        for bi, bl in enumerate(pg.iter("block")):
            for ln in bl.iter("line"):
                ws = [Word(float(w.get("xMin")), float(w.get("yMin")), float(w.get("xMax")), float(w.get("yMax")), w.text or "")
                      for w in ln.iter("word")]
                ws = [w for w in ws if w.text]
                if ws:
                    lines.append(Line(pi, bi, ws))
        pages.append(lines)
    return pages, sizes


def extract_markers(pages):
    """Retire les mots « @@MK:…@@ » et renvoie {nom: index de page}."""
    markers = {}
    for pi, lines in enumerate(pages):
        kept = []
        for l in lines:
            ws = []
            for w in l.words:
                m = MARK_RE.search(w.text)
                if m:
                    markers.setdefault(m.group(1), pi)
                    rest = MARK_RE.sub("", w.text)
                    if rest:
                        ws.append(Word(w.x0, w.y0, w.x1, w.y1, rest))
                else:
                    ws.append(w)
            if ws:
                l.words = ws
                kept.append(l)
        pages[pi] = kept
    return markers


def mat_mul(a, b):
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return (a0 * b0 + a1 * b2, a0 * b1 + a1 * b3, a2 * b0 + a3 * b2, a2 * b1 + a3 * b3,
            a4 * b0 + a5 * b2 + b4, a4 * b1 + a5 * b3 + b5)


def form_bands(reader, page_index):
    """Rectangles (repère pdftotext : origine en haut à gauche) des XObjects Form dessinés sur la page."""
    from pypdf.generic import ContentStream
    page = reader.pages[page_index]
    height = float(page.mediabox.height)
    xo = page["/Resources"].get("/XObject", {})
    ctm, stack, out = (1, 0, 0, 1, 0, 0), [], []
    for operands, op in ContentStream(page.get_contents(), reader).operations:
        if op == b"q":
            stack.append(ctm)
        elif op == b"Q":
            ctm = stack.pop() if stack else (1, 0, 0, 1, 0, 0)
        elif op == b"cm":
            ctm = mat_mul(tuple(float(v) for v in operands), ctm)
        elif op == b"Do" and operands and operands[0] in xo:
            o = xo[operands[0]].get_object()
            if o.get("/Subtype") != "/Form":
                continue
            bb = [float(v) for v in o["/BBox"]]
            m = mat_mul(tuple(float(v) for v in o.get("/Matrix", [1, 0, 0, 1, 0, 0])), ctm)
            pts = [(m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]) for x in (bb[0], bb[2]) for y in (bb[1], bb[3])]
            xs = [p[0] for p in pts]
            ys = [height - p[1] for p in pts]
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


# --------------------------------------------------------------------------- texte

class Hyphens:
    """Décide du sort des traits d'union en fin de ligne à partir des mots attestés dans le livre."""

    def __init__(self, pages):
        self.corpus = Counter()
        for lines in pages:
            for l in lines:
                toks = l.text.split()
                for i, t in enumerate(toks):
                    if i == len(toks) - 1 and t.endswith("-"):
                        continue
                    core = self.core(t)
                    if core:
                        self.corpus[core.lower()] += 1
        self.log: list[tuple[str, str, str]] = []

    @staticmethod
    def core(t: str) -> str:
        return t.strip(".,;:!?()[]«»\"“”'’…")

    def join(self, left: str, right: str, ctx: str) -> str:
        a = self.core(left.split()[-1][:-1])
        b = self.core(right.split()[0])
        compound, fused = f"{a}-{b}".lower(), f"{a}{b}".lower()
        if self.corpus[compound]:
            decision, out = "composé attesté, trait d'union conservé", left + right
        elif self.corpus[fused]:
            decision, out = "coupure typographique, trait d'union retiré", left[:-1] + right
        else:
            decision, out = "incertain, trait d'union conservé", left + right
        self.log.append((ctx, f"{a}-|{b}", decision))
        return out


def join_lines(texts, hy: Hyphens, ctx: str) -> str:
    out = ""
    for t in texts:
        t = t.strip()
        if not t:
            continue
        if not out:
            out = t
        elif re.search(r"\w-$", out) and re.match(r"\w", t):
            out = hy.join(out, t, ctx)
        else:
            out += " " + t
    return out


def is_running_header(l: Line) -> bool:
    return l.y0 < 65 and bool(re.match(r"CHAPITRE\d+·", despace(l.text)))


def is_folio(l: Line, page_h: float) -> bool:
    return l.y0 > page_h - 60 and bool(re.fullmatch(r"\d{1,3}", l.text.strip()))


def merge_rows(lines, tol=2.5):
    """Regroupe des lignes de même ligne de base (yMax proches) ; renvoie des listes de mots triées en x."""
    rows = []
    for l in sorted(lines, key=lambda l: l.y1):
        if rows and abs(l.y1 - rows[-1]["y1"]) < tol:
            rows[-1]["words"].extend(l.words)
            rows[-1]["lines"].append(l)
        else:
            rows.append({"y1": l.y1, "words": list(l.words), "lines": [l]})
    for r in rows:
        r["words"].sort(key=lambda w: w.x0)
    return rows


# --------------------------------------------------------------------------- livre

class Book:
    def __init__(self, slug: str, pdf: Path, txt: Path | None, verbose: bool):
        self.slug, self.pdf, self.txt, self.verbose = slug, pdf, txt, verbose
        self.notes = Notes()
        self.pages, self.sizes = load_bbox(pdf)
        self.markers = extract_markers(self.pages)
        self.hy = Hyphens(self.pages)
        last = " ".join(l.text for l in self.pages[-1])
        self.n_content = len(self.pages) - 1 if "AUSOMMAIRE" in despace(last) else len(self.pages)
        self.review: list[str] = []
        from pypdf import PdfReader
        self.reader = PdfReader(str(pdf))

    # ----- utilitaires de pages
    def page_h(self, pi):
        return self.sizes[pi][1]

    def content_lines(self, pi):
        return [l for l in self.pages[pi] if not is_running_header(l) and not is_folio(l, self.page_h(pi))]

    def section_end(self, start_pi):
        later = [p for p in self.markers.values() if p > start_pi]
        return min(later) if later else self.n_content

    def chapter_numbers(self):
        return sorted(int(k[2:]) for k in self.markers if re.fullmatch(r"ch\d+", k))

    # ----- métadonnées
    def parse_legal(self):
        """Tableau « libellé → valeur » de la page légale ; une valeur peut tenir sur plusieurs lignes."""
        meta = {}
        pi = self.markers.get("legal")
        if pi is None:
            self.notes.add("section « Informations légales » absente")
            return meta
        lines = self.content_lines(pi)
        for l in lines:
            m = re.match(r"©\s*(\d{4})", l.text)
            if m:
                meta["year"] = int(m.group(1))
        labels = {"Titre": "title", "Auteurs": "authors", "Édition": "edition"}
        value_lines = [l for l in lines if l.x0 > 120]
        for lab in lines:
            key = labels.get(lab.text.strip())
            if key is None or lab.x0 > 120:
                continue
            cy = (lab.y0 + lab.y1) / 2
            blocks = {}
            for v in value_lines:
                blocks.setdefault(v.block, []).append(v)
            hit = [ls for ls in blocks.values() if min(v.y0 for v in ls) - 3 <= cy <= max(v.y1 for v in ls) + 3]
            if hit:
                ls = sorted(hit[0], key=lambda v: v.y0)
                meta[key] = join_lines([v.text for v in ls], self.hy, "informations légales")
            else:
                self.notes.add(f"informations légales : valeur de « {lab.text} » introuvable")
        return meta

    def parse_cover_stats(self):
        text = " ".join(words_text(r["words"]) for r in merge_rows(self.pages[0]))
        stats = {}
        m = re.search(r"(\d+)\s+chapitres", text)
        if m:
            stats["chapters"] = int(m.group(1))
        m = re.search(r"(\d+)\s+mots cachés", text)
        if m:
            stats["words"] = int(m.group(1))
        return stats

    def parse_toc(self):
        toc = {}
        pi = self.markers.get("toc")
        if pi is None:
            return toc
        for row in merge_rows(self.content_lines(pi)):
            m = re.match(r"^(\d{2})\s+(.+?)\s+(\d+)\s+(\d+)$", words_text(row["words"]))
            if m:
                toc[int(m.group(1))] = m.group(2)
        return toc

    # ----- chapitres
    def parse_chapter(self, n, toc_title):
        start = self.markers[f"ch{n}"]
        grid_pi = self.markers.get(f"grid{n}")
        if grid_pi is None:
            raise SystemExit(f"{self.slug} : repère grid{n} absent")
        end = self.section_end(grid_pi)
        ctx = f"chapitre {n}"
        chapter = {"order": n}

        # Page d'ouverture : titre, sous-titre
        opening = self.content_lines(start)
        chap_line = next((l for l in opening if despace(l.text).startswith("CHAPITRE")), None)
        if chap_line is None:
            raise SystemExit(f"{self.slug} : ligne « CHAPITRE {n} » introuvable p. {start + 1}")
        top = [l for l in opening if l.y0 < chap_line.y0 + 190]
        tl = sorted([l for l in top if l.h > 30 and not re.fullmatch(r"\d{1,2}", l.text.strip())], key=lambda l: l.y0)
        title = re.sub(r"^\d{1,2}\s+", "", " ".join(l.text for l in tl)).strip()
        sl = sorted([l for l in top if 16.5 < l.h < 17.6 and l is not chap_line and l.y0 > chap_line.y0
                     and abs(l.x0 - chap_line.x0) < 3], key=lambda l: l.y0)
        subtitle = join_lines([l.text for l in sl], self.hy, ctx + " (sous-titre)")
        if toc_title and despace(toc_title) != despace(title):
            self.notes.add(f"{ctx} : titre de la page d'ouverture « {title} » ≠ sommaire « {toc_title} » (titre de la page d'ouverture retenu)")
        if not title:
            title = toc_title or ""
            self.notes.add(f"{ctx} : titre absent de la page d'ouverture, repris du sommaire")
        chapter["title"] = title
        chapter["subtitle"] = subtitle

        # Figures (toutes les pages avant la grille)
        figures, consumed = [], set()
        for pi in range(start, grid_pi):
            lines = sorted(self.content_lines(pi), key=lambda l: (l.y0, l.x0))
            for i, l in enumerate(lines):
                if not FIG_RE.match(l.text) or id(l) in consumed:
                    continue
                cap = [x for x in lines if x.block == l.block]
                consumed.update(id(x) for x in cap)
                rest = [x for x in lines if x.y0 > cap[-1].y0 and id(x) not in consumed]
                source = ""
                if rest and rest[0].text.startswith("Source"):
                    src = [x for x in lines if x.block == rest[0].block]
                    consumed.update(id(x) for x in src)
                    source = re.sub(r"^Source\s*:\s*", "", join_lines([x.text for x in src], self.hy, ctx + " (source)"))
                figures.append({"caption": join_lines([x.text for x in cap], self.hy, ctx + " (légende)"), "source": source})
        chapter["figures"] = figures

        # Résumé théorique et corrélations cliniques
        body_cands, corr, dropped, state, corr_heading = [], [], [], None, ""
        for pi in range(start + 1, grid_pi):
            for l in sorted(self.content_lines(pi), key=lambda l: (l.y0, l.x0)):
                t = l.text
                if id(l) in consumed:
                    continue
                if t == "Résumé théorique":
                    state = "summary"
                    continue
                if t.startswith("Corrélations cliniques"):
                    state, corr_heading = "corr", t
                    continue
                if state == "summary":
                    body_cands.append(l)
                elif state == "corr":
                    corr.append(l)
                else:
                    dropped.append(l)
        if not body_cands:
            self.notes.add(f"{ctx} : « Résumé théorique » introuvable")
        paragraphs, dropped2 = self.summary_paragraphs(body_cands, ctx)
        dropped += dropped2
        chapter["summary"] = "\n\n".join(paragraphs)
        chapter["vignettes"], chapter["clinical_correlations"] = self.parse_correlations(corr, corr_heading, ctx)
        for l in dropped:
            self.review.append(f"{ctx} p.{l.page + 1} écarté (libellé de schéma ?) : {l.text}")

        # Grille et mots
        chapter["grid_rows"], chapter["words"] = self.parse_grid_page(grid_pi, ctx)

        # Questions médicales
        chapter["questions"] = self.parse_questions(range(grid_pi, end), ctx)
        chapter["pages"] = (start + 1, end)
        return chapter

    def summary_paragraphs(self, lines, ctx):
        if not lines:
            return [], []
        long_lines = [l for l in lines if len(l.text) > 50]
        left = Counter(round(l.x0, 1) for l in long_lines).most_common(1)[0][0]
        body_h = Counter(round(l.h, 2) for l in long_lines if abs(l.x0 - left) < 1.5).most_common(1)[0][0]
        strict = [l for l in lines if abs(l.x0 - left) < 1.5 and abs(l.h - body_h) < 0.35]
        body_blocks = {(l.page, l.block) for l in strict}
        body = [l for l in lines if (l.page, l.block) in body_blocks and abs(l.x0 - left) < 1.5]
        dropped = [l for l in lines if l not in body]
        right = max(l.x1 for l in body)
        paras, cur, prev = [], [], None
        for l in body:
            if prev is not None and (l.page, l.block) != (prev.page, prev.block):
                if prev.x1 >= right - 2.5:
                    self.review.append(f"{ctx} p.{l.page + 1} paragraphe recollé (ligne précédente pleine) : « …{prev.text[-40:]} » + « {l.text[:40]}… »")
                else:
                    paras.append(cur)
                    cur = []
            cur.append(l.text)
            prev = l
        if cur:
            paras.append(cur)
        return [join_lines(p, self.hy, ctx + " (résumé)") for p in paras], dropped

    def parse_correlations(self, lines, heading, ctx):
        if not lines:
            if heading:
                self.notes.add(f"{ctx} : rubrique « {heading} » vide")
            return [], []
        if any(l.text.startswith("VIGNETTE") for l in lines):
            vignettes, cur, part = [], None, None
            for l in lines:
                t = l.text
                m = re.match(r"^VIGNETTE\s+(\d+)\s*(.*)$", t)
                if m:
                    cur = {"n": int(m.group(1)), "case": [m.group(2)], "answer": []}
                    vignettes.append(cur)
                    part = "case"
                    continue
                m = re.match(r"^Réponse\s*—\s*(.*)$", t)
                if m and cur is not None:
                    part = "answer"
                    cur["answer"].append(m.group(1))
                    continue
                if cur is None:
                    self.notes.add(f"{ctx} : texte avant la première vignette conservé hors JSON : {t}")
                    continue
                cur[part].append(t)
            out = []
            for i, v in enumerate(vignettes, 1):
                if v["n"] != i:
                    self.notes.add(f"{ctx} : vignettes mal numérotées ({v['n']} au lieu de {i})")
                if not v["answer"]:
                    self.notes.add(f"{ctx} : vignette {v['n']} sans réponse imprimée")
                out.append({"case": {"fr": join_lines(v["case"], self.hy, ctx + " (vignette)")},
                            "answer": {"fr": join_lines(v["answer"], self.hy, ctx + " (réponse)")}})
            return out, []
        # Puces (« Corrélations cliniques » sans vignettes) : un bloc pdftotext par puce.
        pitches = [b.y0 - a.y0 for a, b in zip(lines, lines[1:]) if (a.page, a.block) == (b.page, b.block)]
        pitch = sorted(pitches)[len(pitches) // 2] if pitches else None
        items, prev = [], None
        for l in lines:
            new = prev is None or l.page != prev.page or (
                (l.page, l.block) != (prev.page, prev.block) and (pitch is None or l.y0 - prev.y0 > pitch * 1.12))
            if new:
                items.append([])
            items[-1].append(l.text)
            prev = l
        if len({l.page for l in lines}) > 1:
            self.notes.add(f"{ctx} : corrélations cliniques sur deux pages, découpage des puces à vérifier")
        return [], [{"fr": join_lines(it, self.hy, ctx + " (corrélation)")} for it in items]

    def parse_grid_page(self, pi, ctx):
        lines = self.content_lines(pi)
        hdr = next((l for l in lines if l.text.startswith("MOTS À TROUVER")), None)
        if hdr is None:
            raise SystemExit(f"{self.slug} {ctx} : « MOTS À TROUVER » introuvable p. {pi + 1}")
        rows = []
        for l in sorted(lines, key=lambda l: l.y0):
            if l.y0 >= hdr.y0 - 1:
                continue
            if all(re.fullmatch(r"[A-Z]", w.text) for w in l.words) and len(l.words) >= 8:
                rows.append("".join(w.text for w in sorted(l.words, key=lambda w: w.x0)))
            elif all(re.fullmatch(r"[A-Z]+", w.text) for w in l.words) and len(despace(l.text)) >= 8:
                self.notes.add(f"{ctx} : ligne de grille avec lettres accolées p. {pi + 1} : {l.text}")
                rows.append(despace(l.text))
        size = len(rows)
        if size != 20 or any(len(r) != size for r in rows):
            self.notes.add(f"{ctx} : grille de {size} lignes, longueurs {sorted({len(r) for r in rows})} (20 × 20 attendu)")
        wl = [l for l in lines if l.y0 > hdr.y0 + 3 and l.text.strip()]
        words = [w for l in wl for w in l.words]
        bad = [w.text for w in words if not re.fullmatch(r"[A-Z]+", w.text)]
        if bad:
            self.notes.add(f"{ctx} : éléments inattendus dans « MOTS À TROUVER » : {bad}")
        words = [w for w in words if re.fullmatch(r"[A-Z]+", w.text)]
        xs = sorted({round(w.x0) for w in words})
        cols, cur = [], []
        for x in xs:
            if cur and x - cur[-1] > 15:
                cols.append(cur)
                cur = []
            cur.append(x)
        if cur:
            cols.append(cur)
        col_of = {x: i for i, c in enumerate(cols) for x in c}
        ordered = [w.text for w in sorted(words, key=lambda w: (col_of[round(w.x0)], w.y0))]
        if ordered != sorted(ordered):
            self.notes.add(f"{ctx} : la liste « MOTS À TROUVER » lue colonne par colonne n'est pas alphabétique")
        return rows, ordered

    def parse_questions(self, page_range, ctx):
        lines = []
        for pi in page_range:
            lines += sorted(self.content_lines(pi), key=lambda l: (l.y0, l.x0))
        i0 = next((i for i, l in enumerate(lines) if l.text == "Questions médicales"), None)
        if i0 is None:
            self.notes.add(f"{ctx} : « Questions médicales » introuvable")
            return []
        seg = []
        for l in lines[i0 + 1:]:
            if l.text.startswith("Fiche d'évaluation") or l.text.startswith("Fiche d’évaluation"):
                break
            seg.append(l)
        qs = []
        for page in sorted({l.page for l in seg}):
            for row in merge_rows([l for l in seg if l.page == page]):
                ws = row["words"]
                if re.fullmatch(r"\d{1,2}", ws[0].text) and ws[0].x0 < 70:
                    qs.append({"n": int(ws[0].text), "lines": [words_text(ws[1:])]})
                elif qs:
                    qs[-1]["lines"].append(words_text(ws))
                else:
                    self.notes.add(f"{ctx} : texte avant la première question ignoré : {words_text(ws)}")
        for i, q in enumerate(qs, 1):
            if q["n"] != i:
                self.notes.add(f"{ctx} : questions mal numérotées ({q['n']} au lieu de {i})")
        return [{"fr": join_lines(q["lines"], self.hy, ctx + " (question)")} for q in qs]

    # ----- glossaire
    def parse_glossary(self):
        start = self.markers.get("glossary")
        if start is None:
            self.notes.add("glossaire absent")
            return [], None
        end = self.section_end(start)
        lines = [l for pi in range(start, end) for l in self.content_lines(pi)]
        heights = Counter(round(w.h, 2) for l in lines for w in l.words)
        h_def = heights.most_common(1)[0][0]
        head_c = Counter(round(w.h, 2) for l in lines for w in l.words
                         if len(w.text) >= 2 and w.text.upper() == w.text and re.search(r"[A-Z]", w.text) and w.h > h_def + 0.5)
        h_head = head_c.most_common(1)[0][0]
        num_c = Counter(round(w.h, 2) for l in lines for w in l.words
                        if w.text.isdigit() and abs(w.h - h_def) > 0.2 and abs(w.h - h_head) > 0.2)
        h_num = num_c.most_common(1)[0][0]
        # colonnes : débuts de ligne fréquents
        x0s = Counter(round(l.x0) for l in lines if abs(l.h - h_def) < 0.3 or abs(l.h - h_head) < 0.3)
        top = x0s.most_common(1)[0][1]
        col_starts = sorted(x for x, c in x0s.items() if c >= top * 0.2)
        merged = []
        for x in col_starts:
            if merged and x - merged[-1] < 20:
                continue
            merged.append(x)
        col_starts = merged

        def col_of(x):
            return max([i for i, s in enumerate(col_starts) if s <= x + 2] or [0])

        # préambule de la 1re page (titre, introduction, légende des pastilles) : tout ce qui
        # précède le premier intitulé d'entrée est écarté
        first_head = min(w.y0 for l in self.content_lines(start) for w in l.words
                         if abs(w.h - h_head) < 0.25 and len(w.text) >= 2)
        stream = []   # lignes visuelles dans l'ordre de lecture : [(classe, mot), ...]
        for pi in range(start, end):
            sub = {}
            for l in self.content_lines(pi):
                if pi == start and l.y1 < first_head - 0.5:
                    continue
                for w in l.words:
                    sub.setdefault((col_of(w.x0), id(l)), []).append(w)
            per_col = {}
            for (ci, _), ws in sub.items():
                per_col.setdefault(ci, []).append(Line(pi, 0, ws))
            for ci in sorted(per_col):
                for row in merge_rows(per_col[ci], tol=2.5):
                    toks = []
                    for w in row["words"]:
                        if len(w.text) == 1 and w.h > h_head + 3:
                            cls = "L"
                        elif abs(w.h - h_head) < 0.25:
                            cls = "H"
                        elif abs(w.h - h_num) < 0.25 and w.text.isdigit():
                            cls = "N"
                        else:
                            cls = "D"
                        toks.append((cls, w))
                    stream.append(toks)
        entries, cur = [], None
        for toks in stream:
            new_row = True
            for cls, w in toks:
                if cls == "L":
                    continue
                if cls == "H" and (cur is None or cur["state"] == "def"):
                    cur = {"head": [[w]], "nums": [], "def": [], "state": "head", "dash": False}
                    entries.append(cur)
                    new_row = False
                    continue
                if cur is None:
                    continue
                if cls == "H" and cur["state"] == "head":
                    if new_row:
                        cur["head"].append([w])
                    else:
                        cur["head"][-1].append(w)
                elif cls == "N" and cur["state"] in ("head", "num"):
                    cur["nums"].append(int(w.text))
                    cur["state"] = "num"
                elif cur["state"] in ("head", "num") and w.text == "—":
                    cur["state"], cur["dash"] = "def", True
                    new_row = True
                    continue
                else:
                    if cur["state"] != "def":
                        cur["state"] = "def"
                        new_row = True
                    if new_row or not cur["def"]:
                        cur["def"].append([w])
                    else:
                        cur["def"][-1].append(w)
                new_row = False
        out = []
        for e in entries:
            head = " ".join(words_text(ws) for ws in e["head"])
            definition = join_lines([words_text(ws) for ws in e["def"]], self.hy, f"glossaire ({head})")
            if not e["nums"] or not e["dash"] or not definition:
                self.notes.add(f"glossaire : entrée mal formée « {head} » (chapitre {e['nums']}, définition « {definition[:40]} »)")
            out.append({"head": head, "chapters": e["nums"], "definition": definition})
        intro = " ".join(l.text for l in self.content_lines(start)[:6])
        m = re.search(r"les\s+(\d+)\s+termes", intro, re.I)
        announced = int(m.group(1)) if m else None
        return out, announced

    # ----- solutions
    def parse_solutions(self):
        start = self.markers.get("solutions")
        if start is None:
            self.notes.add("section « Solutions des grilles » absente")
            return {}
        end = self.section_end(start)
        sols = {}
        for pi in range(start, end):
            mid = self.sizes[pi][0] / 2
            sides = {}
            for l in self.content_lines(pi):
                for side in (0, 1):
                    ws = [w for w in l.words if ((w.x0 + w.x1) / 2 >= mid) == bool(side)]
                    if ws:
                        sides.setdefault(side, []).append(Line(pi, l.block, ws))
            grids = []
            for side, ls in sides.items():
                labels = [l for l in ls if re.match(r"^\d{1,2}\s+—\s+", l.text)]
                letter_lines = [l for l in ls if len(l.words) >= 8 and all(re.fullmatch(r"[A-Z]", w.text) for w in l.words)]
                for lab in labels:
                    n = int(re.match(r"^(\d{1,2})", lab.text).group(1))
                    nxt = min([x.y0 for x in labels if x.y0 > lab.y0] or [1e9])
                    rows = sorted([l for l in letter_lines if lab.y0 < l.y0 < nxt], key=lambda l: l.y0)
                    cells = {}
                    for r, l in enumerate(rows):
                        for c, w in enumerate(sorted(l.words, key=lambda w: w.x0)):
                            cells[(r, c)] = ((w.x0 + w.x1) / 2, (w.y0 + w.y1) / 2)
                    grids.append((n, ["".join(w.text for w in sorted(l.words, key=lambda w: w.x0)) for l in rows], cells))
            bands = form_bands(self.reader, pi)
            for n, rows, cells in grids:
                if not cells:
                    continue
                gx0 = min(x for x, _ in cells.values()) - 6
                gx1 = max(x for x, _ in cells.values()) + 6
                gy0 = min(y for _, y in cells.values()) - 6
                gy1 = max(y for _, y in cells.values()) + 6
                boxes = []
                for (bx0, by0, bx1, by1) in bands:
                    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
                    if not (gx0 <= cx <= gx1 and gy0 <= cy <= gy1):
                        continue
                    inside = [rc for rc, (x, y) in cells.items() if bx0 <= x <= bx1 and by0 <= y <= by1]
                    if inside:
                        rs = [r for r, _ in inside]
                        cs = [c for _, c in inside]
                        boxes.append((min(rs), max(rs), min(cs), max(cs)))
                sols[n] = {"rows": rows, "boxes": boxes, "page": pi + 1}
        return sols

    # ----- bibliographie et crédits
    def parse_biblio(self):
        pi = self.markers.get("biblio")
        if pi is None:
            self.notes.add("bibliographie absente")
            return [], ""
        end = self.section_end(pi)
        lines = []
        for p in range(pi, end):
            lines += sorted(self.content_lines(p), key=lambda l: (l.y0, l.x0))
        lines = [l for l in lines if l.h <= 30]          # titre de page
        cut = next((l for l in lines if l.text.startswith("Crédits des illustrations")), None)
        if cut is not None:                               # crédits sur la même page
            self.credits_anchor = (cut.page, cut.y1)
            lines = [l for l in lines if (l.page, l.y0) < (cut.page, cut.y0)]
        entries, intro = [], []
        for row in merge_rows(lines):
            t = words_text(row["words"])
            m = re.match(r"^(\d+)\.\s+(.*)$", t)
            if m:
                entries.append({"n": int(m.group(1)), "lines": [m.group(2)]})
            elif entries:
                entries[-1]["lines"].append(t)
            else:
                intro.append(t)
        for i, e in enumerate(entries, 1):
            if e["n"] != i:
                self.notes.add(f"bibliographie mal numérotée ({e['n']} au lieu de {i})")
        bib = [{"citation": join_lines(e["lines"], self.hy, "bibliographie"), "url": ""} for e in entries]
        return bib, join_lines(intro, self.hy, "bibliographie (introduction)")

    def parse_credits(self):
        pi = self.markers.get("credits")
        if pi is not None:
            lines = [l for l in self.content_lines(pi) if l.h <= 30]
        elif getattr(self, "credits_anchor", None):
            pi, y = self.credits_anchor
            lines = [l for l in self.content_lines(pi) if l.y0 >= y - 0.5]
        else:
            return [], ""
        lines = sorted(lines, key=lambda l: (l.y0, l.x0))
        hdr = next((l for l in lines if l.text == "Sujet"), None)
        if hdr is None:
            self.notes.add("crédits des illustrations : tableau non reconnu")
            return [], ""
        hdr_row = [l for l in lines if abs(l.y1 - hdr.y1) < 2.5]
        starts = sorted(l.x0 for l in hdr_row)
        intro = join_lines([l.text for l in lines if l.y1 < hdr.y0], self.hy, "crédits (introduction)")
        body = [l for l in lines if l.y0 > hdr.y1 - 1 and l not in hdr_row]

        def col(l):
            return max([i for i, s in enumerate(starts) if s <= l.x0 + 2] or [0])

        blocks = {}
        for l in body:
            blocks.setdefault((col(l), l.block), []).append(l)
        anchors = []
        for (c, _), ls in blocks.items():
            if c == 0:
                cy = sum((l.y0 + l.y1) / 2 for l in ls) / len(ls)
                anchors.append({"cy": cy, "figure": " ".join(l.text for l in sorted(ls, key=lambda l: l.y0)), 1: [], 2: []})
        anchors.sort(key=lambda a: a["cy"])
        for (c, _), ls in blocks.items():
            if c == 0 or not anchors:
                continue
            cy = sum((l.y0 + l.y1) / 2 for l in ls) / len(ls)
            a = min(anchors, key=lambda a: abs(a["cy"] - cy))
            a[min(c, 2)].extend(ls)
        credits = []
        for a in anchors:
            credits.append({
                "figure": a["figure"],
                "subject": join_lines([l.text for l in sorted(a[1], key=lambda l: l.y0)], self.hy, "crédits"),
                "source": join_lines([l.text for l in sorted(a[2], key=lambda l: l.y0)], self.hy, "crédits"),
            })
        return credits, intro


# --------------------------------------------------------------------------- contre-vérification .txt

def txt_grids(path: Path):
    """Grilles et listes de mots relues dans le texte « pdftotext -layout » (contre-vérification)."""
    lines = path.read_text(encoding="utf-8").split("\n")
    out = {}
    i = 0
    while i < len(lines):
        m = re.search(r"@@MK:grid(\d+)@@", lines[i])
        if not m:
            i += 1
            continue
        n = int(m.group(1))
        rows, j = [], i
        while j + 1 < len(lines) and "MOTS À TROUVER" not in lines[j + 1]:
            j += 1
            s = lines[j].strip()
            if re.fullmatch(r"(?:[A-Z] ){7,}[A-Z]", s):
                rows.append(s.replace(" ", ""))
        k = j + 1
        cols = []
        while k + 1 < len(lines) and lines[k + 1].strip() and not re.fullmatch(r"\s*\d+\s*", lines[k + 1]):
            k += 1
            cols.append(lines[k].split())
        words = []
        for c in range(max((len(r) for r in cols), default=0)):
            words += [r[c] for r in cols if c < len(r)]
        out[n] = (rows, words)
        i = k + 1
    return out


# --------------------------------------------------------------------------- assemblage

SEG_TOKEN_RE = re.compile(r"[^\s\-'’(),/;:]+")
MATCH_LABELS = {
    1: "intitulé entier",
    2: "intitulé sans sa parenthèse",
    3: "contenu de la parenthèse",
    4: "segment de l'intitulé",
    5: "forme fléchie (pluriel/féminin) d'un segment de l'intitulé",
    6: "début ou fin d'un mot de l'intitulé",
    7: "rapprochement approximatif",
}
UNMATCHED_COST = 10_000
NO_EDGE = 10 ** 9


def head_segments(head):
    """Segments contigus de l'intitulé (sans parenthèse à l'intérieur) : [(position du 1er mot, texte)]."""
    toks = [(m.start(), m.end()) for m in SEG_TOKEN_RE.finditer(head)]
    out = []
    for i in range(len(toks)):
        for j in range(i, len(toks)):
            seg = head[toks[i][0]:toks[j][1]]
            if "(" not in seg and ")" not in seg:
                out.append((i, seg))
    return out


def inflected(w, form):
    """form (segment de l'intitulé) est-il une forme fléchie de w (mot de la grille) ?"""
    if form == w:
        return False
    if form in (w + "S", w + "X", w + "E", w + "ES"):
        return True
    if w.endswith("AL") and form in (w[:-2] + "AUX",):
        return True
    return w == form + "E" or w == form + "S"


def match_cost(w, head):
    """(coût, niveau, texte fr) de la meilleure correspondance entre un mot de grille et un intitulé."""
    if grid_form(head) == w:
        return 100, 1, head
    best = None
    no_par = re.sub(r"\s*\([^)]*\)", "", head).strip()
    if no_par != head and grid_form(no_par) == w:
        best = (200, 2, no_par)
    for par in re.findall(r"\(([^)]*)\)", head):
        if grid_form(par) == w and (best is None or 300 < best[0]):
            best = (300, 3, par.strip())
    if best:
        return best
    for pos, seg in head_segments(head):
        f = grid_form(seg)
        if f == w:
            c = (400 + pos, 4, seg)
        elif inflected(w, f):
            c = (500 + pos, 5, w)
        elif " " not in seg and "-" not in seg and len(w) >= 5 and len(f) > len(w) and (f.startswith(w) or (len(w) >= 6 and f.endswith(w))):
            c = (600 + pos, 6, w)
        else:
            continue
        if best is None or c[0] < best[0]:
            best = c
    return best


def hungarian(cost):
    """Affectation de coût minimal (lignes ≤ colonnes). Renvoie col[i] pour chaque ligne i."""
    n, m = len(cost), len(cost[0])
    INF = float("inf")
    u, v, p, way = [0] * (n + 1), [0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [INF] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    res = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            res[p[j] - 1] = j - 1
    return res


def longest_common(a, b):
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            best = max(best, k)
    return best


def match_glossary(words, n, glossary, used, notes, ctx):
    """Associe chaque mot de la grille à une entrée du glossaire.

    1) entrées portant la pastille du chapitre : affectation optimale (algorithme hongrois)
       sur les niveaux 1 à 6 ; 2) mots restants : intitulé exact (niveaux 1 à 3) sous une autre
       pastille ; 3) mots et entrées du chapitre encore libres : rapprochement approximatif
       (sous-chaîne commune ≥ 5 lettres), signalé. Renvoie {mot: (index, texte fr, niveau)}.
    """
    cands = [gi for gi, g in enumerate(glossary) if n in g["chapters"]]
    edges = {}
    cost = []
    for w in words:
        row = []
        for gi in cands:
            mc = match_cost(w, glossary[gi]["head"])
            if mc:
                edges[(w, gi)] = mc
            row.append(mc[0] if mc else NO_EDGE)
        row += [UNMATCHED_COST] * len(words)
        cost.append(row)
    result = {}
    if cands:
        for wi, col in enumerate(hungarian(cost)):
            if 0 <= col < len(cands) and (words[wi], cands[col]) in edges:
                gi = cands[col]
                c, level, fr = edges[(words[wi], gi)]
                result[words[wi]] = (gi, fr, level)
    taken = {v[0] for v in result.values()}
    for w in words:
        if w in result:
            continue
        other = []
        for gi, g in enumerate(glossary):
            mc = match_cost(w, g["head"])
            if mc and mc[1] <= 3:
                other.append((mc[0], gi, mc))
        if other:
            _, gi, mc = min(other)
            result[w] = (gi, mc[2], mc[1])
            notes.add(f"{ctx} : {w} — pas d'entrée sous la pastille {n} ; définition reprise de « {glossary[gi]['head']} » (pastille {glossary[gi]['chapters']})")
    free = [gi for gi in cands if gi not in taken and gi not in {v[0] for v in result.values()}]
    for w in words:
        if w in result:
            continue
        scored = sorted(((longest_common(w, grid_form(glossary[gi]["head"])), gi) for gi in free), reverse=True)
        if scored and scored[0][0] >= 5 and (len(scored) == 1 or scored[1][0] < scored[0][0]):
            gi = scored[0][1]
            free.remove(gi)
            result[w] = (gi, w, 7)
            notes.add(f"{ctx} : {w} rapproché de « {glossary[gi]['head']} » (sous-chaîne commune, À VALIDER)")
    for w, (gi, fr, level) in result.items():
        used.add(gi)
    return result


def build_book(book: Book, out_root: Path, write: bool):
    notes = book.notes
    print(f"== {book.slug} ← {book.pdf.name}")
    legal = book.parse_legal()
    cover = book.parse_cover_stats()
    toc = book.parse_toc()
    glossary, announced = book.parse_glossary()
    if announced is not None and announced != len(glossary):
        notes.add(f"glossaire : {len(glossary)} entrées lues, {announced} annoncées")
    sols = book.parse_solutions()
    txt = txt_grids(book.txt) if book.txt and book.txt.exists() else None
    bib, bib_intro = book.parse_biblio()
    credits, credits_intro = book.parse_credits()

    used = set()
    chapters = []
    nums = book.chapter_numbers()
    if nums != list(range(1, len(nums) + 1)):
        notes.add(f"repères de chapitres non consécutifs : {nums}")
    for n in nums:
        ctx = f"chapitre {n}"
        raw = book.parse_chapter(n, toc.get(n))
        rows, words = raw["grid_rows"], raw["words"]
        if len(words) != 60:
            notes.add(f"{ctx} : {len(words)} mots dans « MOTS À TROUVER » (60 attendus)")
        if len(set(words)) != len(words):
            notes.add(f"{ctx} : mots en double dans la liste : {sorted({w for w in words if words.count(w) > 1})}")
        if txt is not None:
            if n not in txt:
                notes.add(f"{ctx} : grille absente du .txt de contre-vérification")
            else:
                trows, twords = txt[n]
                if trows != rows:
                    notes.add(f"{ctx} : la grille du .txt diffère de celle du PDF")
                if twords != words:
                    notes.add(f"{ctx} : la liste de mots du .txt diffère de celle du PDF")
        sol = sols.get(n)
        if sol is None:
            notes.add(f"{ctx} : grille absente des solutions")
        elif sol["rows"] != rows:
            notes.add(f"{ctx} : la grille des solutions (p. {sol['page']}) diffère de la grille du chapitre")
        if sol is not None and len(sol["boxes"]) != len(words):
            notes.add(f"{ctx} : {len(sol['boxes'])} bandes de surlignage dans les solutions pour {len(words)} mots")

        # placements
        placements, band_used = [], set()
        boxes = sol["boxes"] if sol else []
        for ti, w in enumerate(words):
            occ = find_all(rows, w)
            if not occ:
                notes.add(f"{ctx} : ERREUR BLOQUANTE — {w} introuvable dans la grille")
                continue
            chosen, from_sol = occ[0], False
            if w == w[::-1] and len(occ) > 1:
                notes.add(f"{ctx} : {w} est un palindrome — ses deux sens de lecture couvrent les mêmes cases (occurrences = {len(occ)})")
            if boxes:
                matched = [o for o in occ if occ_box(o, len(w)) in boxes]
                distinct = {tuple(sorted({(o[0] + o[2] * k, o[1] + o[3] * k) for k in range(len(w))})) for o in matched}
                if matched:
                    chosen, from_sol = matched[0], True
                    if len(distinct) > 1:
                        notes.add(f"{ctx} : {w} — plusieurs emplacements correspondent à une bande des solutions (premier retenu)")
                    band_used.add(occ_box(chosen, len(w)))
                else:
                    notes.add(f"{ctx} : {w} — aucun de ses {len(occ)} emplacements ne correspond à une bande des solutions (premier retenu)")
            r, c, dr, dc = chosen
            placements.append({"term_index": ti, "word": w, "row": r, "col": c, "d_row": dr, "d_col": dc,
                               "occurrences": len(occ), "solution_band": from_sol})
        if boxes:
            orphan = [b for b in boxes if b not in band_used]
            if orphan:
                notes.add(f"{ctx} : {len(orphan)} bande(s) des solutions sans mot correspondant : {orphan}")

        # termes + glossaire
        gm = match_glossary(words, n, glossary, used, notes, ctx)
        terms = []
        for w in words:
            if w in gm:
                gi, txt_fr, level = gm[w]
                t = {"word": w, "fr": txt_fr, "definition": {"fr": glossary[gi]["definition"]}}
                if txt_fr != glossary[gi]["head"]:
                    t["glossary_term"] = glossary[gi]["head"]
                    t["glossary_match"] = MATCH_LABELS[level]
            else:
                notes.add(f"{ctx} : définition manquante dans le glossaire pour {w}")
                t = {"word": w, "fr": w, "definition": {"fr": ""}}
            terms.append(t)

        title = raw["title"]
        chapters.append({
            "book": book.slug,
            "order": n,
            "slug": slugify(title),
            "title": {"fr": title},
            "description": {"fr": raw["subtitle"]},
            "summary": {"fr": raw["summary"]},
            "key_points": [],
            "pitfalls": [],
            "red_flags": [],
            "clinical_correlations": raw["clinical_correlations"],
            "figures": raw["figures"],
            "terms": terms,
            "grid": {"size": len(rows), "rows": rows},
            "placements": placements,
            "questions": raw["questions"],
            "vignettes": raw["vignettes"],
            "references": [],
            "source_pages": {"first": raw["pages"][0], "last": raw["pages"][1]},
        })

    unused = [g for gi, g in enumerate(glossary) if gi not in used]
    for g in unused:
        notes.add(f"glossaire : « {g['head']} » (chapitre {g['chapters']}) ne correspond à aucun mot de grille")

    total_words = sum(len(c["terms"]) for c in chapters)
    if cover.get("chapters") not in (None, len(chapters)):
        notes.add(f"couverture : {cover['chapters']} chapitres annoncés, {len(chapters)} lus")
    if cover.get("words") not in (None, total_words):
        notes.add(f"couverture : {cover['words']} mots cachés annoncés, {total_words} lus")
    if book.hy.log:
        unsure = [x for x in book.hy.log if x[2].startswith("incertain")]
        cut = [x for x in book.hy.log if x[2].startswith("coupure")]
        if cut:
            notes.add("traits d'union de fin de ligne retirés (coupure typographique) : " + "; ".join(f"{c[1]} ({c[0]})" for c in cut))
        if unsure:
            notes.add("traits d'union de fin de ligne conservés sans certitude : " + "; ".join(f"{c[1]} ({c[0]})" for c in unsure))
    if any(c["clinical_correlations"] for c in chapters):
        notes.add("les « Corrélations cliniques » en puces (sans vignette) sont dans le champ clinical_correlations de chaque chapitre")
    notes.add("non extraits : préface, annexes, présentation de la collection, fiches d'auto-évaluation, libellés internes des schémas")

    authors = [a.strip() for a in re.split(r"\s*&\s*|\s+et\s+", legal.get("authors", "")) if a.strip()]
    book_json = {
        "slug": book.slug,
        "title": {"fr": legal.get("title", "")},
        "authors": authors,
        "edition": legal.get("edition", ""),
        "year": legal.get("year"),
        "chapter_count": len(chapters),
        "word_count": total_words,
        "terms_per_chapter": 60,
        "glossary_entry_count": len(glossary),
        "bibliography_note": bib_intro,
        "bibliography": bib,
        "credits_note": credits_intro,
        "credits": credits,
        "source_pdf": book.pdf.name,
        "extraction": "tools/books/parse_marked_books.py (pdftotext -bbox-layout + pypdf) : texte recopié tel quel",
        "notes": notes.items,
    }

    if book.verbose:
        for r in book.review:
            print("   · " + r)
        for x in book.hy.log:
            print(f"   - trait d'union {x[1]} ({x[0]}) : {x[2]}")
    if write:
        out_dir = out_root / book.slug
        out_dir.mkdir(parents=True, exist_ok=True)
        for c in chapters:
            (out_dir / f"{c['order']:02d}-{c['slug']}.json").write_text(
                json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out_dir / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing = sum(1 for c in chapters for t in c["terms"] if not t["definition"]["fr"])
    multi = sum(1 for c in chapters for p in c["placements"] if p["occurrences"] > 1)
    print(f"   {len(chapters)} chapitres, {total_words} termes, {missing} définitions manquantes, "
          f"{multi} mots à plusieurs occurrences, {sum(len(c['questions']) for c in chapters)} questions, "
          f"{sum(len(c['vignettes']) for c in chapters)} vignettes, {len(glossary)} entrées de glossaire")
    return chapters, book_json


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", action="append", choices=sorted(DEFAULT_BOOKS), help="livre(s) par défaut à traiter")
    ap.add_argument("--pdf", type=Path, help="autre PDF balisé à traiter (avec --slug)")
    ap.add_argument("--slug", help="slug du livre pour --pdf")
    ap.add_argument("--txt", type=Path, help="texte pdftotext -layout pour contre-vérification (avec --pdf)")
    ap.add_argument("--out", type=Path, default=OUT_ROOT, help="dossier de sortie (défaut : content/books)")
    ap.add_argument("--dry-run", action="store_true", help="analyse sans écrire")
    ap.add_argument("--verbose", action="store_true", help="affiche les lignes écartées et les traits d'union")
    ns = ap.parse_args(argv)
    jobs = []
    if ns.pdf:
        if not ns.slug:
            ap.error("--slug est obligatoire avec --pdf")
        jobs.append((ns.slug, ns.pdf, ns.txt))
    else:
        for slug in ns.book or sorted(DEFAULT_BOOKS):
            pdf, txt = DEFAULT_BOOKS[slug]
            jobs.append((slug, UPLOADS / pdf, TXT_DIR / txt))
    for slug, pdf, txt in jobs:
        build_book(Book(slug, pdf, txt, ns.verbose), ns.out, not ns.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
