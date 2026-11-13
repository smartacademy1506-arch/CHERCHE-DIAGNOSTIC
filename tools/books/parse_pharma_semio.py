#!/usr/bin/env python3
"""Extraction fidèle des livres « Cherche et Diagnostique » : Pharmacologie et Sémiologie par systèmes.

Source : les PDF de l'auteur (couche texte). Le texte est lu mot par mot avec ses coordonnées
(`pdftotext -bbox`, poppler) ; la mise en page est reconstruite à partir des positions :
lignes (même ordonnée), colonnes (abscisses), paragraphes (ligne courte ou interligne plus grand).

Règles de fidélité appliquées (aucune reformulation) :
- seuls les artefacts de mise en page sont retirés : en-têtes courants, numéros de page, lettres
  décoratives des pages d'ouverture, libellés de schémas, fiche d'évaluation ;
- coupure de mot en fin de ligne : le trait d'union typographique U+2010 « ‐ » (inséré par la
  composition) est supprimé et le mot recollé ; le trait d'union U+002D « - » d'un mot composé est
  conservé et les deux parties recollées sans espace ;
- un espace est restitué entre deux mots lorsque l'écart horizontal dépasse 0,5 pt.

Usage :
  python3 tools/books/parse_pharma_semio.py                  # les deux livres -> content/books/
  python3 tools/books/parse_pharma_semio.py --book semiologie
  python3 tools/books/parse_pharma_semio.py --compare-semio  # compare les deux versions, n'écrit rien
  python3 tools/books/parse_pharma_semio.py --dry-run        # analyse sans écrire

Dépendances : python3 (bibliothèque standard), pdftotext (poppler).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO / "content" / "books"
UPLOADS = Path("/mnt/user-data/uploads")
PDF_PHARMA = UPLOADS / "8b9b4aa6-Cherche_et_Diagnostique_Pharmacologie.pdf"
PDF_SEMIO_1 = UPLOADS / "395f841a-Cherche_et_Diagnostique_Semiologie_par_Systemes-1.pdf"
PDF_SEMIO_2 = UPLOADS / "dc0bf5e7-Cherche_et_Diagnostique_Semiologie_par_Systemes-2.pdf"

SOFT_HYPHEN = "‐"  # trait d'union typographique de la composition
DIRECTIONS = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


# ---------------------------------------------------------------------------
# Lecture du PDF : mots avec coordonnées
# ---------------------------------------------------------------------------
class W:
    __slots__ = ("x0", "y0", "x1", "y1", "t")

    def __init__(self, x0, y0, x1, y1, t):
        self.x0, self.y0, self.x1, self.y1, self.t = x0, y0, x1, y1, t

    @property
    def h(self):
        return self.y1 - self.y0

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    def __repr__(self):
        return f"W({self.x0:.0f},{self.y0:.0f},h={self.h:.2f},{self.t!r})"


WORD_RE = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>')


def load_pdf(pdf: Path) -> list[list[W]]:
    raw = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, check=True).stdout
    text = raw.decode("utf-8")
    pages = []
    for pm in re.finditer(r"<page [^>]*>(.*?)</page>", text, re.S):
        pages.append([W(float(m[1]), float(m[2]), float(m[3]), float(m[4]), html.unescape(m[5]))
                      for m in WORD_RE.finditer(pm[1])])
    return pages


class Line:
    def __init__(self, words):
        self.w = sorted(words, key=lambda w: w.x0)

    @property
    def x0(self):
        return self.w[0].x0

    @property
    def x1(self):
        return max(w.x1 for w in self.w)

    @property
    def y0(self):
        return min(w.y0 for w in self.w)

    @property
    def y1(self):
        return max(w.y1 for w in self.w)

    @property
    def cy(self):
        return statistics.mean(w.cy for w in self.w)

    @property
    def h(self):
        return max(w.h for w in self.w)

    def text(self, th=0.5):
        return join_words(self.w, th)

    def spaced(self):
        return decode_spaced(self.w)

    def __repr__(self):
        return f"Line(y={self.y0:.1f},x={self.x0:.0f}-{self.x1:.0f}: {self.text()[:60]!r})"


def group_lines(words, tol=3.0) -> list[Line]:
    out: list[list[W]] = []
    for w in sorted(words, key=lambda w: (w.cy, w.x0)):
        if out and abs(w.cy - statistics.mean(x.cy for x in out[-1])) <= tol:
            out[-1].append(w)
        else:
            out.append([w])
    return [Line(ws) for ws in out]


def join_words(words, th=0.5) -> str:
    s = ""
    prev = None
    for w in sorted(words, key=lambda w: w.x0):
        if prev is not None and w.x0 - prev.x1 > th:
            s += " "
        s += w.t
        prev = w
    return s


def decode_spaced(words) -> str:
    """Texte composé en capitales espacées (C H A P I T R E) : espace seulement si l'écart > 2,2 pt."""
    s = join_words(words, 2.2)
    return re.sub(r"(\w)['’] (?=\w)", r"\1'", s)


def is_spaced(words) -> bool:
    ws = sorted(words, key=lambda w: w.x0)
    gaps = [b.x0 - a.x1 for a, b in zip(ws, ws[1:])]
    small = sum(1 for g in gaps if 0.8 <= g <= 1.7)
    return len(gaps) >= 3 and small >= 0.5 * len(gaps)


def join_lines(texts) -> str:
    out = ""
    for t in texts:
        t = t.strip()
        if not t:
            continue
        if not out:
            out = t
        elif out.endswith(SOFT_HYPHEN):
            out = out[:-1] + t
        elif out.endswith("-") and len(out) > 1 and out[-2].isalnum():
            out = out + t
        else:
            out = out + " " + t
    return out


def paragraphs(lines: list[Line], right=None, short_margin=15.0, gap_factor=1.4) -> list[str]:
    """Regroupe des lignes justifiées en paragraphes : nouvelle ligne de paragraphe après une ligne
    courte (ne touchant pas la marge droite) ou lorsque l'interligne dépasse 1,4 × l'interligne médian."""
    if not lines:
        return []
    right = right if right is not None else max(l.x1 for l in lines)
    pitches = [b.cy - a.cy for a, b in zip(lines, lines[1:])]
    base = statistics.median(pitches) if pitches else 0
    groups = [[lines[0]]]
    for prev, cur in zip(lines, lines[1:]):
        if prev.x1 < right - short_margin or (base and cur.cy - prev.cy > gap_factor * base):
            groups.append([cur])
        else:
            groups[-1].append(cur)
    return [join_lines([l.text() for l in g]) for g in groups]


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def grid_form(s: str) -> str:
    s = s.upper().replace("Œ", "OE").replace("Æ", "AE")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z]", "", s)


def slugify(s: str) -> str:
    s = s.replace("Œ", "OE").replace("œ", "oe").replace("Æ", "AE").replace("æ", "ae")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# ---------------------------------------------------------------------------
# Pages de structure
# ---------------------------------------------------------------------------
def body(ws, top=65.0, bottom=800.0):
    """Retire l'en-tête courant (y < 65) et le numéro de page (y > 800)."""
    return [w for w in ws if w.y0 >= top and w.y0 < bottom]


