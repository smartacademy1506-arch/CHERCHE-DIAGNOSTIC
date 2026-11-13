#!/usr/bin/env python3
"""Extraction fidèle des livres « Cherche et Diagnostique » (format chapitre « expert »)
vers les fichiers JSON de content/books/<slug-livre>/.

Livres pris en charge (PDF à couche texte, sans repères de section) :
  - anatomie-organes          (21 chapitres, 60 mots par grille)
  - anatomie-vascularisation  (20 chapitres, 60 mots par grille)

Principe
--------
Le texte est lu avec `pdftotext -bbox-layout` (poppler) : chaque mot arrive avec ses
coordonnées. Les lignes sont reconstruites mot à mot (un écart horizontal < 1 pt entre
deux mots signifie qu'ils appartiennent au même mot typographique : changement de graisse
au milieu d'un mot, ponctuation collée). La géométrie sert ensuite à :
  - séparer les paragraphes (écart vertical anormal entre deux lignes) ;
  - recoller les lettrines (« L » + « a cavité… » → « La cavité… ») ;
  - lire la grille de lettres et la liste des 60 mots (colonnes lues de haut en bas) ;
  - lire le glossaire sur trois colonnes, puis les crédits des illustrations (tableau).

Le texte n'est ni reformulé ni corrigé. Seuls sont retirés les artefacts de mise en page
(numéros de page, en-têtes courants, lettres décoratives, coupures de ligne). Toute
anomalie détectée est consignée dans book.json → "notes" et affichée à l'écran.

Contrôles intégrés : la grille de chaque chapitre est comparée à la grille imprimée dans
les « Solutions des grilles » ; chaque mot est recherché dans les 8 directions.

Usage
-----
  python3 tools/books/parse_expert_books.py                 # écrit les deux livres
  python3 tools/books/parse_expert_books.py --book anatomie-organes
  python3 tools/books/parse_expert_books.py --dry-run       # analyse sans rien écrire
  python3 tools/books/parse_expert_books.py --compare A.pdf B.pdf
      # compare deux éditions (ex. Vascularisation 12 vs 20 chapitres), n'écrit rien

Dépendances : python3 (bibliothèque standard), pdftotext (poppler-utils).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import statistics
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UPLOADS = '/mnt/user-data/uploads'

BOOKS = {
    'anatomie-organes': {
        'pdf': os.path.join(UPLOADS, '01dcda8c-Cherche_et_Diagnostique_Anatomie_Organes.pdf'),
        # Règle de placement annoncée dans le livre : jamais de gauche à droite ni de haut en bas.
        'forbidden_dirs': [(0, 1), (1, 0)],
    },
    'anatomie-vascularisation': {
        'pdf': os.path.join(UPLOADS, '7ad9fa0e-Cherche_et_Diagnostique_Anatomie_Vascularisation.pdf'),
        'forbidden_dirs': [],
    },
}

DIRECTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
JOIN_GAP = 1.0          # pt : en dessous, deux « mots » pdftotext forment un seul mot
EXPECTED_WORDS = 60


# --------------------------------------------------------------------------- utilitaires

def grid_form(s: str) -> str:
    """Forme grille : majuscules, accents retirés, tout ce qui n'est pas A–Z retiré."""
    s = s.replace('œ', 'oe').replace('Œ', 'OE').replace('æ', 'ae').replace('Æ', 'AE').replace('ß', 'ss')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^A-Z]', '', s.upper())


def slugify(s: str) -> str:
    s = s.replace('œ', 'oe').replace('Œ', 'OE').replace('æ', 'ae').replace('Æ', 'AE')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def nospace(s: str) -> str:
    return re.sub(r'\s+', '', s)


def join_lines(lines: list[str]) -> str:
    """Recolle les lignes d'un paragraphe. Un trait d'union en fin de ligne est conservé
    et collé au mot suivant : dans ces livres, aucune coupure n'est typographique
    (vérifié : toutes sont des mots composés, ex. « hépato-|pancréatique »)."""
    out = ''
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if not out:
            out = ln
        elif out.endswith('-') and not out.endswith(' -') and not out.endswith('--'):
            out += ln
        else:
            out += ' ' + ln
    return out


# --------------------------------------------------------------------------- modèle de page

@dataclass
class Word:
    x0: float
    y0: float
    x1: float
    y1: float
    t: str

    @property
    def h(self) -> float:
        return self.y1 - self.y0


@dataclass
class Line:
    words: list
    block: int = -1

    @property
    def x0(self): return min(w.x0 for w in self.words)
    @property
    def x1(self): return max(w.x1 for w in self.words)
    @property
    def y0(self): return min(w.y0 for w in self.words)
    @property
    def y1(self): return max(w.y1 for w in self.words)
    @property
    def cy(self): return (self.y0 + self.y1) / 2
    @property
    def h(self): return max(w.h for w in self.words)

    @property
    def text(self) -> str:
        ws = sorted(self.words, key=lambda w: w.x0)
        out, prev = '', None
        for w in ws:
            if prev is not None and w.x0 - prev > JOIN_GAP:
                out += ' '
            out += w.t
            prev = w.x1
        return out


@dataclass
class Page:
    num: int
    width: float
    height: float
    lines: list = field(default_factory=list)

    def vlines(self, lines=None, tol=3.0) -> list:
        """Lignes visuelles : fusionne les lignes pdftotext de même hauteur (blocs voisins)."""
        src = sorted(lines if lines is not None else self.lines, key=lambda l: (l.cy, l.x0))
        groups: list[list] = []
        for ln in src:
            placed = False
            for g in reversed(groups[-4:]):
                gcy = statistics.mean(x.cy for x in g)
                if abs(gcy - ln.cy) <= tol and all(ln.x1 <= o.x0 + 0.5 or ln.x0 >= o.x1 - 0.5 for o in g):
                    g.append(ln)
                    placed = True
                    break
            if not placed:
                groups.append([ln])
        return [Line([w for l in g for w in l.words]) for g in groups]


