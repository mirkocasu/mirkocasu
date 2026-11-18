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
import math
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
    grid = [
        [" " if bg[y][x] else ramp[max(1, min(9, im.getpixel((x, y)) * 10 // 256))] for x in range(cols)]
        for y in range(rows)
    ]
    drop_specks(grid)
    lines = ["".join(r).rstrip() for r in grid]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def drop_specks(grid, min_size=4):
    """Blank out groups of fewer than min_size touching characters (8-neighbour), such as stray dots."""
    rows, cols = len(grid), len(grid[0])
    seen = [[False] * cols for _ in range(rows)]
    for y in range(rows):
        for x in range(cols):
            if grid[y][x] == " " or seen[y][x]:
                continue
            group, stack = [], [(x, y)]
            seen[y][x] = True
            while stack:
                cx, cy = stack.pop()
                group.append((cx, cy))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        a, b = cx + dx, cy + dy
                        if 0 <= a < cols and 0 <= b < rows and not seen[b][a] and grid[b][a] != " ":
                            seen[b][a] = True
                            stack.append((a, b))
            if len(group) < min_size:
                for gx, gy in group:
                    grid[gy][gx] = " "


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


# Colour themes: ASCII-art gradient (top, bottom), then header and accent colours for the
# light and the dark GitHub theme.
THEMES = {
    "blue": {"art": (BLUE, TEAL), "light": "#0969da", "dark": "#58a6ff"},
    "violet": {"art": ("#a371f7", "#6e40c9"), "light": "#8250df", "dark": "#a371f7"},
    "teal": {"art": ("#56d4dd", "#1b7c83"), "light": "#1b7c83", "dark": "#39c5cf"},
    "lava": {"art": ("#ffa657", "#c4432b"), "light": "#bc4c00", "dark": "#f0883e"},
}


def info_card(art, header, facts, theme, label, art_size=6.0):
    """ASCII art beside a system-info list (`user@host`, then dot-leader rows).

    Transparent background; text colours follow the viewer's light or dark theme.
    """
    t = THEMES[theme]
    W = 760
    a_lead = 2 * art_size * CHAR_W  # line height that keeps the art's pixels square
    size, lead = 12.5, 21
    n_chars = 60
    fx = W - n_chars * size * CHAR_W - 4
    top = 22
    parts = [f'<text x="{fx:.1f}" y="{top}" class="h">{esc(header)}</text>']
    rule_x = fx + (len(header) + 1) * size * CHAR_W
    parts.append(f'<line x1="{rule_x:.1f}" y1="{top - 4}" x2="{W - 4}" y2="{top - 4}" class="r"/>')
    y = top + lead
    for key, value, accent in facts:
        lab = f". {key}: "
        dots = n_chars - len(lab) - len(value) - 1
        if dots < 2:
            raise ValueError(f"{key}: value too long for {n_chars} columns")
        parts.append(
            f'<text x="{fx:.1f}" y="{y}"><tspan class="k">{esc(lab)}</tspan><tspan class="d">{"." * dots} </tspan>'
            f'<tspan class="{"v" if accent else "t"}">{esc(value)}</tspan></text>'
        )
        y += lead
    facts_h = y - lead + 12
    art_h = len(art) * a_lead + 8
    H = max(facts_h, art_h)
    if facts_h < H:  # centre the list beside taller art
        shift = (H - facts_h) / 2
        body_list = f'<g transform="translate(0 {shift:.1f})">' + "\n".join(parts) + "</g>"
    else:
        body_list = "\n".join(parts)
    art_w = max(len(r) for r in art) * art_size * CHAR_W
    ax = max(8, (fx - 24 - art_w) / 2)
    ay0 = (H - len(art) * a_lead) / 2
    ay = ay0 + art_size
    art_rows = []
    for row in art:
        art_rows.append(f'<text x="{ax:.1f}" y="{ay:.1f}" class="a">{esc(row)}</text>')
        ay += a_lead
    body = body_list + "\n" + "\n".join(art_rows)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H:.0f}" viewBox="0 0 {W} {H:.0f}" role="img" aria-label="{html.escape(label)}">
<title>{esc(label)}</title>
<defs>
  <linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="{ay0:.0f}" x2="0" y2="{ay0 + len(art) * a_lead:.0f}">
    <stop offset="0%" stop-color="{t["art"][0]}"/><stop offset="100%" stop-color="{t["art"][1]}"/>
  </linearGradient>
</defs>
<style>
  text {{ font-family: {FONT}; white-space: pre; font-size: {size}px; }}
  .a {{ fill: url(#g); font-size: {art_size}px; }}
  .h {{ fill: {t["light"]}; font-weight: 700; }}
  .r {{ stroke: #d1d9e0; }}
  .k {{ fill: #59636e; }}
  .d {{ fill: #c4ccd4; }}
  .t {{ fill: #1f2328; }}
  .v {{ fill: {t["light"]}; }}
  @media (prefers-color-scheme: dark) {{
    .h {{ fill: {t["dark"]}; }}
    .r {{ stroke: #3d444d; }}
    .k {{ fill: #9198a1; }}
    .d {{ fill: #3d444d; }}
    .t {{ fill: #e6edf3; }}
    .v {{ fill: {t["dark"]}; }}
  }}
</style>
{body}
</svg>
"""


def identity(portrait):
    return info_card(portrait, "mirkocasu@github", FACTS, "blue", "Mirko Casu: AI researcher and licensed psychologist")


# ---------------------------------------------------------------- project cards


def symbol_art(kind, cols=60, rows=32):
    """An original line-art symbol drawn with PIL, then turned into ASCII (brighter = denser)."""
    from PIL import Image, ImageDraw

    s = 10  # pixels per column; rows are twice as tall, so the drawing has square pixels
    W, H = cols * s, rows * 2 * s
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    cx, cy = W / 2, H / 2
    stroke = 26
    if kind == "film":  # a film frame with sprocket holes and a play button
        d.rounded_rectangle((30, 90, W - 30, H - 90), radius=40, outline=255, width=stroke)
        n = 8
        for i in range(n):  # sprocket holes inside the top and bottom edges
            x = 80 + i * (W - 160 - 34) / (n - 1)
            d.rectangle((x, 140, x + 34, 170), fill=255)
            d.rectangle((x, H - 170, x + 34, H - 140), fill=255)
        r = 92
        d.polygon([(cx - r * 0.55, cy - r), (cx - r * 0.55, cy + r), (cx + r * 0.95, cy)], fill=255)
    elif kind == "chat":  # a speech bubble with a heart
        top, bottom = 50, H - 150
        d.rounded_rectangle((30, top, W - 30, bottom), radius=90, outline=255, width=stroke)
        d.polygon([(120, bottom - stroke), (95, H - 40), (230, bottom - stroke)], fill=255)
        d.polygon([(120 + stroke, bottom - stroke * 2), (125, H - 110), (200, bottom - stroke * 2)], fill=0)
        hx, hy, hr = cx, (top + bottom) / 2 - 40, 62
        d.ellipse((hx - 2 * hr, hy - hr, hx, hy + hr), fill=255)
        d.ellipse((hx, hy - hr, hx + 2 * hr, hy + hr), fill=255)
        d.polygon([(hx - 2 * hr + 4, hy + 22), (hx + 2 * hr - 4, hy + 22), (hx, hy + 2.6 * hr)], fill=255)
    elif kind == "eye":  # an eye inside a viewfinder
        # the almond is two circular arcs that meet at the corners of the eye
        hw, h = W * 0.4, 150  # half width and half height of the almond
        R = (hw * hw + h * h) / (2 * h)
        t = math.degrees(math.asin((R - h) / R))
        d.arc((cx - R, cy - h, cx + R, cy - h + 2 * R), 180 + t, 360 - t, fill=255, width=stroke)
        d.arc((cx - R, cy + h - 2 * R, cx + R, cy + h), t, 180 - t, fill=255, width=stroke)
        d.ellipse((cx - 92, cy - 92, cx + 92, cy + 92), fill=255)
        d.ellipse((cx - 36, cy - 36, cx + 36, cy + 36), fill=0)
        d.ellipse((cx + 22, cy - 62, cx + 50, cy - 34), fill=0)  # highlight
        k, w, e = 110, 22, 24  # bracket arm length, width, margin
        for x0, y0, sx, sy in ((e, e, 1, 1), (W - e, e, -1, 1), (e, H - e, 1, -1), (W - e, H - e, -1, -1)):
            d.rectangle((min(x0, x0 + sx * k), min(y0, y0 + sy * w), max(x0, x0 + sx * k), max(y0, y0 + sy * w)), fill=255)
            d.rectangle((min(x0, x0 + sx * w), min(y0, y0 + sy * k), max(x0, x0 + sx * w), max(y0, y0 + sy * k)), fill=255)
    small = m.resize((cols, rows), Image.BOX)
    ramp = " .:;+=xX$&"
    out = []
    for y in range(rows):
        shade = 1 - 0.3 * y / rows  # brighter at the top, like a light from above
        row = ""
        for x in range(cols):
            v = small.getpixel((x, y)) / 255 * shade
            row += " " if v < 0.08 else ramp[max(1, min(9, round(v * 9)))]
        out.append(row.rstrip())
    return out


# name: (output file, art, colour theme, header, facts, image description)
PROJECTS = {
    "synthforensics": (
        "film",
        "violet",
        "synthforensics@neurips",
        [
            ("What", "benchmark for synthetic-video detection", False),
            ("Videos", "6,815 generated, people-centric", True),
            ("Finding", "detectors lose 29 AUC points on average", True),
            ("Venue", "NeurIPS 2026 · Evaluations & Datasets", False),
            ("Paper", "arXiv:2602.04939", True),
        ],
        "SynthForensics: a benchmark of 6,815 synthetic videos; detectors lose 29 AUC points on average",
    ),
    "chatbots": (
        "chat",
        "teal",
        "chatbots@review",
        [
            ("What", "scoping review of AI chatbots", False),
            ("Area", "mental health", False),
            ("Looks.at", "effectiveness · feasibility · applications", False),
            ("Cited.by", "UK Parliament POST · POSTnote 737", True),
            ("Venue", "Applied Sciences · 2024", False),
        ],
        "AI chatbots for mental health: a scoping review, cited by the UK Parliament POST",
    ),
    "deepfakes": (
        "eye",
        "lava",
        "deepfakes@iplab",
        [
            ("Paper", "GenAI Mirage · FSIDI 2024", False),
            ("Idea", "the impostor bias in deepfake detection", False),
            ("Mentioned.by", "INTERPOL · Project SynthWave", True),
            ("Workshop", "co-chair · DFF '25 @ ACM Multimedia", True),
            ("Challenge", "AADD-2025 · dataset committee", False),
        ],
        "Deepfake forensics: GenAI Mirage, mentioned by INTERPOL; DFF '25 workshop; AADD-2025 challenge",
    ),
}


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
    for name, (kind, theme, header, facts, label) in PROJECTS.items():
        (BUILD / f"card-{name}.svg").write_text(info_card(symbol_art(kind), header, facts, theme, label, art_size=6.6))
    names = ["banner.gif", "card-identity.svg"] + [f"card-{n}.svg" for n in PROJECTS]
    names = [n for n in names if (BUILD / n).exists()]
    print("wrote", ", ".join(publish(n) for n in names))


if __name__ == "__main__":
    main()