def parse_toc(ws):
    chapters, end_matter, parts = [], {}, []
    part = None
    for L in group_lines(body(ws, top=80)):
        toks = [w.t for w in L.w]
        if is_spaced(L.w):
            txt = L.spaced()
            if txt.startswith("PARTIE"):
                part = txt
                parts.append({"title": txt, "chapters": []})
            continue
        if re.fullmatch(r"\d{2}", toks[0]) and len(toks) >= 4 and toks[-1].isdigit() and toks[-2].isdigit():
            title_words = [w for w in L.w[1:-2]]
            ch = {"num": int(toks[0]), "title": join_words(title_words), "grid_page": int(toks[-2]),
                  "page": int(toks[-1]), "part": part}
            chapters.append(ch)
            if parts:
                parts[-1]["chapters"].append(ch["num"])
        elif toks[-1].isdigit():
            end_matter[join_words(L.w[:-1])] = int(toks[-1])
    return chapters, end_matter, parts


def parse_legal(ws):
    """Page « Informations légales » : tableau libellé/valeur puis paragraphes."""
    lines = group_lines(body(ws, top=90))
    fields, paras_lines, label_rows = {}, [], []
    last = next((k for k, L in enumerate(lines) if L.text().startswith("Lieu d'impression")), None)
    for k, L in enumerate(lines):
        lab = [w for w in L.w if w.x0 < 150]
        val = [w for w in L.w if w.x0 >= 150]
        if last is not None and k <= last and "©" not in L.text():
            label_rows.append((L, join_words(lab) if lab else "", join_words(val) if val else ""))
        else:
            paras_lines.append(L)
    # rattache chaque valeur au libellé le plus proche verticalement
    labels = [(L.cy, lab) for L, lab, _ in label_rows if lab]
    vals = defaultdict(list)
    for L, lab, val in label_rows:
        if not val:
            continue
        name = lab or min(labels, key=lambda x: abs(x[0] - L.cy))[1]
        vals[name].append(val)
    for k, v in vals.items():
        fields[k] = join_lines(v)
    copyright_line = paras_lines[0].text() if paras_lines and "©" in paras_lines[0].text() else ""
    rest = [L for L in paras_lines if "©" not in L.text()]
    return copyright_line, fields, paragraphs(rest)


# ---------------------------------------------------------------------------
# Chapitre : page d'ouverture
# ---------------------------------------------------------------------------
def is_decor(w: W) -> bool:
    return re.fullmatch(r"[A-Z]+", w.t) is not None and 14.8 <= w.h <= 16.2


def parse_opening(ws, warn):
    ws = [w for w in ws if not is_decor(w) and w.y0 < 800]
    lines = group_lines(ws)
    res = {"title_printed": "", "subtitle": "", "carte": "", "planche": "", "band_title": "", "band_items": [],
           "perle": ""}
    title_lines = [L for L in lines if L.y0 < 130 and 20 < L.h < 40 and not re.fullmatch(r"\d+", L.text())]
    res["title_printed"] = join_lines([L.text() for L in title_lines])
    termes = next((L for L in lines if "termes à débusquer" in L.text()), None)
    if not title_lines or termes is None:
        warn("page d'ouverture : titre ou ligne « termes à débusquer » introuvable")
        return res
    t_bottom = max(L.y1 for L in title_lines)
    sub = [L for L in lines if L.y0 >= t_bottom - 2 and L.y1 <= termes.y0 + 1 and L.h < 14.5
           and not is_spaced(L.w)]
    res["subtitle"] = join_lines([L.text() for L in sub])
    carte = next((L for L in lines if is_spaced(L.w) and L.spaced().startswith("CARTE ")), None)
    planche = next((L for L in lines if L.text(2.2).replace(" ", "").startswith("PLANCHE")), None)
    if carte is None or planche is None:
        warn("page d'ouverture : carte ou planche introuvable")
        return res
    # la ligne du libellé « CARTE … » peut contenir un mot d'un encadré voisin : on ne garde que les capitales espacées
    cw = [w for w in carte.w if w.h <= carte.w[0].h + 0.5 and abs(w.cy - carte.w[0].cy) < 1.5]
    ctxt = decode_spaced(cw)
    m = re.match(r"(CARTE [A-ZÉÈ]+)", ctxt)
    res["carte"] = m.group(1) if m else ctxt
    if m and ctxt != m.group(1):
        warn(f"libellé de carte accompagné d'un mot isolé de schéma ignoré : {ctxt!r}")
    # « PL A N CHE 12 Titre de la planche »
    num_i = next(i for i, w in enumerate(planche.w) if re.fullmatch(r"\d+", w.t))
    label = decode_spaced(planche.w[:num_i]).replace(" ", "")
    ptitle_words = planche.w[num_i + 1:]
    ptitle = join_words(ptitle_words)
    # titre de planche sur deux lignes ?
    th_ = statistics.median(w.h for w in ptitle_words) if ptitle_words else 0
    nxt = [L for L in lines if 0 < L.y0 - planche.y1 < 6 and abs(L.h - th_) < 0.3 and L.x0 >= ptitle_words[0].x0 - 2]
    if nxt:
        warn(f"titre de planche sur deux lignes : {ptitle!r} + {nxt[0].text()!r}")
        ptitle = join_lines([ptitle, nxt[0].text()])
    res["planche"] = f"{label} {planche.w[num_i].t} — {ptitle}"
    res["planche_num"] = int(planche.w[num_i].t)
    perle = next((L for L in lines if is_spaced(L.w) and L.spaced().startswith("PERLE ")), None)
    band = next((L for L in lines if L.y0 > planche.y1 and is_spaced(L.w) and L is not perle
                 and not L.spaced().startswith("PERLE")), None)
    if band is not None:
        res["band_title"] = band.spaced()
        stop = perle.y0 if perle is not None and perle.y0 > band.y0 else 800
        for L in lines:
            if band.y1 < L.cy < stop:
                # éléments séparés par de grands blancs
                cur = [L.w[0]]
                for a, b in zip(L.w, L.w[1:]):
                    if b.x0 - a.x1 > 9:
                        res["band_items"].append(join_words(cur))
                        cur = [b]
                    else:
                        cur.append(b)
                res["band_items"].append(join_words(cur))
    else:
        warn("bandeau (molécules/syndromes clés) introuvable")
    if perle is not None:
        res["perle_label"] = perle.spaced()
        plines = [L for L in lines if L.y0 > perle.y1 - 1 and L.cy > perle.cy + 3]
        res["perle"] = join_lines([L.text() for L in plines])
    else:
        warn("perle introuvable")
    return res