def load_pdf(pdf: str) -> list:
    out = subprocess.run(['pdftotext', '-bbox-layout', pdf, '-'], capture_output=True, check=True).stdout
    h = out.decode('utf-8')
    pages = []
    for i, pm in enumerate(re.finditer(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', h, re.S)):
        page = Page(i + 1, float(pm.group(1)), float(pm.group(2)))
        for bi, bm in enumerate(re.finditer(r'<block [^>]*>(.*?)</block>', pm.group(3), re.S)):
            for lm in re.finditer(r'<line [^>]*>(.*?)</line>', bm.group(1), re.S):
                ws = [Word(float(a), float(b), float(c), float(d), html.unescape(t))
                      for a, b, c, d, t in re.findall(
                          r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>',
                          lm.group(1))]
                if ws:
                    page.lines.append(Line(ws, bi))
        pages.append(page)
    return pages


def is_page_number(ln: Line, page: Page) -> bool:
    return ln.y0 > page.height - 45 and re.fullmatch(r'\d{1,3}', ln.text.strip()) is not None


def is_running_header(ln: Line) -> bool:
    if ln.y0 > 65:
        return False
    t = nospace(ln.text)
    return t.startswith('CHAPITRE') or t.startswith('ANATOMIEHUMAINE')


def is_decorative(ln: Line) -> bool:
    """Lettres décoratives (couvertures, pages d'ouverture) : mots d'une ou deux capitales."""
    toks = ln.text.split()
    return bool(toks) and all(re.fullmatch(r'[A-ZÀ-ÖØ-ÞŒ]{1,2}', t) for t in toks)


def content_lines(page: Page) -> list:
    return [l for l in page.lines if not is_page_number(l, page) and not is_running_header(l)]


# --------------------------------------------------------------------------- table des matières

def parse_toc(pages: list) -> tuple[list, dict]:
    toc_page = next(p for p in pages[:8] if any(nospace(l.text).startswith('Tabledesmatières') for l in p.lines))
    chapters, back = [], {}
    for vl in toc_page.vlines():
        t = vl.text.strip()
        m = re.fullmatch(r'(\d{2})\s+(.+?)\s+(\d{1,3})\s+(\d{1,3})', t)
        if m:
            chapters.append({'order': int(m.group(1)), 'title': m.group(2).strip(),
                             'grid_page': int(m.group(3)), 'page': int(m.group(4))})
            continue
        m = re.fullmatch(r'(Préface|Glossaire médical|Annexe.*?|Solutions des grilles|La collection.*?|Bibliographie.*?)\s+(\d{1,3})', t)
        if m:
            key = m.group(1)
            back[key] = int(m.group(2))
    return chapters, back


def back_page(back: dict, prefix: str) -> int:
    for k, v in back.items():
        if k.startswith(prefix):
            return v
    raise KeyError(prefix)


# --------------------------------------------------------------------------- chapitres

SECTION_PATTERNS = [
    ('summary', re.compile(r'^Résumé théorique$')),
    ('vignettes', re.compile(r'^Corrélations cliniques — vignettes de type USMLE$')),
    ('grid', re.compile(r'^Exercice : Mots cachés$')),
    ('words', re.compile(r'^MOTSÀTROUVER')),           # testé sur le texte sans espaces
    ('questions', re.compile(r'^Questions médicales$')),
    ('pitfalls', re.compile(r'^!?\s*Pièges classiques à l\'examen$')),
    ('red_flags', re.compile(r'^!?\s*Drapeaux rouges', re.I)),
    ('key_points', re.compile(r'^(Signes clés|Perles|Points? (clés|essentiels)|À retenir)', re.I)),
    ('fiche', re.compile(r'^Fiche d\'évaluation — Chapitre \d+$')),
]


def section_of(ln: Line):
    t = ln.text.strip()
    for name, rx in SECTION_PATTERNS:
        if rx.search(nospace(t) if name == 'words' else t):
            return name
    return None


def split_paragraphs(lines: list, factor: float = 1.3) -> list[list]:
    """Sépare en paragraphes d'après l'interligne (écart vertical supérieur à la normale)."""
    if not lines:
        return []
    gaps = [b.y0 - a.y0 for a, b in zip(lines, lines[1:]) if 0 < b.y0 - a.y0 < 40]
    base = statistics.median(gaps) if gaps else 14.0
    paras, cur = [], [lines[0]]
    for a, b in zip(lines, lines[1:]):
        if b.y0 - a.y0 > base * factor or b.y0 < a.y0:   # b.y0 < a.y0 : changement de page
            paras.append(cur)
            cur = []
        cur.append(b)
    paras.append(cur)
    return paras


class Notes:
    def __init__(self):
        self.items: list[str] = []

    def add(self, msg: str):
        self.items.append(msg)
        print('  [note] ' + msg)


def parse_opening(page: Page, ch: dict, notes: Notes) -> tuple[str, list]:
    """Page d'ouverture : sous-titre (description) et figures (légende + source)."""
    lines = [l for l in content_lines(page) if not is_decorative(l)]
    lines.sort(key=lambda l: (l.y0, l.x0))
    fig_idx = [i for i, l in enumerate(lines) if re.match(r'^Figure \d+ — ', l.text)]
    top_limit = lines[fig_idx[0]].y0 if fig_idx else page.height
    # --- sous-titre : lignes alignées sur la marge du titre (x ≈ 113), sous l'en-tête
    head = [l for l in lines if l.y0 < top_limit and 108 <= l.x0 <= 118]
    head = [l for l in head if not nospace(l.text).startswith('CHAPITRE')]
    head = [l for l in head if not re.match(r'^\d+ mots cachés', l.text)]
    text = join_lines([l.text for l in head])
    title = ch['title']
    if text.startswith(title):
        desc = text[len(title):].strip()
    elif title not in ' '.join(l.text for l in lines if l.y0 < top_limit):
        desc = text
        notes.add(f"chapitre {ch['order']:02d} : titre de la table des matières introuvable sur la page d'ouverture")
    else:
        desc = text  # titre imprimé ailleurs (ligne du numéro de chapitre)
    # --- figures
    figures = []
    for k, i in enumerate(fig_idx):
        end = fig_idx[k + 1] if k + 1 < len(fig_idx) else len(lines)
        block = lines[i:end]
        src_i = next((j for j, l in enumerate(block) if l.text.startswith('Source :')), None)
        cap_lines = block[:src_i] if src_i is not None else block
        src_lines = block[src_i:] if src_i is not None else []
        m = re.match(r'^(Figure \d+) — (.*)$', cap_lines[0].text)
        caption = join_lines([m.group(2)] + [l.text for l in cap_lines[1:]])
        source = join_lines([l.text for l in src_lines])
        source = re.sub(r'^Source : ', '', source)
        figures.append({'label': m.group(1), 'caption': caption, 'source': source})
        if src_i is None:
            notes.add(f"chapitre {ch['order']:02d} : {m.group(1)} sans ligne « Source : »")
    if not figures:
        notes.add(f"chapitre {ch['order']:02d} : aucune figure trouvée sur la page d'ouverture")
    return desc, figures


def extract_grid_rows(vls: list) -> list[str]:
    rows = []
    for vl in vls:
        toks = vl.text.split()
        if toks and all(re.fullmatch(r'[A-Z]{1,3}', t) for t in toks):
            s = ''.join(toks)
            if len(s) >= 8:
                rows.append(s)
    return rows


def parse_word_list(vls: list) -> list[str]:
    """Liste « MOTS À TROUVER » : 4 colonnes, lues de haut en bas, colonne après colonne."""
    words = []
    for vl in vls:
        for w in vl.words:
            if re.fullmatch(r'[A-Z]{2,}', w.t):
                words.append(w)
    if not words:
        return []
    xs = sorted(set(round(w.x0) for w in words))
    starts = [xs[0]]
    for a, b in zip(xs, xs[1:]):
        if b - a > 40:
            starts.append(b)
    def col(w):
        return max(i for i, s in enumerate(starts) if round(w.x0) >= s - 0.5)
    words.sort(key=lambda w: (col(w), w.y0))
    return [w.t for w in words]


def parse_chapter(pages: list, ch: dict, end_page: int, notes: Notes) -> dict:
    o = ch['order']
    opening = pages[ch['page'] - 1]
    description, figures = parse_opening(opening, ch, notes)

    # Flux de lignes visuelles des pages suivantes, avec repérage des sections.
    stream = []   # (section, Line, page)
    cur = None
    dropcaps = []
    for pn in range(ch['page'] + 1, end_page + 1):
        page = pages[pn - 1]
        lines = content_lines(page)
        caps = [l for l in lines if len(l.words) == 1 and l.h > 25 and len(l.text) <= 2 and l.x0 < 60]
        for c in caps:
            dropcaps.append((pn, c))
        lines = [l for l in lines if l not in caps]
        for vl in page.vlines(lines):
            s = section_of(vl)
            if s:
                cur = s
                stream.append((s + ':heading', vl, pn))
                continue
            stream.append((cur, vl, pn))

    def sec(name):
        return [(vl, pn) for s, vl, pn in stream if s == name]

    unknown = [vl.text for s, vl, pn in stream if s is None]
    if unknown:
        notes.add(f"chapitre {o:02d} : lignes hors section ignorées : {unknown[:5]}")

    # --- résumé théorique
    summ = sec('summary')
    sum_lines = [vl for vl, pn in summ]
    # Lettrine : rattachée à la première ligne du paragraphe qu'elle ouvre.
    for pn, cap in dropcaps:
        target = min((vl for vl, p in summ if p == pn and vl.y0 >= cap.y0 - 3),
                     key=lambda vl: vl.y0, default=None)
        if target is None:
            notes.add(f"chapitre {o:02d} : lettrine « {cap.text} » sans ligne associée")
            continue
        # Lettrine collée au premier mot (écart < JOIN_GAP) : « L » + « a cavité » → « La cavité ».
        target.words.insert(0, Word(target.x0 - 0.5, target.y0, target.x0 - 0.1, target.y1, cap.text))
    paragraphs = []
    for para in split_paragraphs(sum_lines):
        txt = join_lines([l.text for l in para])
        # paragraphe coupé par un changement de page : on le recolle
        if paragraphs and not re.search(r'[.!?:»)]$', paragraphs[-1]) and txt[:1].islower():
            paragraphs[-1] = paragraphs[-1] + ' ' + txt
        else:
            paragraphs.append(txt)
    summary = '\n\n'.join(paragraphs)

    # --- vignettes
    vign = []
    curv = None
    mode = None
    for vl, pn in sec('vignettes'):
        t = vl.text.strip()
        m = re.match(r'^VIGNETTE (\d+)\s*(.*)$', t)
        if m:
            curv = {'n': int(m.group(1)), 'case': [m.group(2)], 'answer': []}
            vign.append(curv)
            mode = 'case'
            continue
        m = re.match(r'^Réponse — (.*)$', t)
        if m and curv is not None:
            mode = 'answer'
            curv['answer'].append(m.group(1))
            continue
        if curv is None:
            notes.add(f"chapitre {o:02d} : texte avant la première vignette : {t[:60]}")
            continue
        curv[mode].append(t)
    vignettes = []
    for k, v in enumerate(vign, 1):
        if v['n'] != k:
            notes.add(f"chapitre {o:02d} : numérotation des vignettes inattendue ({v['n']} au rang {k})")
        if not v['answer']:
            notes.add(f"chapitre {o:02d} : vignette {v['n']} sans « Réponse — »")
        vignettes.append({'case': {'fr': join_lines(v['case'])}, 'answer': {'fr': join_lines(v['answer'])}})

    # --- grille
    grid_lines = [vl for vl, pn in sec('grid')]
    rows = extract_grid_rows(grid_lines)
    other = [vl for vl in grid_lines if vl.text.replace(' ', '') not in rows and extract_grid_rows([vl]) == []]
    level = next((vl.text for vl in other if re.match(r'^niveau', vl.text, re.I)), '')
    instr = join_lines([vl.text for vl in other if not re.match(r'^niveau', vl.text, re.I)])
    size = len(rows)
    if size == 0:
        notes.add(f"chapitre {o:02d} : ERREUR grille introuvable")
    elif any(len(r) != size for r in rows):
        notes.add(f"chapitre {o:02d} : ERREUR grille non carrée ({size} lignes, longueurs {sorted(set(map(len, rows)))})")

    # --- mots à trouver
    word_vls = [vl for vl, pn in sec('words')]
    words = parse_word_list(word_vls)
    if len(words) != EXPECTED_WORDS:
        notes.add(f"chapitre {o:02d} : {len(words)} mots dans la liste (60 attendus)")
    if words != sorted(words):
        notes.add(f"chapitre {o:02d} : la liste lue colonne par colonne n'est pas alphabétique")

    # --- questions
    questions, curq = [], None
    for vl, pn in sec('questions'):
        toks = sorted(vl.words, key=lambda w: w.x0)
        if re.fullmatch(r'\d{1,2}', toks[0].t) and toks[0].x0 < 65:
            curq = [Line(toks[1:]).text]
            questions.append(curq)
        elif curq is not None:
            curq.append(vl.text)
        else:
            notes.add(f"chapitre {o:02d} : ligne de questions non numérotée : {vl.text[:60]}")
    questions = [{'fr': join_lines(q)} for q in questions]

    def numbered_items(name):
        items, curi = [], None
        for vl, pn in sec(name):
            t = vl.text.strip()
            m = re.match(r'^(\d+)\.\s+(.*)$', t)
            if m:
                curi = [m.group(2)]
                items.append(curi)
            elif curi is not None:
                curi.append(t)
            else:
                curi = [t]
                items.append(curi)
        return [{'fr': join_lines(i)} for i in items]

    pitfalls = numbered_items('pitfalls')
    red_flags = numbered_items('red_flags')
    key_points = numbered_items('key_points')

    return {
        'book': None, 'order': o, 'slug': slugify(ch['title']),
        'title': {'fr': ch['title']}, 'description': {'fr': description},
        'summary': {'fr': summary},
        'key_points': key_points, 'pitfalls': pitfalls, 'red_flags': red_flags,
        'figures': figures,
        '_words': words,
        'grid': {'size': size, 'rows': rows, 'level': level, 'instructions': instr},
        'questions': questions, 'vignettes': vignettes, 'references': [],
    }


# --------------------------------------------------------------------------- glossaire

_ENTRY_RX = re.compile(r'^(?P<head>.+?) (?P<ch>\d{1,2}(?:\s*(?:,|et)\s*\d{1,2})*) —(?: (?P<rest>.*))?$')
_LOWER = re.compile(r'[a-zàâäçéèêëîïôöùûüÿœæ]')
_UPPER = re.compile(r'[A-ZÀ-ÖØ-ÞŒÆ]')


def _head_ok(head: str) -> bool:
    """Intitulé du glossaire : en capitales ; tolère « 99m », « IgA », « pH »."""
    if len(_UPPER.findall(head)) < 2:
        return False
    for tok in head.split():
        lo, up = len(_LOWER.findall(tok)), len(_UPPER.findall(tok))
        if lo and not (re.fullmatch(r'\d+[a-z]{1,3}', tok) or up >= lo):
            return False
    return True


class _EntryRx:
    @staticmethod
    def match(t: str):
        m = _ENTRY_RX.match(t)
        return m if m and _head_ok(m.group('head')) else None


ENTRY_RX = _EntryRx()


def parse_glossary(pages: list, first: int, last: int, chapter_titles: list, notes: Notes) -> list:
    entries = []
    stream = []
    for pn in range(first, last + 1):
        page = pages[pn - 1]
        lines = content_lines(page)
        if pn == first:
            legend = [l for l in lines if any(t in l.text for t in chapter_titles)]
            cut = max(l.y1 for l in legend) if legend else 0
            lines = [l for l in lines if l.y0 > cut]
        lines = [l for l in lines if not re.fullmatch(r'[A-Z]', l.text.strip())]
        # colonnes : regroupement des abscisses de départ
        xs = sorted(round(l.x0) for l in lines)
        starts = []
        for x in xs:
            if not starts or x - starts[-1][-1] > 60:
                starts.append([x])
            else:
                starts[-1].append(x)
        bounds = [min(s) for s in starts]
        def col(l):
            return max(i for i, b in enumerate(bounds) if round(l.x0) >= b - 1)
        for l in sorted(lines, key=lambda l: (col(l), l.y0)):
            stream.append((pn, l.text.strip()))
    cur = None
    skip = False
    rejoined = []
    lower = re.compile(r'[a-zàâäçéèêëîïôöùûüÿœæ]')
    for i, (pn, t) in enumerate(stream):
        if skip:
            skip = False
            continue
        m = ENTRY_RX.match(t)
        if not (m and len(re.sub(r'[^A-ZÀ-ÖØ-ÞŒÆ]', '', m.group('head'))) >= 2):
            m = None
        # Intitulé coupé : « INTITULÉ 18 » / « — définition », ou « INTITULÉ » / « 18 — définition »,
        # ou « DÉBUT D'INTITULÉ » / « FIN 8 — définition ». On ne recolle qu'après une définition close.
        nxt = stream[i + 1][1] if i + 1 < len(stream) else ''
        prev_closed = cur is None or re.search(r'[.!?)»]$', join_lines(cur['lines'])) is not None
        if m is None and not lower.search(t) and len(t) > 2 and prev_closed and nxt:
            m2 = ENTRY_RX.match(join_lines([t, nxt]))
            if m2 and len(m2.group('head')) >= len(t.rstrip(' 0123456789')) - 1:
                rejoined.append(m2.group('head').strip())
                m = m2
                skip = True
        if m:
            chs = [int(x) for x in re.findall(r'\d{1,2}', m.group('ch'))]
            cur = {'head': m.group('head').strip(), 'chapters': chs, 'lines': [m.group('rest') or ''], 'page': pn}
            entries.append(cur)
            continue
        if cur is None:
            notes.add(f"glossaire p.{pn} : texte avant la première entrée ignoré : {t[:60]}")
            continue
        cur['lines'].append(t)
    if rejoined:
        notes.add(f"glossaire : {len(rejoined)} intitulé(s) imprimé(s) sur deux lignes, recollé(s) : "
                  + ' ; '.join(rejoined))
    out = []
    for e in entries:
        d = join_lines(e['lines'])
        out.append({'head': e['head'], 'chapters': e['chapters'], 'definition': d, 'page': e['page']})
        if re.search(r' \d{1,2} — ', d):
            notes.add(f"glossaire : ERREUR entrée possiblement fusionnée dans « {e['head']} » : {d[:120]}")
    return out


# --------------------------------------------------------------------------- solutions

def parse_solutions(pages: list, first: int, last: int) -> dict:
    """Grilles imprimées dans « Solutions des grilles » → {chapitre: [lignes]}."""
    result = {}
    for pn in range(first, last + 1):
        page = pages[pn - 1]
        lines = content_lines(page)
        third = page.width / 3
        for c in range(3):
            cl = [l for l in lines if min(2, int(((l.x0 + l.x1) / 2) // third)) == c]
            heads = [(l.y0, int(m.group(1))) for l in cl for m in [re.match(r'^(\d{2}) — ', l.text)] if m]
            heads.sort()
            for k, (hy, num) in enumerate(heads):
                ny = heads[k + 1][0] if k + 1 < len(heads) else page.height
                rows_l = [l for l in cl if hy < l.y0 < ny]
                rows = extract_grid_rows(page.vlines(rows_l, tol=2.0))
                result[num] = rows
    return result


# --------------------------------------------------------------------------- bibliographie

def parse_bibliography(pages: list, first: int, notes: Notes) -> tuple[list, str, list, str]:
    bib, credits = [], []
    bib_intro, credits_intro = '', ''
    lines = []
    for pn in range(first, len(pages) + 1):
        page = pages[pn - 1]
        ls = content_lines(page)
        if pn > first and not any(re.fullmatch(r'Figure \d+', l.text) for l in ls):
            break
        lines += [(pn, l) for l in sorted(ls, key=lambda l: (l.y0, l.x0))]
    # 1) ouvrages
    i = 0
    while i < len(lines) and not lines[i][1].text.startswith('Bibliographie'):
        i += 1
    i += 1
    if i < len(lines):
        bib_intro = lines[i][1].text
        i += 1
    curb = None
    while i < len(lines) and lines[i][1].text != 'Crédits des illustrations':
        t = lines[i][1].text
        m = re.match(r'^(\d+)\. (.*)$', t)
        if m:
            curb = [m.group(2)]
            bib.append(curb)
        elif curb is not None:
            curb.append(t)
        i += 1
    bib = [{'citation': join_lines(b), 'url': ''} for b in bib]
    i += 1
    # 2) crédits : paragraphe d'introduction puis tableau Figure | Sujet | Source
    intro = []
    while i < len(lines) and lines[i][1].text != 'Figure':
        intro.append(lines[i][1].text)
        i += 1
    credits_intro = join_lines(intro)
    hdr = [l for pn, l in lines[i:i + 3]]
    cols = {l.text: l.x0 for l in hdr}
    xs = [cols.get('Figure', 50), cols.get('Sujet', 95), cols.get('Source', 330)]
    i += 3
    rows = []
    for pn, l in lines[i:]:
        c = 2 if l.x0 >= xs[2] - 2 else (1 if l.x0 >= xs[1] - 2 else 0)
        if c == 0 and re.fullmatch(r'Figure \d+', l.text):
            rows.append({'figure': l.text, 'subject': [], 'source': []})
        elif c == 0:
            notes.add(f"crédits p.{pn} : ligne inattendue en colonne « Figure » : {l.text[:60]}")
        elif rows:
            rows[-1]['subject' if c == 1 else 'source'].append(l.text)
    for r in rows:
        credits.append({'figure': r['figure'], 'subject': join_lines(r['subject']), 'source': join_lines(r['source'])})
    return bib, bib_intro, credits, credits_intro


# --------------------------------------------------------------------------- recherche dans la grille

def find_word(rows: list[str], word: str) -> list[dict]:
    n = len(rows)
    found = []
    for r in range(n):
        for c in range(len(rows[r])):
            if rows[r][c] != word[0]:
                continue
            for dr, dc in DIRECTIONS:
                rr, cc, ok, cells = r, c, True, []
                for ch in word:
                    if not (0 <= rr < n and 0 <= cc < len(rows[rr])) or rows[rr][cc] != ch:
                        ok = False
                        break
                    cells.append((rr, cc))
                    rr += dr
                    cc += dc
                if ok:
                    # Chaque lecture (case de départ + direction) compte : un palindrome se lit
                    # deux fois sur les mêmes cases (convention partagée avec check_books.py).
                    found.append({'row': r, 'col': c, 'd_row': dr, 'd_col': dc, '_cells': frozenset(cells)})
    return found


# --------------------------------------------------------------------------- appariement glossaire

MATCH_KINDS = {0: 'exact', 1: 'mot-complet', 2: 'inclus', 3: 'intitule-inclus', 4: 'radical', 5: 'cite-dans-definition'}
NO_EDGE = 10 ** 6


def head_parts(head: str) -> list[str]:
    return [g for g in (grid_form(p) for p in re.split(r"[\s'’()/,-]+", head)) if g]


def match_cost(w: str, e: dict):
    """Coût d'appariement mot ↔ entrée du glossaire (même pastille). None = pas de lien."""
    tier = match_tier(w, e)
    if tier is None:
        return None
    g = grid_form(e['head'])
    return TIER_WEIGHT[tier] + abs(len(g) - len(w)) / 1000.0


TIER_WEIGHT = [0, 1, 2, 4, 8, 16]


def match_tier(w: str, e: dict):
    """0 identique ; 1 mot(s) complet(s) de l'intitulé ; 2 inclus dans l'intitulé ;
    3 intitulé (ou un de ses mots de 5 lettres et plus) inclus dans le mot ;
    4 radical commun avec un mot de l'intitulé ; 5 mot cité dans la définition."""
    g = grid_form(e['head'])
    parts = head_parts(e['head'])
    if g == w:
        return 0
    if any(''.join(parts[a:b]) == w for a in range(len(parts)) for b in range(a + 1, len(parts) + 1)):
        return 1
    if w in g:
        return 2
    if (len(g) >= 4 and g in w) or any(len(p) >= 5 and p in w for p in parts):
        return 3
    for p in parts:
        k = 0
        while k < min(len(p), len(w)) and p[k] == w[k]:
            k += 1
        m = min(len(p), len(w))
        if (k >= 4 and k >= 0.6 * m) or (k >= 3 and k >= 0.75 * m):
            return 4
    toks = {grid_form(t) for t in re.split(r"[\s'’()/,;:.«»-]+", e['definition'])}
    if w in toks:
        return 5
    return None


def hungarian(cost: list[list[float]]) -> list[int]:
    """Affectation de coût minimal (matrice carrée). Renvoie col[i] pour chaque ligne i."""
    n = len(cost)
    INF = float('inf')
    u, v, p, way = [0.0] * (n + 1), [0.0] * (n + 1), [0] * (n + 1), [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(n + 1):
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
    for j in range(1, n + 1):
        if p[j]:
            res[p[j] - 1] = j - 1
    return res


def match_terms(order: int, words: list[str], glossary: list, used: set, notes: Notes) -> list[dict]:
    """Rattache chaque mot de la grille à une entrée du glossaire portant la pastille du chapitre.

    Le glossaire contient exactement une entrée par mot caché ; l'intitulé est souvent plus long
    que le mot (« AMYLASE SALIVAIRE » pour AMYLASE) ou en est une variante (« URÈTRE SPONGIEUX »
    pour SPONGIEUSE). L'appariement global (coût minimal) préfère, dans l'ordre : forme grille
    identique, mot complet de l'intitulé, inclusion, radical commun, mot cité dans la définition.
    Aucun appariement n'est forcé en l'absence de lien textuel."""
    chap = [k for k, e in enumerate(glossary) if order in e['chapters']]
    n = max(len(words), len(chap))
    cost = [[NO_EDGE] * n for _ in range(n)]
    for i, w in enumerate(words):
        for j, k in enumerate(chap):
            c = match_cost(w, glossary[k])
            if c is not None:
                cost[i][j] = c
    assign = hungarian(cost) if n else []
    pairs = {}
    for i, j in enumerate(assign):
        if i < len(words) and 0 <= j < len(chap) and cost[i][j] < NO_EDGE:
            pairs[i] = (chap[j], match_tier(words[i], glossary[chap[j]]))
    # Mot sans entrée sous sa pastille : entrée de même forme grille sous une autre pastille.
    for i, w in enumerate(words):
        if i not in pairs:
            cands = [k for k, e in enumerate(glossary) if grid_form(e['head']) == w and k not in used]
            if cands:
                pairs[i] = (cands[0], 0)
                notes.add(f"chapitre {order:02d} : {w} défini sous la pastille {glossary[cands[0]]['chapters']}")
    terms, approx = [], []
    for i, w in enumerate(words):
        if i in pairs:
            k, c = pairs[i]
            e = glossary[k]
            used.add(k)
            kind = MATCH_KINDS[c]
            fr = e['head'] if grid_form(e['head']) == w else w
            terms.append({'word': w, 'fr': fr, 'definition': {'fr': e['definition']},
                          'glossary_term': e['head'], 'glossary_match': kind})
            if c >= 4:
                approx.append(f"{w} ← {e['head']} ({kind})")
        else:
            terms.append({'word': w, 'fr': w, 'definition': {'fr': ''}, 'glossary_term': '', 'glossary_match': 'absent'})
    # Mots restés sans définition : on cite, sans les rattacher, les entrées libres de la même pastille.
    left_now = [glossary[k]['head'] for k in chap if k not in used]
    for t in terms:
        if not t['glossary_term']:
            t['glossary_candidates'] = left_now
    if approx:
        notes.add(f"chapitre {order:02d} : appariement approximatif mot ← entrée du glossaire, à valider : "
                  + ' ; '.join(approx))
    missing = [t['word'] for t in terms if not t['glossary_term']]
    left = [glossary[k]['head'] for k in chap if k not in used]
    if missing:
        notes.add(f"chapitre {order:02d} : DÉFINITION MANQUANTE (laissée vide) pour {missing} ; "
                  f"entrées de la pastille {order} restées libres : {left}")
    elif left:
        notes.add(f"chapitre {order:02d} : entrées du glossaire (pastille {order}) non rattachées : {left}")
    return terms


# --------------------------------------------------------------------------- livre

def parse_legal(pages: list) -> dict:
    page = next(p for p in pages[:4] if any(l.text.startswith('Informations légales') for l in p.lines))
    vls = page.vlines(content_lines(page))
    info = {}
    for vl in sorted(vls, key=lambda l: l.y0):
        t = vl.text.strip()
        m = re.match(r'^(Titre|Auteurs|Contacts|Prix|Lieu d\'impression)\s+(.*)$', t)
        if m:
            info[m.group(1)] = m.group(2)
            continue
        m = re.search(r'© (\d{4})', t)
        if m:
            info['year'] = int(m.group(1))
    # « Édition » : le libellé est centré verticalement sur un texte de deux lignes
    lab = next((l for l in vls if l.text.strip() == 'Édition'), None)
    if lab is not None:
        near = [l for l in vls if abs(l.cy - lab.cy) < 14 and l is not lab and l.x0 > lab.x1]
        info['Édition'] = join_lines([l.text for l in sorted(near, key=lambda l: l.y0)])
    return info


def parse_book(slug: str, pdf: str, notes: Notes, forbidden_dirs=()) -> tuple[dict, list]:
    pages = load_pdf(pdf)
    toc, back = parse_toc(pages)
    if not toc:
        raise SystemExit('table des matières introuvable')
    gloss_first = back_page(back, 'Glossaire')
    annex_first = back_page(back, 'Annexe')
    sol_first = back_page(back, 'Solutions')
    coll_first = back_page(back, 'La collection')
    bib_first = back_page(back, 'Bibliographie')
    titles = [c['title'] for c in toc]
    glossary = parse_glossary(pages, gloss_first, annex_first - 1, titles, notes)
    solutions = parse_solutions(pages, sol_first, coll_first - 1)
    chapters = []
    used = set()
    palindromes = []
    for k, ch in enumerate(toc):
        end = toc[k + 1]['page'] - 1 if k + 1 < len(toc) else gloss_first - 1
        if ch['grid_page'] != ch['page'] + 2:
            notes.add(f"chapitre {ch['order']:02d} : page de grille {ch['grid_page']} inattendue")
        c = parse_chapter(pages, ch, end, notes)
        c['book'] = slug
        words = c.pop('_words')
        rows = c['grid']['rows']
        # contrôle croisé avec les solutions
        sol = solutions.get(ch['order'])
        if sol is None:
            notes.add(f"chapitre {ch['order']:02d} : grille absente des solutions")
        elif sol != rows:
            diff = [i for i, (a, b) in enumerate(zip(rows, sol)) if a != b]
            notes.add(f"chapitre {ch['order']:02d} : ERREUR la grille diffère de celle des solutions (lignes {diff}, "
                      f"{len(rows)} vs {len(sol)} lignes)")
        c['terms'] = match_terms(ch['order'], words, glossary, used, notes)
        placements = []
        for ti, w in enumerate(words):
            occ = find_word(rows, w)
            if not occ:
                notes.add(f"chapitre {ch['order']:02d} : ERREUR mot introuvable dans la grille : {w}")
                continue
            physical = len({p['_cells'] for p in occ})
            if physical < len(occ):
                palindromes.append((ch['order'], w, len(occ), physical))
            pref = [p for p in occ if (p['d_row'], p['d_col']) not in forbidden_dirs]
            if not pref:
                pref = occ
                notes.add(f"chapitre {ch['order']:02d} : {w} n'est placé que dans une direction exclue par la règle "
                          f"annoncée du livre (d_row={occ[0]['d_row']}, d_col={occ[0]['d_col']}) : "
                          f"contenu imprimé conservé tel quel")
            p = {k2: v for k2, v in pref[0].items() if not k2.startswith('_')}
            placements.append({'term_index': ti, 'word': w, **p, 'occurrences': len(occ)})
        c['placements'] = placements
        # ordre des clés conforme au schéma
        chapters.append({k2: c[k2] for k2 in ['book', 'order', 'slug', 'title', 'description', 'summary',
                                              'key_points', 'pitfalls', 'red_flags', 'figures', 'terms', 'grid',
                                              'placements', 'questions', 'vignettes', 'references']})
    if palindromes:
        notes.add("Palindromes : lus dans les deux sens sur les mêmes cases, ils comptent 2 occurrences "
                  "(convention de check_books.py) pour un seul emplacement réel : "
                  + ' ; '.join(f'{o:02d} {w}' for o, w, n, ph in palindromes if ph == 1))
    if not any(c['pitfalls'] for c in chapters):
        notes.add("Ce livre ne comporte pas de section « Pièges classiques » : pitfalls est vide dans chaque chapitre.")
    unused = [e for k, e in enumerate(glossary) if k not in used]
    if unused:
        notes.add(f"glossaire : {len(unused)} entrée(s) non rattachée(s) : "
                  f"{[(e['head'], e['chapters']) for e in unused][:20]}")
    legal = parse_legal(pages)
    bib, bib_intro, credits, credits_intro = parse_bibliography(pages, bib_first, notes)
    authors = [a.strip() for a in legal.get('Auteurs', '').split('&') if a.strip()]
    book = {
        'slug': slug,
        'title': {'fr': legal.get('Titre', '')},
        'authors': authors,
        'edition': legal.get('Édition', ''),
        'year': legal.get('year'),
        'chapter_count': len(chapters),
        'word_count': sum(len(c['terms']) for c in chapters),
        'bibliography_intro': bib_intro,
        'bibliography': bib,
        'credits_intro': credits_intro,
        'credits': credits,
        'source_pdf': os.path.basename(pdf),
        'page_count': len(pages),
        'glossary_entry_count': len(glossary),
        'notes': [],
    }
    return book, chapters, {'pages': pages, 'toc': toc, 'glossary': glossary, 'back': back}


def summarize(slug, book, chapters):
    terms = sum(len(c['terms']) for c in chapters)
    missing = sum(1 for c in chapters for t in c['terms'] if not t['definition']['fr'])
    multi = [(c['order'], p['word'], p['occurrences']) for c in chapters for p in c['placements'] if p['occurrences'] > 1]
    fallback = sum(1 for c in chapters for t in c['terms'] if t['fr'] == t['word'] and t['glossary_term']
                   and grid_form(t['glossary_term']) != t['word'])
    print(f"\n== {slug} : {len(chapters)} chapitres, {terms} termes, {missing} définition(s) manquante(s), "
          f"{sum(len(c['vignettes']) for c in chapters)} vignettes, {sum(len(c['questions']) for c in chapters)} questions, "
          f"{sum(len(c['pitfalls']) for c in chapters)} pièges, {len(multi)} mot(s) à plusieurs occurrences, "
          f"{fallback} terme(s) dont l'intitulé du glossaire est plus long que le mot")
    return multi


def write_book(slug, book, chapters, notes: Notes):
    out_dir = os.path.join(REPO, 'content', 'books', slug)
    os.makedirs(out_dir, exist_ok=True)
    for c in chapters:
        fn = os.path.join(out_dir, f"{c['order']:02d}-{c['slug']}.json")
        with open(fn, 'w', encoding='utf-8') as f:
            json.dump(c, f, ensure_ascii=False, indent=2)
            f.write('\n')
    book['notes'] = notes.items
    with open(os.path.join(out_dir, 'book.json'), 'w', encoding='utf-8') as f:
        json.dump(book, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f"  écrit : {out_dir} ({len(chapters)} chapitres + book.json)")


STANDING_NOTES = [
    "Extraction automatique par tools/books/parse_expert_books.py (pdftotext -bbox-layout) : texte recopié tel quel, "
    "seuls les artefacts de mise en page ont été retirés (numéros de page, en-têtes courants, lettres décoratives, "
    "coupures de ligne). Tous les traits d'union de fin de ligne sont des mots composés et ont été conservés.",
    "Les chapitres ne comportent ni section « drapeaux rouges » ni « points clés » : key_points et red_flags sont vides.",
    "Les chapitres n'ont pas de références propres : la bibliographie et les crédits sont dans book.json ; "
    "references est vide dans chaque chapitre. Les sources des planches sont dans figures[].source.",
    "Non importés : fiche d'évaluation (formulaire à remplir), annexe (tableaux), page « La collection », "
    "pages de couverture et préface. Les « Solutions des grilles » ont servi uniquement au contrôle des grilles.",
    "terms[].fr reprend l'intitulé du glossaire quand sa forme grille est identique au mot ; sinon le mot imprimé. "
    "terms[].glossary_term donne toujours l'intitulé exact de l'entrée du glossaire dont provient la définition.",
    "placements : position (ligne, colonne, direction) trouvée par recherche dans la grille ; quand un mot a plusieurs "
    "emplacements (occurrences > 1), le premier compatible avec la règle de placement du livre est retenu.",
]


def compare_books(pdf_a, pdf_b):
    """Compare deux éditions : signale tout contenu de A absent de B. N'écrit rien."""
    na, nb = Notes(), Notes()
    print(f'Analyse de {pdf_a}')
    _, ca, xa = parse_book('a', pdf_a, na)
    print(f'Analyse de {pdf_b}')
    _, cb, xb = parse_book('b', pdf_b, nb)
    by_title = {c['title']['fr']: c for c in cb}
    print('\n==== Comparaison chapitre par chapitre (A → B)')
    diffs = 0
    for c in ca:
        t = c['title']['fr']
        d = by_title.get(t)
        if d is None:
            print(f'  A{c["order"]:02d} « {t} » : ABSENT de B')
            diffs += 1
            continue
        fields = []
        for key in ['description', 'summary']:
            if c[key] != d[key]:
                fields.append(key)
        for key in ['figures', 'vignettes', 'questions', 'pitfalls', 'grid']:
            if c[key] != d[key]:
                fields.append(key)
        if [x['word'] for x in c['terms']] != [x['word'] for x in d['terms']]:
            fields.append('liste de mots')
        if [x['definition'] for x in c['terms']] != [x['definition'] for x in d['terms']]:
            dd = [x['word'] for x, y in zip(c['terms'], d['terms']) if x['definition'] != y['definition']]
            fields.append(f'définitions ({dd})')
        status = 'identique' if not fields else 'DIFFÉRENCES : ' + ', '.join(fields)
        if fields:
            diffs += 1
        print(f'  A{c["order"]:02d} → B{d["order"]:02d} « {t} » : {status}')
    # glossaire : entrées de A absentes de B (intitulé + définition)
    gb = {(e['head'], e['definition']) for e in xb['glossary']}
    gb_heads = {e['head'] for e in xb['glossary']}
    miss = [e for e in xa['glossary'] if (e['head'], e['definition']) not in gb]
    print(f"\n==== Glossaire : {len(xa['glossary'])} entrées dans A, {len(xb['glossary'])} dans B ; "
          f"{len(miss)} entrée(s) de A absentes ou différentes dans B")
    for e in miss[:40]:
        print(f"  - {e['head']} ({'définition différente' if e['head'] in gb_heads else 'intitulé absent'}) : {e['definition'][:90]}")
    # pages de fin : annexe, bibliographie (texte brut comparé)
    def page_text(x, prefix, nxt):
        first = back_page(x['back'], prefix)
        last = back_page(x['back'], nxt) - 1
        return [l.text for p in x['pages'][first - 1:last] for l in content_lines(p)]
    for prefix, nxt in [('Annexe', 'Solutions')]:
        ta, tb = page_text(xa, prefix, nxt), set(page_text(xb, prefix, nxt))
        absent = [t for t in ta if t not in tb]
        print(f"\n==== {prefix} : {len(absent)} ligne(s) de A absentes de B" + (f' : {absent[:15]}' if absent else ''))
    bf_a = back_page(xa['back'], 'Bibliographie')
    bf_b = back_page(xb['back'], 'Bibliographie')
    ba = [l.text for p in xa['pages'][bf_a - 1:] for l in content_lines(p)]
    bb = set(l.text for p in xb['pages'][bf_b - 1:] for l in content_lines(p))
    absent = [t for t in ba if t not in bb]
    print(f"\n==== Bibliographie/crédits/4e de couverture : {len(absent)} ligne(s) de A absentes de B : {absent[:30]}")
    return diffs


def verify_against_pdftotext(slug: str) -> int:
    """Contrôle de fidélité indépendant : chaque texte écrit dans les JSON doit se retrouver,
    à l'identique (espaces et traits d'union ignorés), dans le texte que pdftotext extrait
    lui-même du PDF (pages du glossaire découpées en trois colonnes). Renvoie le nombre d'échecs."""
    pdf = BOOKS[slug]['pdf']
    out_dir = os.path.join(REPO, 'content', 'books', slug)
    pages = load_pdf(pdf)
    _, back = parse_toc(pages)
    g0, g1 = back_page(back, 'Glossaire'), back_page(back, 'Annexe') - 1

    def norm(s):
        return re.sub(r'[\s\-]+', '', s)

    def run(*opts):
        return subprocess.run(['pdftotext', *opts, pdf, '-'], capture_output=True, check=True).stdout.decode('utf-8')

    def gutters(page):
        # bandes verticales vides (aucun mot) : séparations des colonnes du glossaire
        cover = [0] * (int(page.width) + 2)
        for ln in page.lines:
            if ln.y0 < 250 and page.num == g0:   # légende des chapitres (pleine largeur)
                continue
            for w in ln.words:
                for x in range(int(w.x0), int(w.x1) + 1):
                    cover[x] += 1
        cuts = []
        for lo, hi in ((150, 300), (300, 450)):
            best, run_s, best_band = 0, None, None
            for x in range(lo, hi):
                if cover[x] == 0:
                    run_s = x if run_s is None else run_s
                    if x - run_s + 1 > best:
                        best, best_band = x - run_s + 1, (run_s, x)
                else:
                    run_s = None
            cuts.append((best_band[0] + best_band[1]) // 2 if best_band else int(lo + 50))
        return cuts

    chunks = []
    for p in pages:
        f = ['-f', str(p.num), '-l', str(p.num)]
        if g0 <= p.num <= g1:
            a, b = gutters(p)
            for x0, x1 in ((0, a), (a, b), (b, int(p.width) + 1)):
                crop = ['-x', str(x0), '-y', '0', '-W', str(x1 - x0), '-H', str(int(p.height) + 1)]
                chunks.append(run(*f, *crop))
        else:
            chunks.append(run(*f))
            chunks.append(run(*f, '-raw'))
    ref = norm(''.join(chunks))
    fails, total = 0, 0

    def check(where, text, strip_first=False):
        nonlocal fails, total
        if not text:
            return
        total += 1
        t = norm(text)
        if strip_first:
            t = t[1:]   # lettrine : imprimée à part, avant l'en-tête dans l'ordre de lecture
        if t not in ref:
            fails += 1
            print(f'  ÉCART {where} : {text[:110]}')

    for fn in sorted(os.listdir(out_dir)):
        if not re.match(r'\d{2}-.*\.json$', fn):
            continue
        c = json.load(open(os.path.join(out_dir, fn), encoding='utf-8'))
        o = c['order']
        for i, p in enumerate(c['summary']['fr'].split('\n\n')):
            check(f'{o:02d} résumé §{i + 1}', p, strip_first=(i == 0))
        check(f'{o:02d} description', c['description']['fr'])
        for k in ('questions', 'pitfalls', 'key_points', 'red_flags'):
            for i, q in enumerate(c[k]):
                check(f'{o:02d} {k}[{i}]', q['fr'])
        for i, v in enumerate(c['vignettes']):
            check(f'{o:02d} vignette {i + 1} (cas)', v['case']['fr'])
            check(f'{o:02d} vignette {i + 1} (réponse)', v['answer']['fr'])
        for f in c['figures']:
            check(f'{o:02d} {f["label"]} légende', f['caption'])
            check(f'{o:02d} {f["label"]} source', f['source'])
        for t in c['terms']:
            check(f'{o:02d} définition {t["word"]}', t['definition']['fr'])
            check(f'{o:02d} intitulé {t["word"]}', t['glossary_term'])
        check(f'{o:02d} grille', ''.join(c['grid']['rows']))
    b = json.load(open(os.path.join(out_dir, 'book.json'), encoding='utf-8'))
    for x in b['bibliography']:
        check('bibliographie', x['citation'])
    for x in b['credits']:
        check(f'crédits {x["figure"]} sujet', x['subject'])
        check(f'crédits {x["figure"]} source', x['source'])
    print(f'{slug} : {total} textes contrôlés, {fails} écart(s)')
    return fails


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--book', choices=sorted(BOOKS), action='append')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--compare', nargs=2, metavar=('PDF_A', 'PDF_B'))
    ap.add_argument('--verify', action='store_true',
                    help='contrôle les JSON déjà écrits contre le texte brut de pdftotext (n\'écrit rien)')
    args = ap.parse_args()
    if args.compare:
        compare_books(*args.compare)
        return
    if args.verify:
        bad = sum(verify_against_pdftotext(s) for s in (args.book or sorted(BOOKS)))
        sys.exit(1 if bad else 0)
    for slug in args.book or sorted(BOOKS):
        cfg = BOOKS[slug]
        print(f'== {slug} ← {cfg["pdf"]}')
        notes = Notes()
        for n in STANDING_NOTES:
            notes.items.append(n)
        book, chapters, _ = parse_book(slug, cfg['pdf'], notes, cfg['forbidden_dirs'])
        multi = summarize(slug, book, chapters)
        if multi:
            notes.items.append('Mots à plusieurs emplacements dans la grille (chapitre, mot, occurrences) : ' +
                               '; '.join(f'{o:02d} {w} ×{n}' for o, w, n in multi))
        if not args.dry_run:
            write_book(slug, book, chapters, notes)


if __name__ == '__main__':
    main()
