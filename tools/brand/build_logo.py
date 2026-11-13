"""Logos et icônes de l'application, en aplats, d'après le logo vectoriel du design system.

Usage : python3 -I tools/brand/build_logo.py
Entrée : assets/brand/logo-vectoriel.json (tracés du composant Logo du design system « Cherche & Diagnostic »).
Sorties (apps/web/public/brand/) :
  logo-horizontal.svg, logo-horizontal-inverse.svg (en-têtes, thème clair / sombre),
  logo-vertical.svg (écran d'accueil), symbole.svg (sous 160 px de large),
  icon-512.png, icon-192.png, icon-maskable-512.png, apple-touch-icon.png, favicon-48.png (icône d'application),
  logo-horizontal.png (e-mails : la plupart des messageries n'affichent pas le SVG).
Règles du design system : aplats uniquement, pas de dégradé ni de reflet ajouté, pas de recoloration hors des deux tons.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / 'assets/brand/logo-vectoriel.json').read_text())
OUT = ROOT / 'apps/web/public/brand'

CLAIR = {'crois': '#012d69', 'mot1': '#012d69', 'stetho': '#001b45', 'nuit': '#001b45', 'bande': '#0a4aa6',
         'royal': '#0a62c9', 'ciel': '#079cef', 'et': '#079cef', 'trait': '#079cef', 'croix': '#d80403',
         'mot2': '#d80403', 'reflet': '#ffffff'}
# Version inverse, sur fond marine ou sombre : encres marine en blanc et ciel clair, rouge éclairci.
INVERSE = {**CLAIR, 'crois': '#ffffff', 'mot1': '#ffffff', 'stetho': '#ffffff', 'nuit': '#dce7f6', 'bande': '#9db8de',
           'royal': '#8ccff5', 'croix': '#ff5a55', 'mot2': '#ff5a55'}


def marque(c: dict) -> str:
    return ''.join(f'<path d="{d}" fill="{c[k]}"{" fill-rule=\"evenodd\"" if eo else ""}/>' for d, k, eo in DATA['parts'])


def nom(c: dict) -> str:
    e = DATA['emb']
    return ''.join(f'<path d="{d}" fill="{c[k]}" stroke="{c[k]}" stroke-width="{e}" stroke-linejoin="round"/>' for d, k in DATA['word'])


def svg(viewbox: str, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" role="img" aria-label="Cherche &amp; Diagnostic">'
            f'<title>Cherche &amp; Diagnostic</title>{body}</svg>\n')


def horizontal(c: dict) -> str:
    h = DATA['horizontal']
    return svg(f"0 0 {h['largeur']} 240", f'<g transform="{h["marque"]}">{marque(c)}</g><g transform="{h["nom"]}">{nom(c)}</g>')


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        'logo-horizontal.svg': horizontal(CLAIR),
        'logo-horizontal-inverse.svg': horizontal(INVERSE),
        'logo-vertical.svg': svg('93 31 1089 1146', marque(CLAIR) + nom(CLAIR) + f'<path d="{DATA["trait"]}" fill="{CLAIR["trait"]}"/>'),
        'symbole.svg': svg('222 51 814 747', marque(CLAIR)),
    }
    for name, text in files.items():
        (OUT / name).write_text(text)
    # Icône d'application : symbole sur carré blanc arrondi (22 % du côté) ; version « maskable » à fond plein.
    sym = marque(CLAIR)
    icon = lambda pad, radius: (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">'
                                f'<rect width="1000" height="1000" rx="{radius}" fill="#ffffff"/>'
                                f'<g transform="translate({pad} {pad + (1000 - 2 * pad) * (1 - 747 / 814) / 2}) scale({(1000 - 2 * pad) / 814}) translate(-222 -51)">{sym}</g></svg>')
    renders = [('icon-512.png', icon(110, 220), 512, 512), ('icon-192.png', icon(110, 220), 192, 192),
               ('apple-touch-icon.png', icon(110, 0), 180, 180), ('icon-maskable-512.png', icon(190, 0), 512, 512),
               ('favicon-48.png', icon(40, 220), 48, 48), ('logo-horizontal.png', files['logo-horizontal.svg'], 640, 173)]
    script = """
const { chromium } = require('playwright');
(async () => {
  const jobs = JSON.parse(process.argv[1]);
  const b = await chromium.launch();
  for (const [file, svg, w, h] of jobs) {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    await p.setContent(`<html><body style="margin:0">${svg.replace('<svg ', `<svg width="${w}" height="${h}" `)}</body></html>`);
    await p.screenshot({ path: file, omitBackground: true });
    await p.close();
  }
  await b.close();
})();"""
    jobs = [[str(OUT / f), s, w, h] for f, s, w, h in renders]
    subprocess.run(['node', '-e', script, json.dumps(jobs)], cwd=ROOT / 'apps/web', check=True)
    for f in list(files) + [r[0] for r in renders]:
        print(f'{f:28} {(OUT / f).stat().st_size:>7} o')


if __name__ == '__main__':
    main()
