#!/usr/bin/env python3
"""
Generates a custom, animated SVG banner (dark + light) for the GitHub profile README.

Design:
  left  ─ wordmark "ANADI" (solid accent) / "TRIPATHI" (outline) / handle line
  right ─ terminal window that types itself out, forever, on a loop

Tech notes (why it never breaks):
  * Pure declarative SVG + SMIL only. No <style>, no <script>, no external fonts.
    That means it survives GitHub's camo proxy and works inside <img> tags.
  * Text renders with natural kerning (one <text> per line, no per-glyph
    positioning), and the typewriter effect is done with a reveal mask
    (a rect in the terminal's background colour whose width shrinks in discrete
    steps) plus a block cursor that walks along. No font-metric guesswork on the
    glyphs themselves, so it looks identical in every browser / OS.

Usage:
    python3 scripts/gen_banner.py             # writes assets/banner-{dark,light}.svg
    python3 scripts/gen_banner.py --preview   # also writes fully-visible static copies to /tmp
"""

import argparse
import os

W, H = 1200, 336
CARD_X, CARD_Y = 6, 6
CARD_W, CARD_H = W - 12, H - 12

# ── timeline (seconds) ────────────────────────────────────────────────────────
CYCLE = 15.0          # one full loop
T_START = 0.9         # first character appears
CHAR_DELAY = 0.033    # typing speed, per character
LINE_PAUSE = 0.34     # pause between commands
FADE_AT = 12.4        # terminal fades out here
FADE_DUR = 0.7

MONO = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'DejaVu Sans Mono', 'Liberation Mono', monospace")

# (prompt, prompt colour key, line segments [(colour key, text)])
LINES = [
    ("$", "cyan",  [("blue", " whoami")]),
    ("",  None,    [("text", " anadi tripathi"), ("dim", "  ·  "), ("text", "18"),
                    ("dim", "  ·  "), ("text", "lucknow, india")]),
    ("$", "cyan",  [("blue", " cat roles.txt")]),
    ("",  None,    [("text", " developer"), ("dim", "  ·  "), ("text", "automation"),
                    ("dim", "  ·  "), ("text", "ai / ml"), ("dim", "  ·  "),
                    ("text", "cybersecurity")]),
    ("$", "cyan",  [("blue", " ./status --now")]),
    ("",  None,    [("green", " dual degree: bca + bs data science"),
                    ("muted", " @ iit madras")]),
]

TERM_X, TERM_Y, TERM_W, TERM_H = 592, 52, 570, 232
TERM_HEAD = 30
FS = 15.0                 # terminal font size
LH = 26.0                 # line height
ADV = FS * 0.60           # nominal monospace advance, used only for mask/cursor maths

