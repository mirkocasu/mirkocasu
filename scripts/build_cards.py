#!/usr/bin/env python3
"""Build the images for the GitHub profile README.

Usage: python3 -I scripts/build_cards.py [--portrait IMAGE] [--sprite GIF]

Always rebuilds the identity card. Options:
  --portrait IMAGE  rebuild the ASCII portrait cached in assets/portrait.txt.
  --sprite GIF      rebuild the banner from an animated sprite GIF (now the shiny
                    Umbreon, 197.gif), with its original colours and no outline. The
                    sprite is not kept in this repo; without this option the published
                    banner is left as it is.

Images are built in assets/build/ (not committed) and published as
assets/<name>-<hash>.<ext>; the README links are updated to the new names.

Every image has a transparent background.
"""
import argparse
import hashlib
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
BUILD = ASSETS / "build"  # unhashed outputs, kept so the GIF need not be rebuilt each run

BLUE = "#2f8fd0"
TEAL = "#1fa3b0"
LAVA = "#ef7d32"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
CHAR_W = 0.602  # monospace advance width, in em

def esc(s):
    return html.escape(s, quote=False)


# ---------------------------------------------------------------- sprite banner


def sprite_banner(src, out, scale=3, vpad=80, hpad=40, outline=None):
    """Upscale an animated sprite with empty space around it, keeping its own frame timing.

    outline: an RGB colour for a one-pixel ring around the silhouette, or None.
    """
    from PIL import Image, ImageFilter, ImageSequence

    frames = []
    for f in ImageSequence.Iterator(Image.open(src)):
        im = f.convert("RGBA")
        if outline:
            ring = Image.new("RGBA", im.size, outline + (255,))
            ring.putalpha(im.getchannel("A").filter(ImageFilter.MaxFilter(3)))
            ring.alpha_composite(im)
            im = ring
        frames.append((im, f.info.get("duration") or 100))
    boxes = [im.getbbox() for im, _ in frames]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    size = ((box[2] - box[0]) * scale, (box[3] - box[1]) * scale)
    canvas_size = (size[0] + 2 * hpad, size[1] + 2 * vpad)
    images = []
    for im, _ in frames:
        c = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        c.alpha_composite(im.crop(box).resize(size, Image.NEAREST), (hpad, vpad))
        images.append(c)
    images[0].save(
        out, save_all=True, append_images=images[1:], duration=[d for _, d in frames], loop=0, disposal=2, optimize=True
    )
    return canvas_size


# ---------------------------------------------------------------- identity card