# ---------------------------------------------------------------------------
# Chapitre : résumé théorique et vignettes
# ---------------------------------------------------------------------------
def parse_summary_page(ws, warn):
    ws = body(ws)
    lines = group_lines([w for w in ws if w.h < 30])
    dropcaps = [w for w in ws if w.h >= 30 and re.fullmatch(r"[A-ZÀ-Ý]['’]?", w.t)]
    i_res = next((i for i, L in enumerate(lines) if L.text() == "Résumé théorique"), None)
    i_vig = next((i for i, L in enumerate(lines) if L.text().startswith("Corrélations cliniques")), None)
    if i_res is None or i_vig is None:
        warn("page du résumé : titres « Résumé théorique » / « Corrélations cliniques » introuvables")
        return "", []
    res_lines = lines[i_res + 1:i_vig]
    if dropcaps:
        dc = dropcaps[0]
        first = min(res_lines, key=lambda L: abs(L.cy - (dc.y0 + 8)))
        if first is not res_lines[0]:
            warn("lettrine : première ligne inattendue")
        first.w.insert(0, W(first.x0 - 0.1, first.w[0].y0, first.x0 - 0.05, first.w[0].y1, dc.t))
    else:
        warn("pas de lettrine dans le résumé")
    right = max(L.x1 for L in res_lines)
    summary = "\n\n".join(paragraphs(res_lines, right=right))
    vignettes = []
    mode = None
    for L in lines[i_vig + 1:]:
        t = L.text()
        m = re.match(r"VIGNETTE\s+(\d+)\s+(.*)$", t)
        if m:
            vignettes.append({"n": int(m.group(1)), "case": [L], "case_first": m.group(2), "answer": [],
                              "answer_first": None})
            mode = "case"
            continue
        m = re.match(r"Réponse\s+—\s+(.*)$", t)
        if m and vignettes:
            vignettes[-1]["answer"].append(L)
            vignettes[-1]["answer_first"] = m.group(1)
            mode = "answer"
            continue
        if not vignettes:
            warn(f"ligne avant la première vignette ignorée : {t!r}")
            continue
        vignettes[-1][mode].append(L)
    out = []
    for v in vignettes:
        case_txt = [v["case_first"]] + [L.text() for L in v["case"][1:]]
        ans_txt = ([v["answer_first"]] if v["answer_first"] is not None else []) + [L.text() for L in v["answer"][1:]]
        for key, ls in (("énoncé", v["case"]), ("réponse", v["answer"])):
            r = max(L.x1 for L in ls) if ls else 0
            if any(L.x1 < r - 15 for L in ls[:-1]):
                warn(f"vignette {v['n']} ({key}) : ligne courte au milieu du texte (paragraphe ?)")
        if not v["answer"]:
            warn(f"vignette {v['n']} sans réponse")
        out.append({"n": v["n"], "case": join_lines(case_txt), "answer": join_lines(ans_txt)})
    return summary, out


# ---------------------------------------------------------------------------
# Chapitre : grille et liste de mots
# ---------------------------------------------------------------------------
def split_letters(w: W):
    """Un « mot » de plusieurs lettres dans une grille = lettres accolées : on les répartit."""
    n = len(w.t)
    if n == 1:
        return [w]
    step = (w.x1 - w.x0) / n
    return [W(w.x0 + i * step, w.y0, w.x0 + (i + 1) * step, w.y1, c) for i, c in enumerate(w.t)]


def grid_from_letters(letters, warn, label):
    letters = [l for w in letters for l in split_letters(w)]
    rows = group_lines(letters, tol=3.0)
    grid = []
    for L in rows:
        grid.append("".join(w.t for w in L.w))
    # contrôle de l'alignement des colonnes
    if rows and all(len(L.w) == len(rows[0].w) for L in rows):
        for k in range(len(rows[0].w)):
            xs = [L.w[k].cx for L in rows]
            if max(xs) - min(xs) > 8:
                warn(f"{label} : colonne {k} mal alignée ({min(xs):.0f}–{max(xs):.0f})")
    return grid


def parse_grid_page(ws, warn):
    ws = body(ws)
    lines = group_lines(ws)
    i_mots = next((i for i, L in enumerate(lines) if is_spaced(L.w) and L.spaced().replace(" ", "").startswith("MOTSÀTROUVER")), None)
    if i_mots is None:
        warn("page de grille : « MOTS À TROUVER » introuvable")
        return [], []
    y_mots = lines[i_mots].y0
    heights = Counter(round(w.h, 1) for w in ws if re.fullmatch(r"[A-Z]+", w.t) and w.y0 < y_mots)
    gh = heights.most_common(1)[0][0]
    letters = [w for w in ws if re.fullmatch(r"[A-Z]+", w.t) and abs(w.h - gh) < 0.3 and w.y0 < y_mots]
    grid = grid_from_letters(letters, warn, "grille")
    # liste des mots : 4 colonnes, lecture colonne par colonne
    wl = [w for L in lines[i_mots + 1:] for w in L.w]
    xs = sorted(w.x0 for w in wl)
    cols = []
    for x in xs:
        if not cols or x - cols[-1][-1] > 15:
            cols.append([x])
        else:
            cols[-1].append(x)
    starts = [c[0] for c in cols]
    percol = defaultdict(list)
    for L in group_lines(wl):
        cells = defaultdict(list)
        for w in L.w:
            ci = max(i for i, s in enumerate(starts) if w.x0 >= s - 1)
            cells[ci].append(w)
        for ci, cw in cells.items():
            percol[ci].append(join_words(cw))
    words = [t for ci in sorted(percol) for t in percol[ci]]
    return grid, words


# ---------------------------------------------------------------------------
# Chapitre : questions, pièges, alertes
# ---------------------------------------------------------------------------
def parse_questions_page(ws, warn):
    ws = body(ws)
    lines = group_lines(ws)
    texts = [L.text() for L in lines]

    def idx(pred):
        return next((i for i, t in enumerate(texts) if pred(t)), None)

    i_q = idx(lambda t: t == "Questions médicales")
    i_p = idx(lambda t: "Pièges classiques à l'examen" in t)
    i_a = idx(lambda t: "Alertes de prescription" in t)
    i_f = idx(lambda t: t.startswith("Fiche d'évaluation"))
    if i_q is None or i_p is None or i_f is None:
        warn("page des questions : rubriques introuvables")
        return [], [], []
    questions = []
    qlines = lines[i_q + 1:i_p]
    # numéro centré verticalement sur une question de deux lignes : il forme une « ligne » à lui seul
    for k, L in enumerate(qlines):
        if len(L.w) == 1 and re.fullmatch(r"\d+", L.w[0].t) and L.w[0].x0 < 60 and k > 0:
            above = qlines[k - 1]
            if not re.fullmatch(r"\d+", above.w[0].t) and abs(above.cy - L.cy) < 9:
                above.w.insert(0, L.w[0])
                L.w = []
    qlines = [L for L in qlines if L.w]
    for L in qlines:
        if re.fullmatch(r"\d+", L.w[0].t) and L.w[0].x0 < 60:
            questions.append([join_words(L.w[1:])])
        elif questions:
            questions[-1].append(L.text())
        else:
            warn(f"ligne de questions ignorée : {L.text()!r}")
    questions = [join_lines(q) for q in questions]
    end_p = i_a if i_a is not None else i_f
    pitfalls = []
    for L in lines[i_p + 1:end_p]:
        if re.fullmatch(r"\d+\.", L.w[0].t):
            pitfalls.append([join_words(L.w[1:])])
        elif pitfalls:
            pitfalls[-1].append(L.text())
        else:
            warn(f"ligne de pièges ignorée : {L.text()!r}")
    pitfalls = [join_lines(p) for p in pitfalls]
    alerts = []
    if i_a is not None:
        alerts = parse_alert_table(lines[i_a + 1:i_f], warn)
    return questions, pitfalls, alerts


def parse_alert_table(lines, warn):
    head = lines[0]
    # colonnes : groupes de mots de l'en-tête séparés par de grands blancs
    groups = [[head.w[0]]]
    for a, b in zip(head.w, head.w[1:]):
        if b.x0 - a.x1 > 12:
            groups.append([b])
        else:
            groups[-1].append(b)
    names = [join_words(g) for g in groups]
    starts = [g[0].x0 for g in groups]
    if names != ["Situation à risque", "Risque", "Conduite à tenir"]:
        warn(f"en-tête d'alertes inattendu : {names}")
    rows = []
    prev = None
    pitches = [b.cy - a.cy for a, b in zip(lines[1:], lines[2:])]
    base = min(pitches) if pitches else 9
    for L in lines[1:]:
        cells = defaultdict(list)
        for w in L.w:
            ci = max(i for i, s in enumerate(starts) if w.x0 >= s - 3)
            cells[ci].append(w)
        new_row = prev is None or (L.cy - prev.cy > 1.3 * base and 0 in cells)
        if new_row:
            rows.append([[] for _ in starts])
        for ci, cw in cells.items():
            rows[-1][ci].append(join_words(cw))
        prev = L
    out = []
    for r in rows:
        cells = [join_lines(c) for c in r]
        out.append(" — ".join(f"{n} : {c}" for n, c in zip(names, cells)))
    return out