PALETTE = {
    "dark": {
        "card_a": "#0d1117", "card_b": "#0a0e15", "border": "#1d2635",
        "term_bg": "#080b11", "term_border": "#1b2434", "term_head": "#101722",
        "grid": "#161d2b",
        "text": "#c0caf5", "muted": "#6b7a99", "dim": "#3c4860",
        "title": "#525c78",
        "blue": "#7aa2f7", "purple": "#bb9af7", "cyan": "#7dcfff",
        "green": "#9ece6a", "red": "#f7768e",
        "outline": "#39465f", "glow": "#7aa2f7",
    },
    "light": {
        "card_a": "#ffffff", "card_b": "#f6f8fe", "border": "#dbe2f0",
        "term_bg": "#f8fafd", "term_border": "#dbe2f0", "term_head": "#eef2fa",
        "grid": "#e9eefa",
        "text": "#1f2937", "muted": "#5b6b85", "dim": "#9aa8c2",
        "title": "#8b9ab5",
        "blue": "#2b5bd7", "purple": "#7c3aed", "cyan": "#0b7285",
        "green": "#2f9e44", "red": "#e03131",
        "outline": "#a9b6cd", "glow": "#2b5bd7",
    },
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def line_text(prompt, segments) -> str:
    return (prompt or "") + "".join(t for _, t in segments)


def build(theme: str, preview: bool = False) -> str:
    p = PALETTE[theme]
    o = []
    a = o.append

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'role="img" aria-label="Anadi Tripathi, developer, AI and automation">')
    a('<defs>')
    a(f'<linearGradient id="cardbg" x1="0" y1="0" x2="0" y2="1">'
      f'<stop offset="0" stop-color="{p["card_a"]}"/>'
      f'<stop offset="1" stop-color="{p["card_b"]}"/></linearGradient>')
    a(f'<radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">'
      f'<stop offset="0" stop-color="{p["glow"]}" stop-opacity="0.16"/>'
      f'<stop offset="1" stop-color="{p["glow"]}" stop-opacity="0"/></radialGradient>')
    a(f'<pattern id="dots" width="16" height="16" patternUnits="userSpaceOnUse">'
      f'<circle cx="1" cy="1" r="1" fill="{p["grid"]}"/></pattern>')
    a('</defs>')
    assert 'url(#name)' not in "".join(o), "stale gradient reference"

    # ── card ──────────────────────────────────────────────────────────────
    a(f'<rect x="{CARD_X}" y="{CARD_Y}" width="{CARD_W}" height="{CARD_H}" rx="18" '
      f'fill="url(#cardbg)" stroke="{p["border"]}"/>')
    a(f'<rect x="{CARD_X}" y="{CARD_Y}" width="{CARD_W}" height="{CARD_H}" rx="18" fill="url(#dots)"/>')
    drift = ('' if preview else
             '<animateTransform attributeName="transform" type="translate" '
             'values="0 0; 14 -10; -6 8; 0 0" keyTimes="0;0.35;0.7;1" dur="19s" repeatCount="indefinite"/>')
    a('<g>')
    a(f'<ellipse cx="250" cy="140" rx="320" ry="190" fill="url(#glow)"/>')
    a(f'<ellipse cx="1020" cy="260" rx="300" ry="180" fill="url(#glow)"/>')
    a(drift)
    a('</g>')

    # ── left: wordmark ────────────────────────────────────────────────────
    a(f'<text x="54" y="138" font-family="{MONO}" font-size="88" font-weight="700" '
      f'letter-spacing="-1.5" fill="{p["blue"]}">ANADI</text>')
    a(f'<text x="54" y="218" font-family="{MONO}" font-size="88" font-weight="700" '
      f'letter-spacing="-1.5" fill="none" stroke="{p["outline"]}" stroke-width="1.4">TRIPATHI</text>')

    dot_pulse = ('' if preview else
                 '<animate attributeName="opacity" values="1;0.15;1" dur="2.4s" repeatCount="indefinite"/>')
    a(f'<circle cx="58" cy="249" r="4" fill="{p["green"]}">{dot_pulse}</circle>')
    a(f'<text x="72" y="254" font-family="{MONO}" font-size="13.5" letter-spacing="1.5" '
      f'fill="{p["muted"]}">@yash-tripath1 · solo developer · co-founder @ glymph studio</text>')

    # ── right: terminal (chrome + typed lines + masks + cursor) ──────────
    a('<g id="terminal">')
    a(f'<rect x="{TERM_X+2}" y="{TERM_Y+5}" width="{TERM_W}" height="{TERM_H}" rx="12" '
      f'fill="#000" opacity="0.22"/>')
    a(f'<rect x="{TERM_X}" y="{TERM_Y}" width="{TERM_W}" height="{TERM_H}" rx="12" '
      f'fill="{p["term_bg"]}" stroke="{p["term_border"]}"/>')
    a(f'<path d="M{TERM_X} {TERM_Y+12} a12 12 0 0 1 12 -12 h{TERM_W-24} a12 12 0 0 1 12 12 v18 h-{TERM_W} z" '
      f'fill="{p["term_head"]}"/>')
    a(f'<line x1="{TERM_X}" y1="{TERM_Y+TERM_HEAD}" x2="{TERM_X+TERM_W}" y2="{TERM_Y+TERM_HEAD}" '
      f'stroke="{p["term_border"]}"/>')
    for i, c in enumerate([p["red"], "#febc2e", "#28c840"]):
        a(f'<circle cx="{TERM_X+19+i*17}" cy="{TERM_Y+15}" r="5" fill="{c}"/>')
    a(f'<text x="{TERM_X+TERM_W-14}" y="{TERM_Y+19.5}" text-anchor="end" font-family="{MONO}" '
      f'font-size="11.5" letter-spacing="1.4" fill="{p["title"]}">anadi@iitm : bash</text>')

    # ── right: typed lines + reveal masks + cursor ────────────────────────
    tx = TERM_X + 18
    base_y = TERM_Y + TERM_HEAD + 34
    t = T_START
    total_masks = 0

    for li, (prompt, pcol, segments) in enumerate(LINES):
        y = base_y + li * LH
        full = line_text(prompt, segments)
        n = len(full)
        w_line = n * ADV
        t0 = t
        t_end = t0 + n * CHAR_DELAY

        # text (natural kerning)
        a(f'<text x="{tx}" y="{round(y,2)}" font-family="{MONO}" font-size="{FS}" '
          f'xml:space="preserve">')
        if prompt:
            a(f'<tspan fill="{p[pcol]}">{esc(prompt)}</tspan>')
        for key, txt in segments:
            a(f'<tspan fill="{p[key]}">{esc(txt)}</tspan>')
        a('</text>')

        # reveal mask: starts full width, shrinks one character at a time
        if preview:
            pass
        else:
            kt, vals = ["0", str(round(t0/CYCLE, 5))], [str(round(w_line+3, 2))] * 2
            for i in range(1, n + 1):
                kt.append(str(round((t0 + i * CHAR_DELAY) / CYCLE, 5)))
                vals.append(str(round((w_line + 3) * (n - i) / n, 2)))
            kt.append("1")
            vals.append("0")
            a(f'<rect x="{round(tx-2,2)}" y="{round(y-FS,2)}" height="{round(LH-3,2)}" width="0" '
              f'fill="{p["term_bg"]}">'
              f'<animate attributeName="width" dur="{CYCLE}s" repeatCount="indefinite" '
              f'calcMode="discrete" keyTimes="{";".join(kt)}" values="{' ;'.join(vals)}"/>'
              f'</rect>')
            total_masks += 1

        # cursor for this line
        if preview:
            if li == 0:
                a(f'<rect x="{round(tx,2)}" y="{round(y-FS+2,2)}" width="{round(ADV,2)}" '
                  f'height="{round(FS+3,2)}" fill="{p["blue"]}" opacity="0.9"/>')
        else:
            kt_c = ["0", f"{round(t0/CYCLE,5)}", f"{round(t_end/CYCLE,5)}",
                    f"{round((t_end+0.10)/CYCLE,5)}", "1"]
            xs = [f"{round(tx,2)}", f"{round(tx,2)}", f"{round(tx+w_line,2)}",
                  f"{round(tx+w_line,2)}", f"{round(tx+w_line,2)}"]
            a(f'<rect x="{round(tx,2)}" y="{round(y-FS+2,2)}" width="{round(ADV,2)}" '
              f'height="{round(FS+3,2)}" fill="{p["blue"]}" opacity="0.9">'
              f'<animate attributeName="x" dur="{CYCLE}s" repeatCount="indefinite" calcMode="discrete" '
              f'keyTimes="{";".join(kt_c)}" values="{";".join(xs)}"/>'
              f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" calcMode="discrete" '
              f'keyTimes="0;{round(t0/CYCLE,5)};{round(t_end/CYCLE,5)};{round((t_end+0.10)/CYCLE,5)};1" '
              f'values="0;0.9;0.9;0;0"/>'
              f'</rect>')

        t = t_end + LINE_PAUSE

    # footer strip inside terminal
    a(f'<text x="{tx}" y="{TERM_Y+TERM_H-14}" font-family="{MONO}" font-size="11.5" '
      f'letter-spacing="1.1" fill="{p["dim"]}">'
      f'python · typescript · react · electron · llm apis · n8n · git</text>')

    # the whole terminal fades out and the loop restarts
    if not preview:
        a(f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
          f'values="1;1;0;0" keyTimes="0;{round(FADE_AT/CYCLE,5)};'
          f'{round((FADE_AT+FADE_DUR)/CYCLE,5)};1"/>')

    a('</g></svg>')
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="also emit a fully-typed static copy to /tmp")
    ap.add_argument("--out", default="assets")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    for theme in ("dark", "light"):
        svg = build(theme)
        path = os.path.join(args.out, f"banner-{theme}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {path} ({len(svg)} bytes)")
        if args.preview:
            prev = build(theme, preview=True)
            with open(f"/tmp/banner-{theme}-preview.svg", "w", encoding="utf-8") as f:
                f.write(prev)


if __name__ == "__main__":
    main()
