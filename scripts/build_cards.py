#!/usr/bin/env python3
"""Build the SVG banner and cards for the GitHub profile README.

Usage: python3 scripts/build_cards.py [path/to/portrait.(jpg|png|webp)]
Writes assets/banner.svg and assets/card-*.svg. The portrait is optional:
without it, the identity card keeps the ASCII portrait already in assets/portrait.txt.
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


def typed_line(x, y, text, cls, start, cps=28, size=13, idx=0):
    """A line that types itself in once, using a discrete SMIL clip animation."""
    # The clip starts at full width, so the text is visible where SMIL is not supported.
    # The animation runs from t=0: width 0 until `start`, then one character per step.
    n = len(text)
    char_px = size * CHAR_W
    typing = max(n / cps, 0.2)
    total = start + typing
    widths = [0.0] + [i * char_px for i in range(n + 1)]
    times = [0.0] + [(start + typing * i / n) / total for i in range(n + 1)]
    values = ";".join(f"{w:.1f}" for w in widths)
    key_times = ";".join(f"{t:.4f}" for t in times)
    full = (n + 1) * char_px
    return f"""<clipPath id="c{idx}"><rect x="{x}" y="{y - size}" width="{full:.1f}" height="{size + 6}">
  <animate attributeName="width" begin="0s" dur="{total:.2f}s" values="{values}" keyTimes="{key_times}" calcMode="discrete" fill="freeze"/>
</rect></clipPath>
<text x="{x}" y="{y}" class="{cls}" clip-path="url(#c{idx})">{esc(text)}</text>""", total


def banner():
    W, H = 900, 240
    lines = [
        ("$ ", "whoami", None),
        ("", "Mirko Casu · AI researcher · licensed clinical psychologist", "h"),
        ("$ ", "cat focus.txt", None),
        ("", "language models · AI agents · mental health · human safety", "t"),
        ("$ ", "echo $HOME", None),
        ("", "Catania, Sicily 🌋", "t"),
    ]
    parts, t, y, idx = [], 0.6, 62, 0
    for prompt, text, cls in lines:
        x = 28
        if prompt:
            parts.append(f'<text x="{x}" y="{y}" class="p">{prompt}</text>')
            x += len(prompt) * 13 * CHAR_W
            line, t = typed_line(x, y, text, "t", t, cps=14, idx=idx)
        else:
            size = 15 if cls == "h" else 13
            line, t = typed_line(x, y, text, cls, t, cps=40, size=size, idx=idx)
        parts.append(line)
        idx += 1
        t += 0.35
        y += 24 if prompt else 30
    # blinking cursor after the last line
    parts.append(
        f'<text x="28" y="{y}" class="p">$ </text>'
        f'<rect x="{28 + 2 * 13 * CHAR_W:.1f}" y="{y - 12}" width="8" height="15" fill="{LAVA}">'
        f'<animate attributeName="opacity" begin="{t:.2f}s" values="1;0" dur="1.1s" calcMode="discrete" repeatCount="indefinite"/></rect>'
    )
    return window(W, H, "mirko@catania: ~", "\n".join(parts))


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
    ASSETS.mkdir(exist_ok=True)
    cache = ASSETS / "portrait.txt"
    if len(sys.argv) > 1:
        portrait = ascii_portrait(sys.argv[1])
        cache.write_text("\n".join(portrait) + "\n")
    else:
        portrait = cache.read_text().splitlines()
    (ASSETS / "banner.svg").write_text(banner())
    (ASSETS / "card-identity.svg").write_text(identity(portrait))
    for fname, (title, cmd, lines) in CARDS.items():
        (ASSETS / fname).write_text(project(title, cmd, lines))
    print("wrote", ", ".join(sorted(p.name for p in ASSETS.glob("*.svg"))))


if __name__ == "__main__":
    main()