# ---------------------------------------------------------------------------
# Glossaire
# ---------------------------------------------------------------------------
def parse_glossary(pages_ws, warn):
    """Glossaire sur trois colonnes : « TERME n — définition ». Le terme (gras) et le numéro de chapitre
    (pastille) se distinguent de la définition par la hauteur de leurs caractères."""
    all_ws = [w for ws in pages_ws for w in ws]
    h_def = Counter(round(w.h, 2) for w in all_ws if re.search(r"[a-zé]", w.t)).most_common(1)[0][0]
    num_cands = Counter(round(w.h, 2) for w in all_ws if re.fullmatch(r"\d+", w.t) and abs(w.h - h_def) > 0.5)
    h_num = num_cands.most_common(1)[0][0]
    term_cands = Counter(round(w.h, 2) for w in all_ws if re.fullmatch(r"[A-ZÀ-ÝŒ][A-ZÀ-ÝŒ'’\-]+", w.t)
                         and h_def + 0.5 < w.h < h_def + 4)
    h_term = term_cands.most_common(1)[0][0]
    stream = []  # (kind, word, line_id)
    dropped = []
    line_id = 0
    for pi, ws in enumerate(pages_ws):
        ws = [w for w in ws if w.y0 < 800]
        tiny_top = [w for w in ws if w.y1 < 50 and w.h < 10]
        if tiny_top:
            dropped.append(" ".join(w.t for w in tiny_top))
        ws = [w for w in ws if w not in tiny_top]
        if pi == 0:
            first_hdr = min((w for w in ws if len(w.t) == 1 and w.t.isalpha() and w.h > 14 and w.y0 > 150),
                            key=lambda w: w.y0)
            ws = [w for w in ws if w.y0 >= first_hdr.y0 - 12]
        ws = [w for w in ws if not (len(w.t) == 1 and w.t.isalpha() and w.h > 14)]  # lettres de section
        for c0, c1 in ((0, 205), (205, 380), (380, 1000)):
            col = [w for w in ws if c0 <= w.x0 < c1]
            for L in group_lines(col):
                line_id += 1
                for w in L.w:
                    if abs(w.h - h_term) < 0.3:
                        k = "T"
                    elif abs(w.h - h_num) < 0.3 and re.fullmatch(r"\d+", w.t):
                        k = "N"
                    else:
                        k = "X"
                    stream.append((k, w, line_id))
    if dropped:
        warn(f"glossaire : fragments isolés en marge haute ignorés : {dropped}")
    entries = []
    i = 0
    n = len(stream)

    def text_of(items):
        by_line = defaultdict(list)
        order = []
        for _, w, lid in items:
            if lid not in by_line:
                order.append(lid)
            by_line[lid].append(w)
        return join_lines([join_words(by_line[l]) for l in order])

    while i < n:
        if stream[i][0] != "T":
            warn(f"glossaire : texte hors entrée ignoré : {stream[i][1].t!r}")
            i += 1
            continue
        term = []
        while i < n and stream[i][0] == "T":
            term.append(stream[i]); i += 1
        chap = None
        if i < n and stream[i][0] == "N":
            chap = int(stream[i][1].t); i += 1
        else:
            warn(f"glossaire : numéro de chapitre manquant après {text_of(term)!r}")
        if i < n and stream[i][1].t == "—":
            i += 1
        else:
            warn(f"glossaire : tiret manquant après {text_of(term)!r}")
        dfn = []
        while i < n and stream[i][0] != "T":
            dfn.append(stream[i]); i += 1
        entries.append({"term": text_of(term), "chapter": chap, "definition": text_of(dfn)})
    return entries


# ---------------------------------------------------------------------------
# Solutions (contrôle croisé des grilles)
# ---------------------------------------------------------------------------
def parse_solutions(pages_ws, warn):
    grids = []
    for ws in pages_ws:
        ws = body(ws, top=60)
        hs = Counter(round(w.h, 2) for w in ws if re.fullmatch(r"[A-Z]+", w.t))
        gh = hs.most_common(1)[0][0]
        letters = [l for w in ws if re.fullmatch(r"[A-Z]+", w.t) and abs(w.h - gh) < 0.2 for l in split_letters(w)]
        cols = [[l for l in letters if c0 <= l.cx < c1] for c0, c1 in ((0, 210), (210, 385), (385, 1000))]
        per_col = []
        for col in cols:
            rows = group_lines(col, tol=1.5)
            blocks, cur = [], []
            for r in rows:
                if cur and r.cy - cur[-1].cy > 12:
                    blocks.append(cur); cur = []
                cur.append(r)
            if cur:
                blocks.append(cur)
            per_col.append([["".join(w.t for w in r.w) for r in b] for b in blocks])
        for r in range(max(len(c) for c in per_col)):
            for c in per_col:
                if r < len(c):
                    grids.append(c[r])
    return grids


def _mult(m, n):
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return [a * a2 + b * c2, a * b2 + b * d2, c * a2 + d * c2, c * b2 + d * d2, e * a2 + f * c2 + e2, e * b2 + f * d2 + f2]


def solution_bands(pdf: Path, page_numbers, warn):
    """Bandes de couleur des « Solutions des grilles » : chaque mot y est un segment tracé d'un centre de case
    à l'autre, en coordonnées locales de grille (case de 5 unités, centres en 2,5 + 5k). Retourne, dans l'ordre
    des chapitres, la liste des segments (ligne0, col0, ligne1, col1) de chaque grille."""
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    reader = PdfReader(str(pdf))
    grids = []
    for p in page_numbers:
        page = reader.pages[p - 1]
        height = float(page.mediabox.height)
        cs = ContentStream(page.get_contents(), reader)
        ctm, stack, cur = [1, 0, 0, 1, 0, 0], [], None
        groups, order = defaultdict(list), []
        for operands, op in cs.operations:
            if op == b"q":
                stack.append(ctm[:])
            elif op == b"Q":
                ctm = stack.pop()
            elif op == b"cm":
                ctm = _mult([float(x) for x in operands], ctm)
            elif op == b"m":
                cur = [(float(operands[0]), float(operands[1]))]
            elif op == b"l" and cur is not None:
                cur.append((float(operands[0]), float(operands[1])))
            elif op == b"S":
                if cur and len(cur) == 2:
                    k = tuple(round(v, 3) for v in ctm)
                    if k not in groups:
                        order.append(k)
                    groups[k].append(cur)
                cur = None
            elif op in (b"f", b"F", b"f*", b"n", b"B", b"B*", b"b", b"b*", b"s", b"re"):
                cur = None
        page_grids = []
        for k in order:
            bands = []
            for (x0, y0), (x1, y1) in groups[k]:
                vals = [(v - 2.5) / 5 for v in (x0, y0, x1, y1)]
                if all(abs(v - round(v)) < 1e-6 and 0 <= round(v) <= 19 for v in vals):
                    c0, r0, c1, r1 = (int(round(v)) for v in vals)
                    bands.append((r0, c0, r1, c1))
            if not bands:
                continue
            a, b, c, d, e, f = k
            top = height - (b * 50 + d * 50 + f)
            left = a * 50 + c * 50 + e
            page_grids.append((top, left, bands))
        # ordre de lecture : rangées (à 30 pt près), puis de gauche à droite
        page_grids.sort(key=lambda g: g[0])
        rows = []
        for g in page_grids:
            if rows and abs(g[0] - rows[-1][0][0]) < 30:
                rows[-1].append(g)
            else:
                rows.append([g])
        for r in rows:
            for g in sorted(r, key=lambda g: g[1]):
                grids.append(g[2])
    return grids


