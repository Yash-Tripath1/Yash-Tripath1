#!/usr/bin/env python3
"""
Generates the rotating "featured work" strip (dark + light) for the README.

Four rows, each cycling through two projects per loop with a staggered start, so
at any moment four different projects are on screen and all eight get shown.

Animation is SMIL only (opacity + a small translate on entry), so it survives
GitHub's image proxy and plays inside an <img> tag.

Usage:
    python3 scripts/gen_showcase.py            # writes assets/featured-{dark,light}.svg
    python3 scripts/gen_showcase.py --preview  # also writes a static copy to /tmp
"""

import argparse
import os

W = 1200
PAD = 20
ROW_H = 56
ROWS = 4
H = PAD * 2 + ROWS * ROW_H

CYCLE = 27.0        # one full loop
SLOT = CYCLE / 2    # each row shows project A then project B
STAGGER = 4.5       # rows start offset from each other
FADE = 0.9          # fade in / out duration
RISET = 0.7         # entry slide duration
GAP = 0.55          # gap between a row's two slots

MONO = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'DejaVu Sans Mono', 'Liberation Mono', monospace")
SANS = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, "
        "Arial, sans-serif")

# (name, description, stack)  -- kept short so rows never collide
PROJECTS = [
    ("seq-matching",    "a reported policy advantage that does not survive 12x the data",
     "python · simulation · power analysis"),
    ("Bendlab",         "plant bending simulated, clustered, parameters shown to be degenerate",
     "python · clustering · model fitting"),
    ("anadi-dev",       "a 3D universe you scroll through, every planet is a project",
     "react · three.js · typescript"),
    ("Vynt",            "a Y2K photo booth for the desktop, exports PNG and WebM",
     "typescript · canvas · electron"),
    ("vynt-meet",       "Y2K filters piped into the video Google Meet actually sends",
     "chrome mv3 · canvas · javascript"),
    ("Collex",          "verified data and Groq written reviews on 250+ Indian colleges",
     "javascript · groq · firebase"),
    ("Shakespeare-GPT", "a language model trained from scratch on 80,000 lines of Shakespeare",
     "python · numpy"),
    ("SurfGambit",      "a web browser built from scratch, rendering pipeline and all",
     "python · tkinter"),
]

PALETTE = {
    "dark": {
        "bg": "#0a0a0a", "border": "#262626",
        "index": "#4a4a4a", "name": "#ffffff", "desc": "#a8a8a8",
        "stack": "#6a6a6a", "rule": "#1a1a1a",
    },
    "light": {
        "bg": "#ffffff", "border": "#e2e2e2",
        "index": "#a9a9a9", "name": "#0a0a0a", "desc": "#3c3c3c",
        "stack": "#8f8f8f", "rule": "#f0f0f0",
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def slot_times(row: int, slot: int, preview: bool):
    """(t_start, t_end) for a row's slot inside the loop."""
    start = (row * STAGGER + slot * (SLOT + GAP)) % CYCLE
    end = start + SLOT
    if end > CYCLE:                      # wrap: keep schedules monotonic
        start, end = start - CYCLE, end - CYCLE
        if start < 0:
            start += CYCLE
            end += CYCLE
    return start, end


def build(theme: str, preview: bool = False) -> str:
    p = PALETTE[theme]
    o = []
    a = o.append

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'role="img" aria-label="Featured work">')
    a(f'<rect width="{W}" height="{H}" rx="14" fill="{p["bg"]}" stroke="{p["border"]}"/>')

    for row in range(ROWS):
        top = PAD + row * ROW_H
        base = top + 36
        if row:
            a(f'<line x1="30" y1="{top}" x2="{W-30}" y2="{top}" stroke="{p["rule"]}"/>')

        for slot in range(2):
            proj = PROJECTS[row + slot * ROWS]
            idx = PROJECTS.index(proj) + 1
            name, desc, stack = proj

            if preview:
                open_anim = close_anim = slide = ""
                op = 1 if slot == 0 else 0
            else:
                t0, t1 = slot_times(row, slot, preview)
                t_in = (t0 + 0.1)
                t_out = t1 - FADE
                # opacity: hidden, fade in, hold, fade out, hidden
                kt = [0, t_in / CYCLE, (t_in + FADE) / CYCLE,
                      t_out / CYCLE, (t_out + FADE) / CYCLE, 1]
                kt = [f"{max(0.0, min(1.0, k)):.5f}" for k in kt]
                vals = "0;0;1;1;0;0"
                op = 0
                open_anim = (f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
                             f'keyTimes="{";".join(kt)}" values="{vals}"/>')
                # small slide up on entry
                s0, s1 = t_in / CYCLE, min(1.0, (t_in + RISET) / CYCLE)
                slide = (f'<animateTransform attributeName="transform" type="translate" '
                         f'dur="{CYCLE}s" repeatCount="indefinite" '
                         f'keyTimes="0;{s0:.5f};{s1:.5f};1" values="0 9;0 9;0 0;0 0"/>')

            a(f'<g opacity="{op}">{open_anim}{slide}')
            a(f'<text x="40" y="{base}" font-family="{MONO}" font-size="12" letter-spacing="1.2" '
              f'fill="{p["index"]}">{idx:02d}</text>')
            a(f'<text x="78" y="{base}" font-family="{MONO}" font-size="19" font-weight="700" '
              f'letter-spacing="0.2" fill="{p["name"]}">{esc(name)}</text>')
            a(f'<text x="330" y="{base}" font-family="{SANS}" font-size="15" fill="{p["desc"]}">'
              f'{esc(desc)}</text>')
            a(f'<text x="{W-40}" y="{base}" text-anchor="end" font-family="{MONO}" font-size="11.5" '
              f'letter-spacing="0.6" fill="{p["stack"]}">{esc(stack)}</text>')
            a('</g>')

    a('</svg>')
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets")
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for theme in ("dark", "light"):
        svg = build(theme)
        path = os.path.join(args.out, f"featured-{theme}.svg")
        open(path, "w", encoding="utf-8").write(svg)
        print(f"wrote {path} ({len(svg)} bytes)")
        if args.preview:
            open(f"/tmp/featured-{theme}-preview.svg", "w", encoding="utf-8").write(
                build(theme, preview=True))


if __name__ == "__main__":
    main()
