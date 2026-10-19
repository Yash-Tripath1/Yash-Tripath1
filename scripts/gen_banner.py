#!/usr/bin/env python3
"""
Full width animated terminal banner for the GitHub profile README.

Design:
  the entire banner is one terminal window. A shell session types itself out,
  holds, then clears and loops. Monochrome only, so the real contribution
  graph below stays the one coloured thing on the page.

Tech notes (why it never breaks):
  * Pure declarative SVG + SMIL. No <style>, no <script>, no external fonts.
    Survives GitHub's camo proxy and works inside <img>.
  * Text is one <text> per line (natural kerning). The typewriter effect is a
    rect in the terminal's background colour whose width shrinks in discrete
    steps, plus a block cursor. No font metric guessing on the glyphs, so it
    renders identically everywhere.

Usage:
    python3 scripts/gen_banner.py              # writes assets/banner-{dark,light}.svg
    python3 scripts/gen_banner.py --preview    # also writes fully typed copies to /tmp
"""

import argparse
import os

W, H = 1200, 362
RX = 14
CHROME = 48          # height of the window title bar
FS = 18.0            # terminal font size
LH = 31.5            # line height
ADV = FS * 0.6       # nominal monospace advance (mask + cursor maths only)
PAD_X = 34           # left inset of the text
BASE_Y = CHROME + 36 # baseline of the first line

CURSOR_X = PAD_X + 14 * ADV   # right edge of "anadi@iitm:~$ " prompt

MONO = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'DejaVu Sans Mono', 'Liberation Mono', monospace")

PROMPT_USER = "anadi@iitm"
PROMPT_SYM = ":~$"

# kind: "cmd" (typed by hand) | "out" (output burst) | "idle" (bare prompt)
LINES = [
    ("cmd", "whoami"),
    ("out", [("txt", "anadi tripathi"), ("dim", " · "), ("txt", "18"),
             ("dim", " · "), ("txt", "lucknow, india"), ("dim", " · "),
             ("txt", "solo developer")]),
    ("cmd", "cat roles.txt"),
    ("out", [("txt", "co-founder @ glymph studio"), ("dim", " · "),
             ("txt", "ai / ml"), ("dim", " · "), ("txt", "automation"),
             ("dim", " · "), ("txt", "cybersecurity")]),
    ("cmd", "ls ~/stack"),
    ("out", [("txt", "python"), ("dim", " · "), ("txt", "typescript"),
             ("dim", " · "), ("txt", "javascript"), ("dim", " · "),
             ("txt", "react"), ("dim", " · "), ("txt", "vite"), ("dim", " · "),
             ("txt", "node"), ("dim", " · "), ("txt", "electron"),
             ("dim", " · "), ("txt", "llm apis"), ("dim", " · "),
             ("txt", "linux")]),
    ("cmd", "cat links.txt"),
    ("out", [("link", "anadi-dev.vercel.app"), ("dim", " · "),
             ("link", "github.com/yash-tripath1"), ("dim", " · "),
             ("link", "linkedin.com/in/anadi-tripathi")]),
    ("idle", ""),
]

TYPE_CMD = 0.020     # seconds per character, hand typed
TYPE_OUT = 0.008     # seconds per character, output burst
LINE_PAUSE = 0.26
T_START = 0.7        # first keystroke
TAIL = 0.9           # room for the cursor to settle on the last prompt