def band_letters(grid, band):
    r0, c0, r1, c1 = band
    n = max(abs(r1 - r0), abs(c1 - c0)) + 1
    dr = (r1 > r0) - (r1 < r0)
    dc = (c1 > c0) - (c1 < c0)
    if not (r0 == r1 or c0 == c1 or abs(r1 - r0) == abs(c1 - c0)):
        return None, None
    cells = [(r0 + dr * k, c0 + dc * k) for k in range(n)]
    if any(not (0 <= r < len(grid) and 0 <= c < len(grid[r])) for r, c in cells):
        return None, None
    return "".join(grid[r][c] for r, c in cells), (dr, dc)


# ---------------------------------------------------------------------------
# Bibliographie
# ---------------------------------------------------------------------------
def parse_bibliography(pages_ws, warn):
    lines = []
    for ws in pages_ws:
        lines += group_lines(body(ws, top=40))
    intro, entries, section = [], [], None
    sections = []
    num_x = min((L.w[0].x0 for L in lines if re.fullmatch(r"\d+\.", L.w[0].t)), default=0)
    for L in lines:
        t = L.text()
        if t == "Bibliographie":
            continue
        # numéro d'entrée : dans la colonne des numéros (une ligne de suite « 2021. » est en retrait)
        if re.fullmatch(r"\d+\.", L.w[0].t) and len(L.w) > 1 and L.w[0].x0 < num_x + 6 and L.w[1].x0 - L.w[0].x1 > 2:
            entries.append({"section": section, "lines": [join_words(L.w[1:])]})
        elif L.h >= 16:
            section = t
            sections.append(t)
        elif entries:
            entries[-1]["lines"].append(t)
        else:
            intro.append(t)
    out = [{"section": e["section"], "citation": join_lines(e["lines"])} for e in entries]
    return join_lines(intro), out, sections


# ---------------------------------------------------------------------------
# Assemblage
# ---------------------------------------------------------------------------
def distinct_locations(placements, word):
    """Nombre d'emplacements distincts (ensembles de cases) : un palindrome lu dans les deux sens compte une fois."""
    return len({frozenset((r + dr * k, c + dc * k) for k in range(len(word))) for r, c, dr, dc in placements})


def find_placements(grid, word):
    n = len(grid)
    found = []
    for r in range(n):
        for c in range(len(grid[r])):
            if grid[r][c] != word[0]:
                continue
            for dr, dc in DIRECTIONS:
                ok = True
                for k, ch in enumerate(word):
                    rr, cc = r + dr * k, c + dc * k
                    if not (0 <= rr < n and 0 <= cc < len(grid[rr])) or grid[rr][cc] != ch:
                        ok = False
                        break
                if ok:
                    found.append((r, c, dr, dc))
    return found


TIERS = {
    "exact": "intitulé identique (forme grille)",
    "mots": "mot = mot(s) de l'intitulé",
    "sous-chaine": "mot contenu dans l'intitulé",
    "racine": "même racine qu'un mot de l'intitulé",
    "definition": "mot présent dans le texte de la définition",
    "optimal": "mots en concurrence pour les mêmes entrées : appariement de preuve textuelle maximale, commun à"
               " toutes les solutions optimales",
    "elimination": "dernière paire restante du chapitre (60 mots ↔ 60 entrées)",
}


def _tokens(s):
    return [t for t in re.findall(r"[^\s\-–—'’()/,.:;«»0-9]+", s) if grid_form(t)]


def _tier_ok(tier, word, e):
    term = e["term"]
    if tier == "exact":
        return grid_form(term) == word
    if tier == "mots":
        toks = [grid_form(t) for t in _tokens(term)]
        return any("".join(toks[a:b]) == word for a in range(len(toks)) for b in range(a + 1, len(toks) + 1))
    if tier == "sous-chaine":
        # début ou fin d'un mot de l'intitulé (BRONCHE ⊂ BRONCHES, SPASME ⊂ BRONCHOSPASME)
        return len(word) >= 3 and any(t != word and (t.startswith(word) or t.endswith(word))
                                      for t in (grid_form(x) for x in _tokens(term)))
    if tier == "racine":
        for t in (grid_form(x) for x in _tokens(term)):
            k = 0
            while k < min(len(t), len(word)) and t[k] == word[k]:
                k += 1
            if k >= 5 and k >= len(word) - 3:
                return True
        return False
    if tier == "definition":
        toks = {grid_form(t) for t in _tokens(e["definition"])}
        return any(t in toks for t in (word, word + "S", word + "X"))
    return False


def _span_with_form(text, word):
    """Plus courte portion de `text` (bornée par des lettres) dont la forme grille vaut `word`."""
    best = None
    for i in range(len(text)):
        if not text[i].isalpha():
            continue
        for j in range(i + 1, len(text) + 1):
            if not text[j - 1].isalpha():
                continue
            g = grid_form(text[i:j])
            if g == word:
                if best is None or j - i < len(best):
                    best = text[i:j]
                break
            if not word.startswith(g):
                break
    return best


def _optimal_common_pairs(words, entries, edge, weight, max_size=10):
    adj = {i: [j for j in entries if edge(i, j)] for i in words}
    # composantes connexes du graphe mots–entrées
    seen, comps = set(), []
    for i in words:
        if i in seen or not adj[i]:
            continue
        comp_w, stack = set(), [i]
        while stack:
            x = stack.pop()
            if x in comp_w:
                continue
            comp_w.add(x)
            for j in adj[x]:
                for y in words:
                    if j in adj[y] and y not in comp_w:
                        stack.append(y)
        seen |= comp_w
        comps.append(sorted(comp_w))
    out = []
    for comp in comps:
        if len(comp) > max_size:
            continue
        best, sols = -1, []

        def rec(k, used, total, pairs):
            nonlocal best, sols
            if k == len(comp):
                if total > best:
                    best, sols = total, [list(pairs)]
                elif total == best:
                    sols.append(list(pairs))
                return
            i = comp[k]
            for j in adj[i]:
                if j not in used:
                    used.add(j)
                    pairs.append((i, j))
                    rec(k + 1, used, total + weight(i, j), pairs)
                    pairs.pop()
                    used.discard(j)
            rec(k + 1, used, total, pairs)

        rec(0, set(), 0, [])
        common = set(sols[0])
        for s in sols[1:]:
            common &= set(s)
        out += sorted(common)
    return out


