"""Polices servies par l'application : Poppins 400, 500 et 700 (SIL Open Font License), seule famille du design system.

Sortie : apps/web/public/fonts/poppins-{400,500,700}.woff, sous-ensemble latin (français, anglais, espagnol).
Usage : python3 tools/brand/build_assets.py
Les logos et icônes sont générés par tools/brand/build_logo.py, d'après le logo vectoriel du design system.
"""
from pathlib import Path
from fontTools import subset

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "apps/web/public/fonts"
FONTS.mkdir(parents=True, exist_ok=True)

UNICODES = "U+0020-007E,U+00A0-00FF,U+0152-0153,U+2013-2014,U+2018-201E,U+2026,U+20AC,U+2192,U+00D7"
for weight, file in [(400, "Poppins-Regular.ttf"), (500, "Poppins-Medium.ttf"), (700, "Poppins-Bold.ttf")]:
    subset.main([f"/usr/share/fonts/truetype/google-fonts/{file}", f"--unicodes={UNICODES}", "--flavor=woff",
                 "--layout-features=kern,liga,tnum,lnum", f"--output-file={FONTS / f'poppins-{weight}.woff'}"])

for p in sorted(FONTS.iterdir()):
    print(f"{p.relative_to(ROOT)}  {p.stat().st_size // 1024} Ko")
