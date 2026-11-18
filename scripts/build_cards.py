#!/usr/bin/env python3
"""Build the SVG banner and cards for the GitHub profile README.

Usage: python3 scripts/build_cards.py [--portrait IMAGE] [--unown DIR]
Writes assets/card-*.svg and, with --unown, assets/banner.svg.
--portrait rebuilds the ASCII portrait cached in assets/portrait.txt.
--unown points to a folder with the Unown GIFs 201-m/i/r/k/o.gif. The GIFs are
not kept in this repo; without --unown the existing banner is left as it is.
"""
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# Palette: the website's blue, a teal, and a lava orange accent.
BG = "#0d1117"
PANEL = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
BLUE = "#3fa7d6"
TEAL = "#2bb3c0"
LAVA = "#f2994a"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
CHAR_W = 0.602  # monospace advance width, in em


def esc(s):
    return html.escape(s, quote=False)


def window(width, height, title, body):
    """A terminal window with title bar, traffic lights and a body group."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title>
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{BLUE}"/><stop offset="55%" stop-color="{TEAL}"/><stop offset="100%" stop-color="{LAVA}"/>
  </linearGradient>
</defs>
<style>
  text {{ font-family: {FONT}; white-space: pre; }}
  .t {{ fill: {TEXT}; font-size: 13px; }}
  .m {{ fill: {MUTED}; font-size: 13px; }}
  .k {{ fill: {TEAL}; font-size: 13px; font-weight: 700; }}
  .h {{ fill: url(#g); font-size: 15px; font-weight: 700; }}
  .p {{ fill: {LAVA}; font-size: 13px; font-weight: 700; }}
  .a {{ fill: url(#g); font-size: 6.4px; }}
  .bar {{ fill: {MUTED}; font-size: 11px; }}
</style>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
<rect x="0.5" y="0.5" width="{width - 1}" height="28" rx="10" fill="{PANEL}"/>
<rect x="0.5" y="18" width="{width - 1}" height="11" fill="{PANEL}"/>
<line x1="0.5" y1="28.5" x2="{width - 0.5}" y2="28.5" stroke="{BORDER}"/>
<circle cx="18" cy="14.5" r="5" fill="#ff5f57"/><circle cx="34" cy="14.5" r="5" fill="#febc2e"/><circle cx="50" cy="14.5" r="5" fill="#28c840"/>
<text x="{width / 2}" y="18.5" text-anchor="middle" class="bar">{esc(title)}</text>
{body}
</svg>
"""