def match_terms(words, gl_entries, warn):
    """Associe chaque mot de la grille à une entrée du glossaire du même chapitre. Le glossaire compte
    exactement une entrée par mot caché (60 par chapitre) mais son intitulé est souvent plus complet que le mot
    (« CHARGE » ↔ « DOSE DE CHARGE »). Rattachement par niveaux de preuve décroissants, une paire n'étant retenue
    que si elle est univoque à son niveau (TIERS). Les mots sans preuve univoque gardent une définition vide."""
    result = [None] * len(words)
    rw = {i for i in range(len(words))}
    re_ = list(range(len(gl_entries)))
    how = {}
    def assign(i, j, tier):
        result[i] = j
        how[i] = tier
        rw.discard(i)
        re_.remove(j)

    order = ("exact", "mots", "sous-chaine", "racine", "definition")
    ok_cache = {}

    def ok(tier, i, j):
        k = (tier, i, j)
        if k not in ok_cache:
            ok_cache[k] = _tier_ok(tier, words[i], gl_entries[j])
        return ok_cache[k]

    def upto(ti, i, j):
        return any(ok(t, i, j) for t in order[:ti + 1])

    def strongest(i, j):
        return next(t for t in order if ok(t, i, j))

    def restriction(i, ti):
        """Candidats du mot au niveau le plus fort où il en a (parmi les entrées restantes) : un mot ambigu à un
        niveau fort ne peut pas être rattaché, à un niveau plus faible, à une autre entrée."""
        for t in order[:ti]:
            s = {j for j in re_ if ok(t, i, j)}
            if s:
                return s
        return None

    progress = True
    while progress:
        progress = False
        for ti, tier in enumerate(order):
            changed = True
            while changed:
                changed = False
                cand = {}
                for i in rw:
                    r = restriction(i, ti)
                    cand[i] = [j for j in re_ if upto(ti, i, j) and (r is None or j in r)]
                back = defaultdict(list)
                for i, js in cand.items():
                    for j in js:
                        back[j].append(i)
                # 1) mot n'ayant qu'un candidat, que nul autre mot n'a pour candidat unique ; si plusieurs mots
                #    n'ont que ce candidat, il revient à celui qui n'a aucune autre entrée possible à aucun niveau
                singles = defaultdict(list)
                for i, js in cand.items():
                    if len(js) == 1:
                        singles[js[0]].append(i)
                for j, iis in singles.items():
                    if len(iis) > 1:
                        alone = [i for i in iis if [x for x in re_ if upto(len(order) - 1, i, x)] == [j]]
                        iis = alone
                    if len(iis) == 1:
                        assign(iis[0], j, strongest(iis[0], j))
                        changed = True
                if not changed:
                    # 2) entrée n'ayant qu'un mot candidat, ce mot n'ayant pas d'autre entrée dans le même cas
                    owners = defaultdict(list)
                    for j, iis in back.items():
                        if len(iis) == 1:
                            owners[iis[0]].append(j)
                    for i, js in owners.items():
                        if len(js) == 1:
                            assign(i, js[0], strongest(i, js[0]))
                            changed = True
                if changed:
                    progress = True
            if progress:
                break  # une nouvelle paire peut lever une ambiguïté à un niveau plus fort : on recommence
        if not progress:
            # 3) groupes résiduels de mots en concurrence : appariement de preuve totale maximale ;
            #    on ne retient que les paires communes à tous les appariements optimaux
            for i, j in _optimal_common_pairs(sorted(rw), list(re_), lambda i, j: upto(len(order) - 1, i, j),
                                              lambda i, j: len(order) - order.index(strongest(i, j))):
                assign(i, j, "optimal")
                progress = True
    if len(rw) == 1 and len(re_) == 1:
        i = next(iter(rw))
        result[i] = re_[0]
        how[i] = "elimination"
        rw.clear()
        re_.clear()
    out, notes, stats = [], [], Counter()
    for i, w in enumerate(words):
        j = result[i]
        if j is None:
            out.append((w, "", None))
            stats["vide"] += 1
            continue
        e = gl_entries[j]
        stats[how[i]] += 1
        if how[i] == "exact":
            out.append((e["term"], e["definition"], e["term"]))
        else:
            span = _span_with_form(e["term"], w) if how[i] in ("mots", "sous-chaine") else None
            out.append((span or w, e["definition"], e["term"]))
            notes.append(("lien", w, e["term"], how[i]))
    for i in sorted(rw):
        notes.append(("vide", words[i], None, None))
    for j in re_:
        notes.append(("orpheline", None, gl_entries[j]["term"], None))
    return out, notes, stats


def build_book(pdf: Path, slug: str, warnings: list):
    pages = load_pdf(pdf)
    W_ = lambda msg: warnings.append(msg)
    chapters_toc, end_matter, parts = parse_toc(pages[3])
    copyright_line, fields, legal_paras = parse_legal(pages[1])
    gl_start = next(v for k, v in end_matter.items() if k.startswith("Glossaire"))
    annex_a = next(v for k, v in end_matter.items() if k.startswith("Annexe A"))
    sol = end_matter["Solutions des grilles"]
    coll = next(v for k, v in end_matter.items() if k.startswith("La collection"))
    bib = end_matter["Bibliographie"]
    glossary = parse_glossary([pages[p - 1] for p in range(gl_start, annex_a)], W_)
    sol_grids = parse_solutions([pages[p - 1] for p in range(sol, coll)], W_)
    sol_bands = solution_bands(pdf, range(sol, coll), W_)
    if len(sol_bands) != len(chapters_toc):
        W_(f"{len(sol_bands)} grilles à bandes dans les solutions pour {len(chapters_toc)} chapitres")
    bib_intro, bibliography, bib_sections = parse_bibliography([pages[p - 1] for p in range(bib, len(pages))], W_)
    gl_by_ch = defaultdict(list)
    for e in glossary:
        gl_by_ch[e["chapter"]].append(e)
    chapters = []
    for ch in chapters_toc:
        cw = []
        warn = lambda msg, n=ch["num"]: cw.append(msg)
        p0 = ch["page"] - 1
        if ch["grid_page"] != ch["page"] + 2:
            warn("page de grille inattendue dans la table des matières")
        op = parse_opening(pages[p0], warn)
        if op["title_printed"] and op["title_printed"] != ch["title"]:
            warn(f"titre de la page d'ouverture différent de la table des matières : {op['title_printed']!r}")
        if op.get("planche_num") not in (None, ch["num"]):
            warn(f"numéro de planche {op.get('planche_num')} ≠ chapitre")
        summary, vignettes = parse_summary_page(pages[p0 + 1], warn)
        grid, words = parse_grid_page(pages[p0 + 2], warn)
        questions, pitfalls, alerts = parse_questions_page(pages[p0 + 3], warn)
        matched, match_notes, match_stats = match_terms(words, gl_by_ch.get(ch["num"], []), warn)
        terms, placements = [], []
        bands = sol_bands[ch["num"] - 1] if ch["num"] - 1 < len(sol_bands) else []
        band_words = {}
        for b in bands:
            s, d = band_letters(grid, b)
            if s is None:
                warn(f"bande de solution hors grille ou non rectiligne : {b}")
                continue
            if s in words:
                band_words.setdefault(s, []).append((b[0], b[1], d[0], d[1]))
            elif s[::-1] in words:
                n = len(s) - 1
                band_words.setdefault(s[::-1], []).append((b[2], b[3], -d[0], -d[1]))
            else:
                warn(f"bande de solution ne correspondant à aucun mot : {s!r} {b}")
        if bands and len(bands) != 60:
            warn(f"{len(bands)} bandes dans la grille de solution (60 attendues)")
        multi = []
        for i, (w, (fr, dfn, src)) in enumerate(zip(words, matched)):
            terms.append({"word": w, "fr": fr, "definition": {"fr": dfn}})
            pl = find_placements(grid, w)
            if not pl:
                warn(f"MOT INTROUVABLE dans la grille : {w}")
                continue
            occ = distinct_locations(pl, w)
            bw = band_words.get(w, [])
            if len(bw) == 1 and bw[0] in pl:
                r, c, dr, dc = bw[0]
            else:
                warn(f"{w} : emplacement non confirmé par les solutions ({len(bw)} bande(s)) ; premier trouvé retenu")
                r, c, dr, dc = pl[0]
            if occ > 1:
                multi.append((w, occ, (r, c, dr, dc)))
            elif len(pl) > 1:
                multi.append((w, 1, "palindrome"))
            # occurrences = nombre de lectures (départ, direction), convention de check_books.py :
            # un palindrome compte donc 2 pour un seul emplacement (voir notes de book.json)
            placements.append({"term_index": i, "word": w, "row": r, "col": c, "d_row": dr, "d_col": dc,
                               "occurrences": len(pl)})
        key_points = []
        if op["perle"]:
            key_points.append({"fr": op["perle"]})
        if op["band_items"]:
            key_points.append({"fr": f"{op['band_title']} : " + " · ".join(op["band_items"])})
        figures = []
        if op["carte"]:
            figures.append({"caption": op["carte"], "source": ""})
        if op["planche"]:
            figures.append({"caption": op["planche"], "source": ""})
        slug_ch = slugify(ch["title"])
        doc = {
            "book": slug, "order": ch["num"], "slug": slug_ch,
            "title": {"fr": ch["title"]},
            "description": {"fr": op["subtitle"]},
            "summary": {"fr": summary},
            "key_points": key_points,
            "pitfalls": [{"fr": p} for p in pitfalls],
            "red_flags": [{"fr": a} for a in alerts],
            "figures": figures,
            "terms": terms,
            "grid": {"size": len(grid), "rows": grid},
            "placements": placements,
            "questions": [{"fr": q} for q in questions],
            "vignettes": [{"case": {"fr": v["case"]}, "answer": {"fr": v["answer"]}} for v in vignettes],
            "references": [],
        }
        # contrôles
        if len(grid) != 20 or any(len(r) != len(grid) for r in grid):
            warn(f"grille non carrée ou ≠ 20 : {len(grid)} lignes, longueurs {sorted(set(len(r) for r in grid))}")
        if len(words) != 60:
            warn(f"{len(words)} mots dans la liste (60 attendus)")
        if words != sorted(words):
            warn("liste de mots non alphabétique dans l'ordre de lecture colonne par colonne")
        if len(questions) != 8:
            warn(f"{len(questions)} questions (8 attendues)")
        if [v["n"] for v in vignettes] != [1, 2, 3]:
            warn(f"vignettes numérotées {[v['n'] for v in vignettes]}")
        if len(pitfalls) != 3:
            warn(f"{len(pitfalls)} pièges (3 attendus)")
        if ch["num"] - 1 < len(sol_grids) and sol_grids[ch["num"] - 1] != grid:
            warn("la grille diffère de celle des « Solutions des grilles »")
        chapters.append({"doc": doc, "warnings": cw, "match_notes": match_notes, "match_stats": match_stats,
                         "opening": op, "multi": multi})
    if len(sol_grids) != len(chapters_toc):
        warnings.append(f"{len(sol_grids)} grilles de solution pour {len(chapters_toc)} chapitres")
    return {"pages": len(pages), "toc": chapters_toc, "end_matter": end_matter, "parts": parts,
            "copyright": copyright_line, "fields": fields, "legal_paras": legal_paras,
            "glossary": glossary, "bibliography": bibliography, "bib_intro": bib_intro, "bib_sections": bib_sections,
            "chapters": chapters}


