#!/usr/bin/env python3
"""Render the open-source mission-control panel from the last good GitHub data.

Offline: no network requests or third-party packages. Generates dark/light SVGs
and can refresh the marked README section, including its accessible alt text.

Usage:
    python3 scripts/gen_open_source.py --update-readme
"""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- OPEN_SOURCE:START -->"
END = "<!-- OPEN_SOURCE:END -->"
W, H = 1200, 420
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
PALETTES = {
    "dark": {
        "bg": "#0a0a0a", "card": "#121214", "border": "#2b2b30",
        "text": "#f5f5f5", "muted": "#a0a0aa", "faint": "#777781",
        "lime": "#c6f477", "purple": "#b79aff", "track": "#26262b",
        "hero": "#141b10", "hero_border": "#43572f", "rule": "#242428",
    },
    "light": {
        "bg": "#ffffff", "card": "#f8f8fa", "border": "#e1e1e7",
        "text": "#17171c", "muted": "#62626e", "faint": "#73737e",
        "lime": "#397313", "purple": "#7048c8", "track": "#e8e8ee",
        "hero": "#f1f8e9", "hero_border": "#b7d49c", "rule": "#e8e8ee",
    },
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def validate(payload: dict) -> dict:
    if payload.get("schema_version") != 1 or payload.get("complete") is not True:
        raise ValueError("Expected complete open-source data with schema_version 1.")
    stats = payload.get("stats", {})
    for key in ("prs_opened", "prs_merged", "issues_opened", "external_repos"):
        value = stats.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Invalid stat {key}: {value!r}")
    if stats["prs_merged"] > stats["prs_opened"]:
        raise ValueError("Merged PRs cannot exceed opened PRs.")
    if not isinstance(payload.get("repositories"), list):
        raise ValueError("Missing repository list.")
    if len(payload["repositories"]) != stats["external_repos"]:
        raise ValueError("Repository count does not match the repository list.")
    datetime.fromisoformat(payload["fetched_at"].replace("Z", "+00:00"))
    return stats


def alt_text(payload: dict) -> str:
    s = validate(payload)
    return (f"Open-source mission control. Pull requests opened: {s['prs_opened']}; "
            f"pull requests merged: {s['prs_merged']}; issues opened: {s['issues_opened']}; "
            f"external repositories reached: {s['external_repos']}. "
            "Public, all-time activity outside the user's own account.")


def truncate(value: str, limit: int = 30) -> str:
    return value if len(value) <= limit else value[:limit - 1] + "…"


def build_svg(payload: dict, theme: str = "dark") -> str:
    s = validate(payload)
    p = PALETTES[theme]
    o = []
    a = o.append
    rate = s["prs_merged"] / s["prs_opened"] if s["prs_opened"] else 0
    bar_width = 1136 * rate
    updated = datetime.fromisoformat(payload["fetched_at"].replace("Z", "+00:00"))
    date_label = updated.strftime("%d %b %Y").upper()

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="oss-title oss-desc">')
    a(f'<title id="oss-title">Open-source mission control</title>')
    a(f'<desc id="oss-desc">{esc(alt_text(payload))}</desc>')
    a(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{p["bg"]}" stroke="{p["border"]}"/>')

    # Header: a small branch mark, a strong title, and an explicit scope pill.
    a(f'<g transform="translate(34 28)" fill="none" stroke="{p["lime"]}" stroke-width="2.2" stroke-linecap="round">')
    a('<circle cx="3" cy="4" r="3"/><circle cx="3" cy="24" r="3"/><circle cx="21" cy="4" r="3"/>')
    a('<path d="M3 7v14M21 7v3a7 7 0 0 1-7 7H3"/></g>')
    a(f'<text x="72" y="49" font-family="{MONO}" font-size="20" font-weight="700" '
      f'letter-spacing="2.4" fill="{p["text"]}">OPEN SOURCE</text>')
    a(f'<text x="267" y="48" font-family="{SANS}" font-size="19" fill="{p["lime"]}">↗</text>')
    a(f'<rect x="925" y="27" width="243" height="29" rx="14.5" fill="{p["card"]}" stroke="{p["border"]}"/>')
    a(f'<circle cx="942" cy="41.5" r="3" fill="{p["lime"]}"/>')
    a(f'<text x="955" y="46" font-family="{MONO}" font-size="11" letter-spacing="0.7" '
      f'fill="{p["muted"]}">PUBLIC · ALL TIME · EXTERNAL</text>')
    a(f'<text x="34" y="78" font-family="{SANS}" font-size="15" fill="{p["muted"]}">'
      'Contributions beyond my own repositories.</text>')

    cards = [
        ("prs_opened", "PRs OPENED", "SUBMITTED", p["text"]),
        ("prs_merged", "PRs MERGED", "ACCEPTED", p["lime"]),
        ("issues_opened", "ISSUES OPENED", "REPORTED", p["purple"]),
        ("external_repos", "EXTERNAL REPOS", "REACHED", p["text"]),
    ]
    for index, (key, label, caption, color) in enumerate(cards):
        x = 32 + index * 289
        hero = key == "prs_merged"
        a(f'<rect x="{x}" y="100" width="269" height="166" rx="10" '
          f'fill="{p["hero"] if hero else p["card"]}" stroke="{p["hero_border"] if hero else p["border"]}"/>')
        a(f'<text x="{x+20}" y="126" font-family="{MONO}" font-size="10" letter-spacing="1.4" '
          f'fill="{color if hero else p["faint"]}">{caption}</text>')
        value = f'{s[key]:,}'
        size = 76 if len(value) < 5 else 62 if len(value) < 7 else 48
        a(f'<text x="{x+18}" y="207" font-family="{SANS}" font-size="{size}" font-weight="750" '
          f'letter-spacing="-3" fill="{color}">{value}</text>')
        a(f'<text x="{x+20}" y="244" font-family="{MONO}" font-size="12" letter-spacing="1.1" '
          f'fill="{p["muted"]}">{label}</text>')
        if hero:
            a(f'<path d="M{x+229} 119l4 4 8-8" fill="none" stroke="{color}" stroke-width="2" '
              'stroke-linecap="round" stroke-linejoin="round"/>')

    a(f'<text x="32" y="301" font-family="{MONO}" font-size="11" letter-spacing="1.5" '
      f'fill="{p["muted"]}">MERGE RATE</text>')
    right = (f'{s["prs_merged"]} / {s["prs_opened"]} PRs · {rate:.0%}'
             if s["prs_opened"] else 'No external PRs yet')
    a(f'<text x="1168" y="301" text-anchor="end" font-family="{MONO}" font-size="12" '
      f'fill="{p["text"]}">{esc(right)}</text>')
    a(f'<rect x="32" y="315" width="1136" height="8" rx="4" fill="{p["track"]}"/>')
    if bar_width:
        a(f'<rect x="32" y="315" width="{bar_width:.2f}" height="8" rx="4" fill="{p["lime"]}"/>')
    a(f'<line x1="32" y1="348" x2="1168" y2="348" stroke="{p["rule"]}"/>')

    names = [truncate(repo["name"]) for repo in payload["repositories"][:3]]
    reaching = " · ".join(names) if names else "The next contribution starts here."
    if s["external_repos"] > 3:
        reaching += f'  +{s["external_repos"]-3} more'
    a(f'<text x="32" y="374" font-family="{MONO}" font-size="10" letter-spacing="1.4" '
      f'fill="{p["faint"]}">REPOSITORY FOOTPRINT</text>')
    a(f'<text x="32" y="398" font-family="{MONO}" font-size="13" fill="{p["muted"]}">{esc(reaching)}</text>')
    a(f'<text x="1168" y="374" text-anchor="end" font-family="{MONO}" font-size="10" '
      f'letter-spacing="1.1" fill="{p["faint"]}">LAST REFRESH</text>')
    a(f'<text x="1168" y="398" text-anchor="end" font-family="{MONO}" font-size="12" '
      f'fill="{p["muted"]}">{date_label} ↻</text>')
    a('</svg>')
    return "\n".join(o)


def search_url(query: str, kind: str) -> str:
    return "https://github.com/search?" + urllib.parse.urlencode({"q": query, "type": kind})


def readme_block(payload: dict) -> str:
    validate(payload)
    user = payload["user"]
    base = f"https://raw.githubusercontent.com/{user}/{user}/main/assets"
    pr_url = search_url(payload["queries"]["prs"], "pullrequests")
    issue_url = search_url(payload["queries"]["issues"], "issues")
    return f"""{START}
### open source

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="{base}/open-source-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="{base}/open-source-light.svg">
  <img src="{base}/open-source-dark.svg" alt="{esc(alt_text(payload))}" width="100%">
</picture>

<sub>Public, all-time activity outside my own account. PRs and issues counted separately.</sub><br>
<a href="{esc(pr_url)}">Pull requests ↗</a> · <a href="{esc(issue_url)}">Issues ↗</a>

</div>
{END}"""


def update_readme(text: str, block: str) -> str:
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("README must contain exactly one OPEN_SOURCE start/end marker pair.")
    pattern = re.escape(START) + r".*?" + re.escape(END)
    return re.sub(pattern, lambda _: block, text, count=1, flags=re.DOTALL)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/open-source.json")
    parser.add_argument("--out", default=str(ROOT / "assets"))
    parser.add_argument("--update-readme", action="store_true")
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    args = parser.parse_args()
    payload = json.loads(args.data.read_text(encoding="utf-8"))
    for theme in PALETTES:
        path = Path(args.out) / f"open-source-{theme}.svg"
        atomic_write(path, build_svg(payload, theme))
        print(f"wrote {path}")
    if args.update_readme:
        old = args.readme.read_text(encoding="utf-8")
        atomic_write(args.readme, update_readme(old, readme_block(payload)))
        print(f"updated {args.readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
