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


def ascii_portrait(src):
    from PIL import Image, ImageOps

    im = Image.open(src).convert("L")
    w, h = im.size
    box = (int(w * 0.22), int(h * 0.06), int(w * 0.78), int(h * 0.80))
    im = ImageOps.autocontrast(im.crop(box), cutoff=2)
    cols, rows = 56, 36
    im = im.resize((cols, rows))
    ramp = " .:-=+*#%@"
    return [
        "".join(ramp[min(9, im.getpixel((x, y)) * 10 // 256)] for x in range(cols)).rstrip()
        for y in range(rows)
    ]


def identity(portrait):
    """Portrait and key facts on a transparent background; text colours follow the theme."""
    W, H = 760, 300
    parts = []
    y = 20
    for row in portrait:
        parts.append(f'<text x="0" y="{y:.1f}" class="a">{esc(row)}</text>')
        y += 7.6
    x = 240
    parts.append(f'<text x="{x}" y="40" class="h">Mirko Casu</text>')
    rows = [
        ("role", "AI researcher · clinical psychologist"),
        ("phd", "Computer Science · Univ. of Catania"),
        ("lab", "IPLab · visiting EPFL MINTS (2025–26)"),
        ("focus", "LLMs & AI agents → mental health,"),
        (None, "human safety, synthetic media"),
        ("stack", "Python · PyTorch · Hugging Face · MLX"),
        ("speaks", "Italian · English · French"),
        ("off", "photography · gaming"),
    ]
    y = 84
    vx = x + 8 * 14 * CHAR_W
    for k, v in rows:
        if k:
            parts.append(f'<text x="{x}" y="{y}" class="k">{esc(k)}</text>')
        parts.append(f'<text x="{vx:.1f}" y="{y}" class="{"t" if k else "m"}">{esc(v)}</text>')
        y += 24
    body = "\n".join(parts)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Mirko Casu">
<title>Mirko Casu</title>
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{BLUE}"/><stop offset="55%" stop-color="{TEAL}"/><stop offset="100%" stop-color="{LAVA}"/>
  </linearGradient>
</defs>
<style>
  text {{ font-family: {FONT}; white-space: pre; }}
  .t {{ fill: #1f2328; font-size: 14px; }}
  .m {{ fill: #59636e; font-size: 14px; }}
  .k {{ fill: {TEAL}; font-size: 14px; font-weight: 700; }}
  .h {{ fill: url(#g); font-size: 22px; font-weight: 700; }}
  .a {{ fill: url(#g); font-size: 6.4px; }}
  @media (prefers-color-scheme: dark) {{
    .t {{ fill: #e6edf3; }}
    .m {{ fill: #9198a1; }}
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