def mix(c1, c2, t):
    """Blend two #rrggbb colours: t=0 gives c1, t=1 gives c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def gif_frames(path):
    """Frames of a palette GIF as (pixel rows of palette indices, duration in ms)."""
    from PIL import Image, ImageSequence

    im = Image.open(path)
    out = []
    for f in ImageSequence.Iterator(im):
        f = f.convert("P") if f.mode != "P" else f
        w, h = f.size
        px = f.load()
        out.append(([[px[x, y] for x in range(w)] for y in range(h)], f.info.get("duration") or 100))
    return out


def pixel_rects(rows, colours, x0, y0):
    """Horizontal runs of same-colour pixels as <rect>s; index 0 is transparent."""
    out = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            c = row[x]
            run = 1
            while x + run < len(row) and row[x + run] == c:
                run += 1
            if c in colours:
                out.append(f'<rect x="{x - x0}" y="{y - y0}" width="{run}" height="1" fill="{colours[c]}"/>')
            x += run
    return "".join(out)


def banner(unown_dir):
    """Five floating Unown spelling MIRKO, each playing its own sprite animation."""
    word = "mirko"
    W, H = 900, 272
    scale = 3
    letter_colours = [BLUE, TEAL, "#7ee2b8", "#f6d365", LAVA]
    letters = []
    for ch in word:
        frames = gif_frames(Path(unown_dir) / f"201-{ch}.gif")
        xs = [x for rows, _ in frames for row in rows for x, c in enumerate(row) if c]
        ys = [y for rows, _ in frames for y, row in enumerate(rows) if any(row)]
        letters.append((frames, min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
    gap = 40
    total_w = sum(w for *_, w, _ in letters) * scale + gap * (len(word) - 1)
    max_h = max(h for *_, h in letters) * scale
    x = (W - total_w) / 2
    top = 62
    defs, body = [], []
    for i, ((frames, x0, y0, w, h), col) in enumerate(zip(letters, letter_colours)):
        colours = {1: col, 2: mix(col, BG, 0.45), 3: mix(col, TEXT, 0.35), 4: TEXT}
        cycle = sum(d for _, d in frames) / 1000
        frame_svg, t = [], 0.0
        uniq = {}
        for j, (rows, d) in enumerate(frames):
            key = tuple(map(tuple, rows))
            if key not in uniq:
                uniq[key] = f"u{i}f{len(uniq)}"
                defs.append(f'<g id="{uniq[key]}">{pixel_rects(rows, colours, x0, y0)}</g>')
            s, e = t / cycle, (t + d / 1000) / cycle
            t += d / 1000
            if j == 0:
                anim = f'values="inline;none" keyTimes="0;{e:.4f}"'
            elif j == len(frames) - 1:
                anim = f'values="none;inline" keyTimes="0;{s:.4f}"'
            else:
                anim = f'values="none;inline;none" keyTimes="0;{s:.4f};{e:.4f}"'
            disp = "" if j == 0 else ' display="none"'
            # the sprite animation starts once the letter has landed
            frame_svg.append(
                f'<use href="#{uniq[key]}"{disp}><animate attributeName="display" {anim} '
                f'dur="{cycle:.2f}s" begin="{1.2 + 0.3 * i:.2f}s" calcMode="discrete" repeatCount="indefinite"/></use>'
            )
        lx = x
        ly = top + (max_h - h * scale) / 2
        delay = 0.25 * i
        bob = 2.6 + 0.35 * i
        body.append(
            f'<ellipse cx="{lx + w * scale / 2:.1f}" cy="{top + max_h + 22}" rx="{w * scale * 0.38:.1f}" ry="4" fill="{col}" opacity="0.18">'
            f'<animate attributeName="rx" values="{w * scale * 0.38:.1f};{w * scale * 0.28:.1f};{w * scale * 0.38:.1f}" dur="{bob:.2f}s" '
            f'begin="{delay + 0.8:.2f}s" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1" repeatCount="indefinite"/></ellipse>'
            f'<g transform="translate({lx:.1f} {ly:.1f})">'
            f'<g><animateTransform attributeName="transform" type="translate" values="0 -24;0 0" dur="0.7s" begin="{delay:.2f}s" '
            f'calcMode="spline" keySplines="0.2 0.8 0.3 1" fill="freeze"/>'
            f'<animate attributeName="opacity" values="0;1" dur="0.5s" begin="{delay:.2f}s" fill="freeze"/>'
            f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -8;0 0" dur="{bob:.2f}s" '
            f'begin="{delay + 0.8:.2f}s" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1" repeatCount="indefinite"/>'
            f'<g transform="scale({scale})" shape-rendering="crispEdges">{"".join(frame_svg)}</g></g></g></g>'
        )
        x += w * scale + gap
    ty = top + max_h + 64
    body.append(f'<text x="{W / 2}" y="{ty}" text-anchor="middle" class="h" style="font-size:22px">Mirko Casu</text>')
    body.append(
        f'<text x="{W / 2}" y="{ty + 26}" text-anchor="middle" class="m">'
        "AI researcher · licensed clinical psychologist · Catania, Sicily</text>"
    )
    svg = window(W, H, "unown — mirko", "\n".join(body))
    return svg.replace("</defs>", "".join(defs) + "\n</defs>", 1)


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


def kv_rows(x, y, rows, key_w=10):
    out = []
    for k, v in rows:
        if k is None:
            out.append(f'<text x="{x}" y="{y}" class="m">{esc(v)}</text>')
        else:
            out.append(
                f'<text x="{x}" y="{y}" class="k">{esc(k)}</text>'
                f'<text x="{x + key_w * 13 * CHAR_W:.1f}" y="{y}" class="t">{esc(v)}</text>'
            )
        y += 21
    return out, y


def identity(portrait):
    W, H = 780, 330
    parts = []
    y = 46
    for row in portrait:
        parts.append(f'<text x="18" y="{y:.1f}" class="a">{esc(row)}</text>')
        y += 7.6
    x = 250
    parts.append(f'<text x="{x}" y="56" class="h">mirko@catania</text>')
    parts.append(f'<text x="{x}" y="74" class="m">{"─" * 30}</text>')
    rows = [
        ("role", "AI researcher · clinical psychologist"),
        ("phd", "Computer Science · Univ. of Catania"),
        ("lab", "IPLab · visiting EPFL MINTS (2025–26)"),
        ("focus", "LLMs & AI agents → mental health,"),
        (None, "          human safety, synthetic media"),
        ("stack", "Python · PyTorch · Hugging Face · MLX"),
        ("speaks", "Italian · English · French"),
        ("off", "photography · gaming"),
    ]
    kv, y = kv_rows(x, 100, rows, key_w=8)
    parts += kv
    # palette swatches, like a system-info tool
    sx = x
    for c in (BLUE, TEAL, "#7ee2b8", "#f6d365", LAVA, "#e5534b", MUTED, TEXT):
        parts.append(f'<rect x="{sx}" y="{y + 2}" width="22" height="12" rx="2" fill="{c}"/>')
        sx += 26
    return window(W, H, "neofetch — mirko", "\n".join(parts))


def project(name, cmd, lines):
    W = 780
    H = 72 + 21 * len(lines) + 14
    parts = [f'<text x="24" y="56" class="p">$ </text><text x="{24 + 2 * 13 * CHAR_W:.1f}" y="56" class="t">{esc(cmd)}</text>']
    kv, _ = kv_rows(24, 84, lines, key_w=10)
    parts += kv
    return window(W, H, name, "\n".join(parts))


CARDS = {
    "card-synthforensics.svg": (
        "synthforensics — NeurIPS 2026",
        "synthforensics --summary",
        [
            ("what", "benchmark of people-centric synthetic videos"),
            ("size", "6,815 generated videos"),
            ("finding", "detectors lose 29 AUC points on average"),
            ("venue", "NeurIPS 2026 · Evaluations & Datasets Track"),
            ("paper", "arXiv:2602.04939"),
        ],
    ),
    "card-chatbots.svg": (
        "chatbots-mental-health — Applied Sciences 2024",
        "review --question 'do AI chatbots help?'",
        [
            ("what", "scoping review of AI chatbots for mental health"),
            ("covers", "effectiveness · feasibility · applications"),
            ("impact", "cited by UK Parliament POST (PN 737)"),
            ("venue", "Applied Sciences, 2024"),
        ],
    ),
    "card-deepfake.svg": (
        "deepfake-forensics",
        "ls ~/deepfake-forensics",
        [
            ("paper", "GenAI Mirage: the impostor bias in deepfake"),
            (None, "          detection · FSIDI 2024"),
            ("impact", "mentioned by INTERPOL (Project SynthWave)"),
            ("workshop", "co-chair, DFF '25 · ACM Multimedia 2025"),
            ("challenge", "dataset committee, AADD-2025"),
        ],
    ),
}


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--portrait")
    ap.add_argument("--unown")
    args = ap.parse_args()
    ASSETS.mkdir(exist_ok=True)
    cache = ASSETS / "portrait.txt"
    if args.portrait:
        portrait = ascii_portrait(args.portrait)
        cache.write_text("\n".join(portrait) + "\n")
    else:
        portrait = cache.read_text().splitlines()
    if args.unown:
        (ASSETS / "banner.svg").write_text(banner(args.unown))
    (ASSETS / "card-identity.svg").write_text(identity(portrait))
    for fname, (title, cmd, lines) in CARDS.items():
        (ASSETS / fname).write_text(project(title, cmd, lines))
    print("wrote", ", ".join(sorted(p.name for p in ASSETS.glob("*.svg"))))


if __name__ == "__main__":
    main()
