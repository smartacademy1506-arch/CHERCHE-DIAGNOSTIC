"""Génère les fichiers de marque servis par l'application à partir des logos fournis par l'utilisateur.

Sources (fournies par l'utilisateur le 12/11/2026) : assets/brand/*-source.png
Sorties : apps/web/public/brand/ (logos recadrés et allégés, icônes PWA) et apps/web/public/fonts/ (Poppins, SIL OFL).
Usage : python3 tools/brand/build_assets.py
"""
from pathlib import Path
from PIL import Image, ImageChops
from fontTools import subset

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "assets/brand"
OUT = ROOT / "apps/web/public/brand"
FONTS = ROOT / "apps/web/public/fonts"
OUT.mkdir(parents=True, exist_ok=True)
FONTS.mkdir(parents=True, exist_ok=True)


def trim(img: Image.Image, pad: int = 0) -> Image.Image:
    """Recadre sur le contenu non blanc."""
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg).convert("L").point(lambda v: 255 if v > 24 else 0)
    x0, y0, x1, y1 = diff.getbbox()
    return rgb.crop((max(0, x0 - pad), max(0, y0 - pad), min(rgb.width, x1 + pad), min(rgb.height, y1 + pad)))


def to_alpha(img: Image.Image) -> Image.Image:
    """Rend le fond blanc transparent en conservant l'anticrénelage (alpha = écart au blanc)."""
    rgb = img.convert("RGB")
    px = rgb.load()
    out = Image.new("RGBA", rgb.size)
    po = out.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            r, g, b = px[x, y]
            a = 255 - min(r, g, b)
            if a <= 6:
                po[x, y] = (0, 0, 0, 0)
                continue
            k = 255 / a
            po[x, y] = (max(0, min(255, round(255 - (255 - r) * k))), max(0, min(255, round(255 - (255 - g) * k))),
                        max(0, min(255, round(255 - (255 - b) * k))), a)
    return out


def save(img: Image.Image, name: str, width: int) -> None:
    h = round(img.height * width / img.width)
    img.resize((width, h), Image.LANCZOS).save(OUT / name, optimize=True)


horizontal = Image.open(SRC / "logo-horizontal-source.png")
lockup = to_alpha(trim(horizontal, 8))
save(lockup, "logo-horizontal.png", 640)
mark = to_alpha(trim(horizontal.crop((0, 0, 470, horizontal.height)), 8))
save(mark, "logo-mark.png", 192)

icon = trim(Image.open(SRC / "icone-app-source.png"), 0)
side = max(icon.size)
square = Image.new("RGB", (side, side), (255, 255, 255))
square.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2))
for size, name in [(512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png"), (48, "favicon-48.png")]:
    square.resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)
# Icône « maskable » : le dessin tient dans la zone sûre (80 %) sur fond blanc.
inner = round(512 * 0.78)
mask = Image.new("RGB", (512, 512), (255, 255, 255))
mask.paste(square.resize((inner, inner), Image.LANCZOS), ((512 - inner) // 2, (512 - inner) // 2))
mask.save(OUT / "icon-maskable-512.png", optimize=True)

# Poppins (SIL Open Font License), sous-ensemble latin pour le français, l'anglais et l'espagnol.
UNICODES = "U+0020-007E,U+00A0-00FF,U+0152-0153,U+2013-2014,U+2018-201E,U+2026,U+20AC,U+2192,U+00D7"
for weight, file in [(500, "Poppins-Medium.ttf"), (700, "Poppins-Bold.ttf")]:
    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = ["kern", "liga", "tnum", "lnum"]
    subset.main([f"/usr/share/fonts/truetype/google-fonts/{file}", f"--unicodes={UNICODES}", "--flavor=woff",
                 "--layout-features=kern,liga,tnum,lnum", f"--output-file={FONTS / f'poppins-{weight}.woff'}"])

for p in sorted(list(OUT.iterdir()) + list(FONTS.iterdir())):
    print(f"{p.relative_to(ROOT)}  {p.stat().st_size // 1024} Ko")
