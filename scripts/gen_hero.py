#!/usr/bin/env python3
"""
Generates a self-hosted animated contribution heatmap (dark + light).

Why: third-party graph services (github-readme-activity-graph, herokuapp streak
stats, etc.) go down or rate-limit with a 402 and leave a broken image in the
README. This one is built from data/contributions.json and lives in the repo, so
it renders forever, matches the profile palette, and can animate.

Animation (SMIL only, works inside <img>):
  * columns fade in one after another (a left-to-right reveal)
  * a soft light sweep crosses the grid on a slow loop
  * month labels + totals are static
"""

import argparse
import json
import os
from datetime import date, datetime

W = 1200
PITCH = 17          # column/row pitch
CELL = 13           # cell size
COLS = 53           # GitHub uses 53 week columns
GRID_W = COLS * PITCH - (PITCH - CELL)
ROWS = 7
GRID_H = ROWS * PITCH - (PITCH - CELL)

X0 = (W - GRID_W) // 2
Y_HEAD = 46
Y0 = Y_HEAD + 44                        # grid top
H = Y0 + GRID_H + 62                    # canvas height

CYCLE = 14.0
COL_DELAY = 0.16
SWEEP_PERIOD = 7.0

MONO = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'DejaVu Sans Mono', 'Liberation Mono', monospace")

PALETTE = {
    "dark": {
        "bg": "#0d1117", "border": "#1d2635", "grid_empty": "#1b2434",
        "ramp": ["#1b2434", "#173a63", "#1f6fb2", "#48a8f0", "#7dcfff"],
        "title": "#3d4a63", "muted": "#6b7a99", "text": "#c0caf5", "accent": "#7aa2f7",
        "sweep": "#7aa2f7",
    },
    "light": {
        "bg": "#ffffff", "border": "#dbe2f0", "grid_empty": "#eaeffb",
        "ramp": ["#e8eefb", "#bcd3f8", "#85aef2", "#4d86e0", "#2b5bd7"],
        "title": "#93a1bb", "muted": "#5b6b85", "text": "#1f2937", "accent": "#2b5bd7",
        "sweep": "#4d86e0",
    },
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(theme, data, preview=False):
    p = PALETTE[theme]
    days = data["days"]
    total = data["total"]
    cur = data.get("current_streak", 0)
    longest = data.get("longest_streak", 0)

    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'role="img" aria-label="{total} contributions in the last year">')
    a('<defs>')
    a(f'<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">'
      f'<stop offset="0" stop-color="{p["sweep"]}" stop-opacity="0"/>'
      f'<stop offset="0.5" stop-color="{p["sweep"]}" stop-opacity="0.30"/>'
      f'<stop offset="1" stop-color="{p["sweep"]}" stop-opacity="0"/>'
      f'</linearGradient>')
    a(f'<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
      f'<stop offset="0" stop-color="{p["bg"]}" stop-opacity="0"/>'
      f'<stop offset="1" stop-color="{p["bg"]}" stop-opacity="0"/></linearGradient>')
    a('</defs>')

    a(f'<rect width="{W}" height="{H}" rx="14" fill="{p["bg"]}" stroke="{p["border"]}"/>')

    # ── header ────────────────────────────────────────────────────────────
    a(f'<text x="44" y="{Y_HEAD}" font-family="{MONO}" font-size="13" letter-spacing="2.6" '
      f'fill="{p["title"]}">CONTRIBUTION ACTIVITY</text>')
    a(f'<text x="{W-44}" y="{Y_HEAD}" text-anchor="end" font-family="{MONO}" font-size="13" '
      f'letter-spacing="1.2" fill="{p["muted"]}">'
      f'{total} contributions in the last year</text>')

    # ── month labels ──────────────────────────────────────────────────────
    labels = {}
    for i, d in enumerate(days):
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        col = i // 7
        if dt.day <= 7 and dt.month not in labels:
            labels[dt.month] = col
    # keep labels from colliding: at least 3 columns (51px) apart
    last_col = -99
    for month, col in sorted(labels.items(), key=lambda kv: kv[1]):
        if col - last_col < 3:
            continue
        last_col = col
        x = X0 + col * PITCH
        a(f'<text x="{x}" y="{Y0-12}" font-family="{MONO}" font-size="10.5" '
          f'letter-spacing="1" fill="{p["title"]}">{MONTHS[month-1]}</text>')

    # ── cells, grouped per column so each column can fade in as a unit ────
    a('<g>')
    for col in range(COLS):
        cells = []
        for row in range(ROWS):
            i = col * 7 + row
            if i >= len(days):
                continue
            lvl = days[i]["level"]
            cells.append((row, lvl, days[i]["date"]))
        if not cells:
            continue
        if preview:
            reveal = ""
        else:
            t_in = 0.55 + col * COL_DELAY
            reveal = (f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" '
                      f'calcMode="discrete" keyTimes="0;{round(t_in/CYCLE,5)};'
                      f'{round((CYCLE-0.9)/CYCLE,5)};1" values="0;1;1;0"/>')
        a(f'<g opacity="{1 if preview else 0}">{reveal}')
        for row, lvl, day in cells:
            x = X0 + col * PITCH
            y = Y0 + row * PITCH
            a(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" '
              f'fill="{p["ramp"][lvl]}"><title>{esc(day)}, level {lvl}</title></rect>')
        a('</g>')
    a('</g>')

    # ── light sweep across the grid ───────────────────────────────────────
    if not preview:
        a(f'<rect x="{X0}" y="{Y0-4}" width="170" height="{GRID_H+8}" fill="url(#sweep)" clip-path="none">'
          f'<animate attributeName="x" dur="{SWEEP_PERIOD}s" repeatCount="indefinite" '
          f'values="{X0-180};{X0+GRID_W+20}" keyTimes="0;1"/>'
          f'</rect>')

    # ── footer: streaks + legend ──────────────────────────────────────────
    fy = Y0 + GRID_H + 40
    a(f'<text x="44" y="{fy}" font-family="{MONO}" font-size="12" letter-spacing="1.2" fill="{p["muted"]}">'
      f'current streak <tspan fill="{p["accent"]}">{cur}d</tspan>'
      f'<tspan fill="{p["title"]}">  ·  </tspan>longest <tspan fill="{p["accent"]}">{longest}d</tspan>'
      f'<tspan fill="{p["title"]}">  ·  </tspan>updated {esc(data["fetched"])}</text>')

    lx = W - 44
    a(f'<text x="{lx - 5*PITCH - 10}" y="{fy}" text-anchor="end" font-family="{MONO}" '
      f'font-size="11" fill="{p["title"]}">less</text>')
    for i, c in enumerate(p["ramp"]):
        a(f'<rect x="{lx - 5*PITCH + i*PITCH - CELL}" y="{fy-11}" width="{CELL}" height="{CELL}" '
          f'rx="3" fill="{c}"/>')
    a(f'<text x="{lx + 8}" y="{fy}" font-family="{MONO}" font-size="11" fill="{p["title"]}">more</text>')

    a('</svg>')
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/contributions.json")
    ap.add_argument("--out", default="assets")
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(args.out, exist_ok=True)
    for theme in ("dark", "light"):
        svg = build(theme, data)
        path = os.path.join(args.out, f"activity-{theme}.svg")
        open(path, "w", encoding="utf-8").write(svg)
        print(f"wrote {path} ({len(svg)} bytes)")
        if args.preview:
            open(f"/tmp/activity-{theme}-preview.svg", "w", encoding="utf-8").write(
                build(theme, data, preview=True))


if __name__ == "__main__":
    main()
