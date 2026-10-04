#!/usr/bin/env python3
"""
Fetches the public contribution calendar for a GitHub user and stores it as JSON.

Source: https://github.com/users/<user>/contributions  (public HTML, no token needed)

Usage:
    python3 scripts/fetch_contributions.py                 # defaults to Yash-Tripath1
    python3 scripts/fetch_contributions.py --user someone

Writes data/contributions.json:
    {
      "user": "...",
      "fetched": "2026-10-04",
      "total": 265,
      "first_day": "2025-10-05",
      "last_day": "2026-10-03",
      "days": [{"date": "2025-10-05", "level": 0}, ...]
    }
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fetch(user: str) -> str:
    url = f"https://github.com/users/{user}/contributions"
    for tool in (["curl", "-sL", "--max-time", "40", url],
                 ["wget", "-qO-", "--timeout=40", url]):
        try:
            out = subprocess.run(tool, capture_output=True, text=True, timeout=60)
            if out.returncode == 0 and "data-level" in out.stdout:
                return out.stdout
        except Exception:
            continue
    sys.exit("could not fetch contribution data")


def parse(html: str):
    days = []
    for m in re.finditer(r'<td[^>]*data-date="([\d-]+)"[^>]*data-level="(\d)"', html):
        days.append({"date": m.group(1), "level": int(m.group(2))})
    if not days:
        sys.exit("no contribution cells found in GitHub response")
    total = None
    for pat in (r'([\d,]+)\s+contributions?\s+in the last year', r'>([\d,]+)</span>\s*contributions'):
        m = re.search(pat, html)
        if m:
            total = int(m.group(1).replace(",", ""))
            break
    if total is None:
        total = sum(1 for d in days if d["level"] > 0)   # fallback: active days
    return days, total


def streaks(days):
    """(current, longest) in days. Today counts as a grace day if it is empty."""
    flags = [d["level"] > 0 for d in days]
    longest = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        longest = max(longest, cur)
    current = 0
    for i in range(len(flags) - 1, -1, -1):
        if flags[i]:
            current += 1
        elif i == len(flags) - 1:
            continue         # today not finished yet — don't break the streak
        else:
            break
    return current, longest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="Yash-Tripath1")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "contributions.json"))
    args = ap.parse_args()

    html = fetch(args.user)
    days, total = parse(html)
    cur, longest = streaks(days)

    payload = {
        "user": args.user,
        "fetched": date.today().isoformat(),
        "total": total,
        "current_streak": cur,
        "longest_streak": longest,
        "first_day": days[0]["date"],
        "last_day": days[-1]["date"],
        "days": days,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)

    print(f"{args.user}: {total} contributions · {len(days)} days · "
          f"streak {cur}d (longest {longest}d) · {days[0]['date']} → {days[-1]['date']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