def book_json(slug, title, data, notes):
    f = data["fields"]
    authors = [a.strip() for a in f.get("Auteurs", "").split("&")]
    year = int(re.search(r"\d{4}", data["copyright"]).group(0))
    credits = [data["copyright"]]
    for k in ("Titre", "Auteurs", "Édition", "Lieu d'impression"):
        if k in f:
            credits.append(f"{k} : {f[k]}")
    credits += data["legal_paras"]
    if data["bib_intro"]:
        credits.append(data["bib_intro"])
    total_terms = sum(len(c["doc"]["terms"]) for c in data["chapters"])
    return {
        "slug": slug,
        "title": {"fr": title},
        "authors": authors,
        "edition": f.get("Édition", ""),
        "year": year,
        "chapter_count": len(data["chapters"]),
        "word_count": total_terms,
        "bibliography": [{"citation": b["citation"], "url": ""} for b in data["bibliography"]],
        "credits": credits,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Comparaison des deux versions de la sémiologie
# ---------------------------------------------------------------------------
def compare_semio(d1, d2):
    report = []
    t1 = {c["title"]: c for c in d1["toc"]}
    t2 = {c["title"]: c for c in d2["toc"]}
    only1 = [c["title"] for c in d1["toc"] if c["title"] not in t2]
    only2 = [c["title"] for c in d2["toc"] if c["title"] not in t1]
    report.append(f"Édition v1 : {d1['fields'].get('Édition')}")
    report.append(f"Édition v2 : {d2['fields'].get('Édition')}")
    report.append(f"Copyright v1 : {d1['copyright']} ; v2 : {d2['copyright']}")
    report.append(f"Chapitres v1 : {len(d1['toc'])} ; v2 : {len(d2['toc'])}")
    report.append(f"Chapitres seulement dans v1 : {only1}")
    report.append(f"Chapitres seulement dans v2 : {only2}")
    c1 = {c["doc"]["title"]["fr"]: c["doc"] for c in d1["chapters"]}
    c2 = {c["doc"]["title"]["fr"]: c["doc"] for c in d2["chapters"]}
    for title in c1:
        if title not in c2:
            continue
        a, b = dict(c1[title]), dict(c2[title])
        diffs = [k for k in a if k not in ("order",) and a[k] != b[k]]
        if diffs:
            report.append(f"  « {title} » : champs différents {diffs}")
            for k in diffs:
                if k == "summary":
                    _difftext(report, a[k]["fr"], b[k]["fr"])
    g1 = {(e["term"], e["definition"]) for e in d1["glossary"]}
    g2 = {(e["term"], e["definition"]) for e in d2["glossary"]}
    report.append(f"Glossaire v1 : {len(d1['glossary'])} entrées ; v2 : {len(d2['glossary'])}")
    report.append(f"  entrées (terme, définition) seulement dans v1 : {len(g1 - g2)} ; seulement dans v2 : {len(g2 - g1)}")
    for t, dfn in sorted(g2 - g1)[:20]:
        report.append(f"    v2 seulement : {t} — {dfn[:80]}")
    b1 = [b["citation"] for b in d1["bibliography"]]
    b2 = [b["citation"] for b in d2["bibliography"]]
    report.append(f"Bibliographie identique : {b1 == b2}")
    report.append(f"Mentions légales identiques (hors édition) : {d1['legal_paras'] == d2['legal_paras']}")
    return report


def _difftext(report, a, b):
    import difflib
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            report.append(f"      {op}: {a[max(0, i1 - 20):i2 + 20]!r} -> {b[max(0, j1 - 20):j2 + 20]!r}")


# ---------------------------------------------------------------------------
def write_book(slug, title, data, notes, dry):
    out = OUT_ROOT / slug
    files = []
    for c in data["chapters"]:
        d = c["doc"]
        files.append((out / f"{d['order']:02d}-{d['slug']}.json", d))
    files.append((out / "book.json", book_json(slug, title, data, notes)))
    if dry:
        return files
    out.mkdir(parents=True, exist_ok=True)
    for path, doc in files:
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return files


def collect_notes(data, extra):
    notes = list(extra)
    for c in data["chapters"]:
        d = c["doc"]
        for w in c["warnings"]:
            notes.append(f"Chapitre {d['order']:02d} : {w}")
        by_tier = defaultdict(list)
        for kind, w, term, tier in c["match_notes"]:
            if kind == "lien":
                by_tier[tier].append(f"{w} → « {term} »")
        for tier in ("mots", "sous-chaine", "racine", "definition", "optimal", "elimination"):
            if by_tier[tier]:
                notes.append(f"Chapitre {d['order']:02d} : définition rattachée ({TIERS[tier]}) : "
                             + " ; ".join(by_tier[tier]))
        orphans = [term for kind, _, term, _ in c["match_notes"] if kind == "orpheline"]
        if orphans:
            notes.append(f"Chapitre {d['order']:02d} : entrées du glossaire non rattachées à un mot (à apparier par"
                         f" un éditeur) : " + " ; ".join(f"« {t} »" for t in orphans))
        pal = [w for w, n, p in c["multi"] if p == "palindrome"]
        if pal:
            notes.append(f"Chapitre {d['order']:02d} : palindromes (un seul emplacement, lisible dans les deux sens ; occurrences = 2) : "
                         + ", ".join(pal))
        for w, n, p in c["multi"]:
            if p != "palindrome":
                r, cc, dr, dc = p
                notes.append(f"Chapitre {d['order']:02d} : le mot {w} apparaît à {n} emplacements dans la grille ;"
                             f" placement retenu = celui surligné dans les solutions (ligne {r}, colonne {cc},"
                             f" direction {dr},{dc})")
        empty = [t["word"] for t in d["terms"] if not t["definition"]["fr"]]
        if empty:
            notes.append(f"Chapitre {d['order']:02d} : définitions absentes du glossaire : {empty}")
    return notes


MAPPING_NOTES = [
    "Correspondance avec le schéma : description = sous-titre de la page d'ouverture ; summary = « Résumé théorique » ;"
    " key_points[0] = encadré « PERLE » de la page d'ouverture, key_points[1] = bandeau des éléments clés du chapitre"
    " (titre du bandeau imprimé, puis éléments séparés par « · ») ; pitfalls = « Pièges classiques à l'examen » ;"
    " questions = « Questions médicales » ; vignettes = « Corrélations cliniques — vignettes de type USMLE »"
    " (énoncé sans le libellé « VIGNETTE n », réponse sans le libellé « Réponse — ») ;"
    " figures = libellés de la carte et de la planche de la page d'ouverture.",
    "Non repris (pas de champ dans le schéma) : contenu des cartes et tableaux des planches, préface, fiches d'évaluation,"
    " annexes, page « La collection », table de solutions (utilisée seulement pour vérifier les grilles).",
    "Mise en forme : lignes recollées ; trait d'union typographique de fin de ligne (U+2010) supprimé ; trait d'union"
    " des mots composés conservé ; espaces reconstitués d'après les écarts entre mots du PDF.",
    "Les contacts téléphoniques et le prix imprimés dans les « Informations légales » ne sont pas repris dans credits.",
    "Les références sont regroupées dans bibliography (book.json) ; references des chapitres est vide (aucune référence"
    " par chapitre dans le livre).",
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", choices=["pharmacologie", "semiologie", "all"], default="all")
    ap.add_argument("--semio-pdf", default=str(PDF_SEMIO_1), help="version de la sémiologie à importer")
    ap.add_argument("--compare-semio", action="store_true", help="compare les deux versions de la sémiologie")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    if args.compare_semio:
        w1, w2 = [], []
        d1 = build_book(PDF_SEMIO_1, "semiologie", w1)
        d2 = build_book(PDF_SEMIO_2, "semiologie", w2)
        for line in compare_semio(d1, d2):
            print(line)
        return 0

    todo = []
    if args.book in ("pharmacologie", "all"):
        todo.append(("pharmacologie", Path(PDF_PHARMA), "Pharmacologie par classes thérapeutiques"))
    if args.book in ("semiologie", "all"):
        todo.append(("semiologie", Path(args.semio_pdf), "Sémiologie médicale par systèmes"))
    status = 0
    for slug, pdf, fallback_title in todo:
        warnings = []
        data = build_book(pdf, slug, warnings)
        title_full = data["fields"].get("Titre", "")
        m = re.match(r"CHERCHE ET DIAGNOSTIQUE — (.*?)(?: \(édition expert\))?$", title_full)
        title = m.group(1) if m else fallback_title
        extra = list(MAPPING_NOTES)
        extra.insert(0, f"Source : {pdf.name} ({data['pages']} pages).")
        if slug == "semiologie":
            extra.insert(1, SEMIO_CHOICE_NOTE)
        if data["parts"]:
            extra.append("Parties du livre : " + " ; ".join(
                f"{p['title']} (chapitres {p['chapters'][0]}–{p['chapters'][-1]})" for p in data["parts"]))
        if data["bib_sections"]:
            extra.append("Rubriques de la bibliographie (ordre conservé) : " + " ; ".join(data["bib_sections"]))
        extra += [f"Livre : {w}" for w in warnings]
        notes = collect_notes(data, extra)
        files = write_book(slug, title, data, notes, args.dry_run)
        n_terms = sum(len(c["doc"]["terms"]) for c in data["chapters"])
        n_empty = sum(1 for c in data["chapters"] for t in c["doc"]["terms"] if not t["definition"]["fr"])
        n_multi = sum(1 for c in data["chapters"] for m in c["multi"] if m[2] != "palindrome")
        n_pal = sum(1 for c in data["chapters"] for m in c["multi"] if m[2] == "palindrome")
        n_missing = sum(len(c["doc"]["terms"]) - len(c["doc"]["placements"]) for c in data["chapters"])
        print(f"[{slug}] {len(data['chapters'])} chapitres, {n_terms} termes, {len(data['glossary'])} entrées de glossaire,"
              f" {n_empty} définitions vides, {n_multi} mots à plusieurs emplacements, {n_pal} palindromes,"
              f" {n_missing} mots introuvables,"
              f" {sum(len(c['doc']['vignettes']) for c in data['chapters'])} vignettes,"
              f" {sum(len(c['doc']['questions']) for c in data['chapters'])} questions,"
              f" {len(data['bibliography'])} références ; {len(files)} fichiers {'(non écrits)' if args.dry_run else 'écrits'}")
        for n in notes[len(extra) - len(warnings):]:
            if args.verbose or not re.search(r"définition rattachée|palindromes", n):
                print("   -", n)
        if n_missing:
            status = 1
    return status


SEMIO_CHOICE_NOTE = (
    "Version importée : Semiologie_par_Systemes-1 (121 p., « Première édition (21 chapitres …) », 1260 termes). "
    "La version -2 (116 p., « Première édition (20 chapitres …) », 1200 termes) porte la même mention d'édition et le "
    "même copyright (2026) : aucune date ne permet de dire laquelle est la plus récente ; la -1 est la plus complète. "
    "Elle contient en plus le chapitre 11 « Examen Physique en Gynécologie-Obstétrique » (avec ses 60 termes du "
    "glossaire, ses syndromes de l'annexe A et sa mention dans la préface) ; les 20 autres chapitres sont identiques mot "
    "pour mot dans les deux versions (seuls diffèrent la numérotation à partir du chapitre 11 et les coupures de lignes). "
    "Rien n'existe uniquement dans la version -2 (voir --compare-semio)."
)

if __name__ == "__main__":
    sys.exit(main())
