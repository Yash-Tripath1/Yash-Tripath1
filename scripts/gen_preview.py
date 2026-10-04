#!/usr/bin/env python3
"""
Builds preview.html — a local, self-contained mock of how the README renders on
GitHub, with the real generated SVGs inlined so animations play offline.

Dark/light toggle is pure CSS (checkbox + sibling selectors), so it works inside
sandboxed preview iframes with no external requests.

Usage:
    python3 scripts/gen_preview.py            # writes preview.html
    python3 scripts/gen_preview.py --no-snake # skip fetching the live snake svg
"""

import argparse
import base64
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAKE_DARK = "https://raw.githubusercontent.com/Yash-Tripath1/Yash-Tripath1/output/github-contribution-grid-snake-dark.svg"
SNAKE_LIGHT = "https://raw.githubusercontent.com/Yash-Tripath1/Yash-Tripath1/output/github-contribution-grid-snake.svg"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def fetch(url):
    try:
        out = subprocess.run(["curl", "-sL", "--max-time", "30", url],
                             capture_output=True, text=True, timeout=45)
        if out.returncode == 0 and out.stdout.lstrip().startswith("<"):
            return out.stdout
    except Exception:
        pass
    return None


def data_uri_img(svg: str, alt: str) -> str:
    """Exactly how GitHub serves it: an <img> pointing at the SVG bytes.
    Data URI instead of camo so the preview works offline."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (f'<img src="data:image/svg+xml;base64,{b64}" alt="{alt}" '
            f'style="width:100%;height:auto;display:block">')


def inline_svg(svg: str, cls: str = "") -> str:
    """Strip the xml declaration and make sure it scales 100% wide."""
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r'(<svg[^>]*?)width="[^"]*"', r"\1", svg, count=1)
    svg = re.sub(r'(<svg[^>]*?)height="[^"]*"', r"\1", svg, count=1)
    svg = svg.replace("<svg", f'<svg class="{cls}" style="width:100%;height:auto;display:block"', 1)
    return svg


def chip(label: str, gold: str = "#7aa2f7") -> str:
    w = 10 + len(label) * 6.6
    return (f'<svg width="{w:.0f}" height="20" style="vertical-align:middle" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w:.0f}" height="20" rx="3" fill="#16223a"/>'
            f'<text x="5" y="14" font-family="ui-monospace,Menlo,Consolas,monospace" '
            f'font-size="11.5" fill="{gold}">{label}</text></svg>')


def build(with_snake=True):
    banner_d, banner_l = (read(f"{ROOT}/assets/banner-{t}.svg") for t in ("dark", "light"))
    feat_d, feat_l = (read(f"{ROOT}/assets/featured-{t}.svg") for t in ("dark", "light"))
    act_d, act_l = (read(f"{ROOT}/assets/activity-{t}.svg") for t in ("dark", "light"))
    snake_d = fetch(SNAKE_DARK) if with_snake else None
    snake_l = fetch(SNAKE_LIGHT) if with_snake else None
    if with_snake and not snake_d:
        print("note: could not fetch live snake svg — using a placeholder", file=sys.stderr)

    snake_block_d = data_uri_img(snake_d, "snake") if snake_d else \
        '<div style="padding:28px;text-align:center;color:#6b7a99;font:13px ui-monospace,monospace;' \
        'border:1px dashed #1d2635;border-radius:8px">snake.svg renders here (from the <code>output</code> branch)</div>'
    snake_block_l = data_uri_img(snake_l, "snake") if snake_l else snake_block_d

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>github.com/Yash-Tripath1 · README preview</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 32px 16px 64px;
    background: #0d1117; color: #e6edf3;
    font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .wrap {{ max-width: 868px; margin: 0 auto; }}
  .bar {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:22px;
         font: 12.5px ui-monospace, SFMono-Regular, Menlo, monospace; color:#6b7a99; letter-spacing:.6px }}
  .toggle input {{ display:none; }}
  .toggle span {{ border:1px solid #1d2635; border-radius:6px; padding:6px 12px; cursor:pointer; color:#7aa2f7 }}
  .toggle input:checked + span {{ color:#e6edf3; background:#16223a }}
  h3 {{ font-size: 1.25em; font-weight:600; margin: 34px 0 12px; padding-bottom:8px; border-bottom:1px solid #21262d }}
  p, li {{ font-size: 15.5px }}
  a {{ color:#7aa2f7; text-decoration:none }}
  a:hover {{ text-decoration:underline }}
  code {{ background:#161b22; padding:.2em .4em; border-radius:6px; font: 12.5px ui-monospace,Menlo,Consolas,monospace }}
  pre {{ background:#0b0f17; border:1px solid #1d2635; border-radius:8px; padding:14px 16px; overflow:auto;
        font: 13px/1.65 ui-monospace,Menlo,Consolas,monospace; color:#c0caf5 }}
  pre .k {{ color:#7dcfff }} pre .s {{ color:#9ece6a }} pre .p {{ color:#6b7a99 }}
  table {{ border-collapse: collapse; width:100%; font-size:15px }}
  th, td {{ border:1px solid #21262d; padding:7px 12px; text-align:left; vertical-align:top }}
  th {{ background:#161b22; font-weight:600 }}
  tr:nth-child(2n) td {{ background:#0f141b }}
  .center {{ text-align:center }}
  .chips {{ display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:14px }}
  hr {{ border:0; border-top:1px solid #21262d; margin:34px 0 }}
  .foot {{ text-align:center; color:#6b7a99; font-size:13px }}
  /* theme swap — pure CSS */
  body.lightmode {{ background:#fff; color:#1f2328; color-scheme: light }}
  body.lightmode .toggle span {{ border-color:#d1d9e0; color:#2b5bd7 }}
  body.lightmode h3 {{ border-bottom-color:#d1d9e0 }}
  body.lightmode a {{ color:#2b5bd7 }}
  body.lightmode code {{ background:#f6f8fa }}
  body.lightmode pre {{ background:#f6f8fa; border-color:#d1d9e0; color:#1f2328 }}
  body.lightmode th {{ background:#f6f8fa }} body.lightmode th, body.lightmode td {{ border-color:#d1d9e0 }}
  body.lightmode tr:nth-child(2n) td {{ background:#fbfcfe }}
  body.lightmode .foot, body.lightmode .bar {{ color:#5b6b85 }}
  body.lightmode .toggle span {{ background:#fff }}
  body.lightmode .toggle input:checked + span {{ background:#eef2fa }}
  body.lightmode .toggle span.d {{ display:inline }}
</style>
</head>
<body>
<div class="wrap">

  <div class="bar">
    <span>PREVIEW · github.com/Yash-Tripath1 (not live yet)</span>
    <label class="toggle"><input type="checkbox" id="t"><span>themes: dark / light</span></label>
  </div>

  <div class="center">
    <div class="dark-only">{data_uri_img(banner_d, "banner")}</div>
    <div class="light-only">{data_uri_img(banner_l, "banner")}</div>
    <div class="chips">
      {chip("portfolio · anadi-dev.vercel.app")}
      {chip("linkedin · anadi_tripathi")}
      {chip("studio · glymph")}
    </div>
  </div>

  <h3>featured work</h3>
  <div class="center">
    <div class="dark-only">{data_uri_img(feat_d, "featured")}</div>
    <div class="light-only">{data_uri_img(feat_l, "featured")}</div>
  </div>

  <h3>about</h3>
  <ul>
    <li>co-founder of <strong>Glymph Studio</strong>, an indie dev collective that ships tools fast and open</li>
    <li>build end to end: a browser engine in Python, a language model trained from scratch, desktop apps on Electron</li>
    <li>dual degree: <strong>BCA</strong> at University of Lucknow + <strong>BS in Data Science</strong> at IIT Madras (online)</li>
    <li>into <strong>AI/ML, automation and cybersecurity</strong>; learning in public, one repo at a time</li>
    <li>reach me on <a href="https://www.linkedin.com/in/anadi-tripathi-4a33543a6">LinkedIn</a> or through the <a href="https://anadi-dev.vercel.app">portfolio</a></li>
  </ul>

  <h3>selected work</h3>
  <table>
    <tr><th>project</th><th>what it is</th><th>stack</th></tr>
    <tr><td><a href="#">anadi-dev</a></td><td>scroll flown 3D universe where every planet is a project, with browser synthesised audio and a hidden terminal</td><td>React 19 · three.js · TypeScript</td></tr>
    <tr><td><a href="#">memoir</a></td><td>turns WhatsApp chat exports into scrapbooks: custom parser plus a drag, resize and rotate canvas editor</td><td>React · Vite · Tailwind</td></tr>
    <tr><td><a href="#">Vynt</a></td><td>local first Y2K photo booth, 8 real time canvas filters, exports PNG and WebM, ships as a Windows installer</td><td>TypeScript · Canvas · Electron</td></tr>
    <tr><td><a href="#">Veyra</a></td><td>deterministic generative art: text hashed into colour and form, shareable through encrypted links, zero backend</td><td>HTML · JS · Web Crypto</td></tr>
    <tr><td><a href="#">Shakespeare-GPT</a></td><td>GPT style language model built and trained from scratch on ~80k lines of Shakespeare</td><td>Python</td></tr>
    <tr><td><a href="#">SurfGambit</a></td><td>a web browser written from scratch, following browser.engineering, own rendering pipeline</td><td>Python · Tkinter</td></tr>
  </table>

  <h3>stack</h3>
  <pre><span class="k">languages</span>:   [ Python, TypeScript, JavaScript, HTML/CSS, Luau ]
<span class="k">frameworks</span>:  [ React, Vite, Node/Express, Tailwind, Electron, three.js ]
<span class="k">ai_and_data</span>: [ LLM APIs (Groq), model training from scratch, llama.cpp, prompt design ]
<span class="k">tooling</span>:     [ Linux, Git, Docker, Firebase, Vercel, n8n, Ollama ]</pre>

  <h3>activity</h3>
  <div class="center">
    <div class="dark-only">{data_uri_img(act_d, "activity")}</div>
    <div class="light-only">{data_uri_img(act_l, "activity")}</div>
    <div style="height:16px"></div>
    <div class="dark-only">{snake_block_d}</div>
    <div class="light-only">{snake_block_l}</div>
  </div>

  <hr>
  <div class="foot"><sub>this profile rebuilds itself every night. banner, featured strip and activity graph are generated by the scripts in <code>/scripts</code></sub></div>
</div>

<script>
  // theme toggle: dark by default, .light-only starts hidden
  const style = document.createElement('style');
  style.textContent = '.light-only{{display:none}}body.lightmode .light-only{{display:block}}body.lightmode .dark-only{{display:none}}';
  document.head.appendChild(style);
  document.getElementById('t').addEventListener('change', e => {{
    document.body.classList.toggle('lightmode', e.target.checked);
  }});
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-snake", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "preview.html"))
    args = ap.parse_args()
    html = build(with_snake=not args.no_snake)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {args.out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