PALETTE = {
    "dark": {
        "bg": "#0a0a0a", "chrome": "#131313", "border": "#262626",
        "user": "#8b8b8b", "sym": "#4f4f4f", "cmd": "#ffffff",
        "txt": "#b8b8b8", "dim": "#565656", "link": "#ffffff",
        "title": "#5a5a5a", "caps": ["#5c5c5c", "#424242", "#303030"],
        "cursor": "#ffffff",
    },
    "light": {
        "bg": "#ffffff", "chrome": "#f4f4f4", "border": "#e2e2e2",
        "user": "#6a6a6a", "sym": "#b2b2b2", "cmd": "#0a0a0a",
        "txt": "#4a4a4a", "dim": "#a6a6a6", "link": "#0a0a0a",
        "title": "#969696", "caps": ["#d4d4d4", "#bfbfbf", "#a9a9a9"],
        "cursor": "#0a0a0a",
    },
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def line_len(kind, payload) -> int:
    if kind == "idle":
        return 0
    if kind == "cmd":
        return len(payload)
    return sum(len(t) for _, t in payload)


def build(theme: str, preview: bool = False) -> str:
    p = PALETTE[theme]
    o = []
    a = o.append

    # ── timeline ─────────────────────────────────────────────────────────────
    times, t = [], T_START
    for kind, payload in LINES:
        n = line_len(kind, payload)
        step = TYPE_OUT if kind == "out" else TYPE_CMD
        if kind == "idle":
            n, step = len(PROMPT_USER) + len(PROMPT_SYM) + 1, TYPE_CMD
        t0 = t
        t1 = t0 + n * step
        times.append((t0, t1, step))
        t = t1 + (0.0 if kind == "idle" else LINE_PAUSE)
    end = t
    # the session types once, then freezes: nothing is ever erased until the
    # page (and therefore the image) is reloaded
    cycle = round(end + TAIL, 2)

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}" role="img" '
      f'aria-label="Anadi Tripathi, solo developer, co-founder of Glymph Studio">')
    a('<defs>')
    a(f'<clipPath id="body"><rect x="1" y="{CHROME}" width="{W-2}" height="{H-CHROME-1}" '
      f'rx="0"/></clipPath>')
    a('</defs>')

    # ── window ───────────────────────────────────────────────────────────────
    a(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="{RX}" fill="{p["bg"]}" '
      f'stroke="{p["border"]}"/>')
    # title bar: rounded top corners, flat bottom
    a(f'<path d="M1 {1+RX} a{RX} {RX} 0 0 1 {RX} -{RX} h{W-2-2*RX} '
      f'a{RX} {RX} 0 0 1 {RX} {RX} v{CHROME-1-RX} h-{W-2} z" fill="{p["chrome"]}"/>')
    a(f'<line x1="1" y1="{CHROME}" x2="{W-1}" y2="{CHROME}" stroke="{p["border"]}"/>')

    for i, c in enumerate(p["caps"]):
        a(f'<circle cx="{24 + i*18}" cy="{CHROME/2}" r="5.5" fill="{c}"/>')
    a(f'<text x="{86}" y="{CHROME/2 + 4.5}" font-family="{MONO}" font-size="12.5" '
      f'letter-spacing="1.3" fill="{p["title"]}">anadi@iitm: ~/profile</text>')
    a(f'<text x="{W-22}" y="{CHROME/2 + 4.5}" text-anchor="end" font-family="{MONO}" '
      f'font-size="12.5" letter-spacing="1.6" fill="{p["title"]}">bash</text>')

    # ── body ─────────────────────────────────────────────────────────────────
    a('<g clip-path="url(#body)">')
    a('<g id="session">')

    for i, ((kind, payload), (t0, t1, step)) in enumerate(zip(LINES, times)):
        y = BASE_Y + i * LH
        segs = []                              # (fill key, text) list
        if kind in ("cmd", "idle"):
            segs.append(("user", PROMPT_USER))
            segs.append(("sym", PROMPT_SYM + " "))
            if kind == "cmd":
                segs.append(("cmd", payload))
        else:
            segs.extend(payload)

        text_w = sum(len(txt) for _, txt in segs) * ADV

        a(f'<text x="{PAD_X}" y="{round(y, 2)}" font-family="{MONO}" '
          f'font-size="{FS}" xml:space="preserve">')
        for key, txt in segs:
            a(f'<tspan fill="{p[key]}">{esc(txt)}</tspan>')
        a('</text>')

        if preview:
            if kind == "idle":
                a(f'<rect x="{round(PAD_X + text_w, 2)}" y="{round(y - FS + 2, 2)}" '
                  f'width="{round(ADV, 2)}" height="{round(FS + 3, 2)}" '
                  f'fill="{p["cursor"]}" opacity="0.9"/>')
            continue

        # reveal mask: full width at t0, shrinks one character at a time to 0
        n = max(1, round(len("".join(txt for _, txt in segs))))
        kt = ["0", str(round(t0 / cycle, 5))]
        vals = [str(round(text_w + 3, 2))] * 2
        for k in range(1, n + 1):
            kt.append(str(round((t0 + k * step) / cycle, 5)))
            vals.append(str(round((text_w + 3) * (n - k) / n, 2)))
        kt.append("1")
        vals.append("0")
        a(f'<rect x="{round(PAD_X - 2, 2)}" y="{round(y - FS, 2)}" height="{round(LH - 3, 2)}" '
          f'width="0" fill="{p["bg"]}">'
          f'<animate attributeName="width" dur="{cycle}s" fill="freeze" '
          f'calcMode="discrete" keyTimes="{";".join(kt)}" values="{";".join(vals)}"/>'
          f'</rect>')

        # block cursor: slides along with the typing, then blinks out
        show_from, show_to = t0, t1 + 0.09
        # outer group carries the blink (idle only), inner rect carries the reveal
        blink = ('<animate attributeName="opacity" dur="1.15s" repeatCount="indefinite" '
                 'values="1;0.1;1" keyTimes="0;0.5;1"/>') if kind == "idle" and not preview else ""
        a(f'<g>{blink}')
        a(f'<rect x="{round(PAD_X, 2)}" y="{round(y - FS + 2, 2)}" width="{round(ADV, 2)}" '
          f'height="{round(FS + 3, 2)}" fill="{p["cursor"]}" opacity="0">')
        a(f'<animate attributeName="x" dur="{cycle}s" fill="freeze" '
          f'keyTimes="0;{round(t0/cycle,5)};{round(t1/cycle,5)};1" '
          f'values="{round(PAD_X,2)};{round(PAD_X,2)};'
          f'{round(PAD_X + text_w, 2)};{round(PAD_X + text_w, 2)}"/>')
        if kind == "idle":
            a(f'<animate attributeName="opacity" dur="{cycle}s" fill="freeze" '
              f'calcMode="discrete" keyTimes="0;{round(t1/cycle,5)};1" values="0;0.9;0.9"/>')
        else:
            a(f'<animate attributeName="opacity" dur="{cycle}s" fill="freeze" '
              f'calcMode="discrete" keyTimes="0;{round(show_from/cycle,5)};'
              f'{round(show_to/cycle,5)};1" values="0;0.9;0;0"/>')
        a('</rect></g>')

    a('</g>')
    a('</g></svg>')

    svg = "\n".join(o)
    assert "url(#" not in svg.replace('url(#body)', '').replace('url(#session)', ''), \
        "stale paint server reference"
    return svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true",
                    help="also emit fully typed static copies to /tmp")
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
            print(f"wrote /tmp/banner-{theme}-preview.svg")


if __name__ == "__main__":
    main()