def ascii_portrait(src, cols=80, rows=46, bg_level=17, gamma=0.6):
    """The photo as ASCII art on an empty background.

    Gamma < 1 lifts the dark hair and clothes. Cells darker than bg_level that connect to the
    edge of the crop are background and stay blank, so only the person is drawn.
    """
    from collections import deque

    from PIL import Image, ImageOps

    im = Image.open(src).convert("L")
    w, h = im.size
    top, bottom = 0.02, 0.98
    height = (bottom - top) * h
    width = min(w, height * cols / (rows * 2))  # a character cell is twice as tall as it is wide
    left = (w - width) / 2
    im = im.crop((int(left), int(top * h), int(left + width), int(bottom * h)))
    raw = im.resize((cols, rows), Image.BOX)
    im = ImageOps.autocontrast(im, cutoff=1).point(lambda v: int(255 * (v / 255) ** gamma))
    im = im.resize((cols, rows), Image.LANCZOS)

    dark = lambda x, y: raw.getpixel((x, y)) < bg_level
    bg = [[False] * cols for _ in range(rows)]
    queue = deque(
        (x, y) for y in range(rows) for x in range(cols) if (x in (0, cols - 1) or y in (0, rows - 1)) and dark(x, y)
    )
    for x, y in queue:
        bg[y][x] = True
    while queue:
        x, y = queue.popleft()
        for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= a < cols and 0 <= b < rows and not bg[b][a] and dark(a, b):
                bg[b][a] = True
                queue.append((a, b))

    ramp = " .:;+=xX$&"
    return [
        "".join(" " if bg[y][x] else ramp[max(1, min(9, im.getpixel((x, y)) * 10 // 256))] for x in range(cols)).rstrip()
        for y in range(rows)
    ]


# Facts beside the portrait: (key, value, accent). Values are right-aligned after dot leaders.
FACTS = [
    ("Name", "Mirko Casu", False),
    ("Role", "AI researcher · licensed psychologist", False),
    ("PhD", "Computer Science · Univ. of Catania", False),
    ("Lab", "IPLab", False),
    ("Visiting", "EPFL MINTS · 2025–26", True),
    ("Focus", "LLMs & AI agents → mental health", True),
    ("Also", "deepfakes · synthetic media", False),
    ("Cited.by", "UK Parliament POST · INTERPOL", True),
    ("Open.Source", "datasets · challenges · apps", False),
    ("Stack", "Python · PyTorch · Hugging Face · MLX · Claude", False),
    ("Languages", "Italian · English", False),
    ("Location", "Italy", False),
    ("Off", "photography · gaming", False),
]


def identity(portrait):
    """Portrait beside a system-info list, on a transparent background; colours follow the theme."""
    W = 760
    a_size = 6.0  # portrait font size
    a_lead = 2 * a_size * CHAR_W  # line height: square pixels for the portrait
    size, lead = 12.5, 21  # facts font size and line height
    n_chars = 60
    fx = W - n_chars * size * CHAR_W - 4
    top = 22
    parts = []
    # header: user@host and a rule to the right edge
    head = "mirkocasu@github"
    parts.append(f'<text x="{fx:.1f}" y="{top}" class="h">{head}</text>')
    rule_x = fx + (len(head) + 1) * size * CHAR_W
    parts.append(f'<line x1="{rule_x:.1f}" y1="{top - 4}" x2="{W - 4}" y2="{top - 4}" class="r"/>')
    y = top + lead
    for key, value, accent in FACTS:
        label = f". {key}: "
        dots = n_chars - len(label) - len(value) - 1
        if dots < 2:
            raise ValueError(f"{key}: value too long for {n_chars} columns")
        parts.append(
            f'<text x="{fx:.1f}" y="{y}"><tspan class="k">{esc(label)}</tspan><tspan class="d">{"." * dots} </tspan>'
            f'<tspan class="{"v" if accent else "t"}">{esc(value)}</tspan></text>'
        )
        y += lead
    H = max(y - lead + 12, top + len(portrait) * a_lead)
    ay = (H - len(portrait) * a_lead) / 2 + a_size
    py0 = ay - a_size
    for row in portrait:
        parts.append(f'<text x="8" y="{ay:.1f}" class="a">{esc(row)}</text>')
        ay += a_lead
    body = "\n".join(parts)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H:.0f}" viewBox="0 0 {W} {H:.0f}" role="img" aria-label="Mirko Casu: AI researcher and licensed psychologist">
<title>Mirko Casu</title>
<defs>
  <linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="{py0:.0f}" x2="0" y2="{H:.0f}">
    <stop offset="0%" stop-color="{BLUE}"/><stop offset="100%" stop-color="{TEAL}"/>
  </linearGradient>
</defs>
<style>
  text {{ font-family: {FONT}; white-space: pre; font-size: {size}px; }}
  .a {{ fill: url(#g); font-size: {a_size}px; }}
  .h {{ fill: {BLUE}; font-weight: 700; }}
  .r {{ stroke: #d1d9e0; }}
  .k {{ fill: #59636e; }}
  .d {{ fill: #c4ccd4; }}
  .t {{ fill: #1f2328; }}
  .v {{ fill: {BLUE}; }}
  @media (prefers-color-scheme: dark) {{
    .r {{ stroke: #3d444d; }}
    .k {{ fill: #9198a1; }}
    .d {{ fill: #3d444d; }}
    .t {{ fill: #e6edf3; }}
    .v {{ fill: #58a6ff; }}
  }}
</style>
{body}
</svg>
"""


def publish(name):
    """Copy assets/build/<name> to assets/<stem>-<hash><ext> and point the README at it.

    GitHub's CDN caches each image URL for minutes, and its /raw/ redirect drops query
    strings, so a new file name is the only reliable way to show a new version at once.
    """
    src = BUILD / name
    stem, ext = src.stem, src.suffix
    data = src.read_bytes()
    final = f"{stem}-{hashlib.sha256(data).hexdigest()[:8]}{ext}"
    for old in ASSETS.glob(f"{stem}-*{ext}"):
        if old.name != final:
            old.unlink()
    (ASSETS / final).write_bytes(data)
    readme = ROOT / "README.md"
    pattern = rf'(src|srcset)="assets/{re.escape(stem)}(?:-[0-9a-f]{{8}})?{re.escape(ext)}"'
    readme.write_text(re.sub(pattern, rf'\1="assets/{final}"', readme.read_text()))
    return final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portrait")
    ap.add_argument("--sprite")
    args = ap.parse_args()
    ASSETS.mkdir(exist_ok=True)
    cache = ASSETS / "portrait.txt"
    if args.portrait:
        portrait = ascii_portrait(args.portrait)
        cache.write_text("\n".join(portrait) + "\n")
    else:
        portrait = cache.read_text().splitlines()
    BUILD.mkdir(exist_ok=True)
    if args.sprite:
        sprite_banner(args.sprite, BUILD / "banner.gif")
    (BUILD / "card-identity.svg").write_text(identity(portrait))
    names = [n for n in ("banner.gif", "card-identity.svg") if (BUILD / n).exists()]
    print("wrote", ", ".join(publish(n) for n in names))


if __name__ == "__main__":
    main()
