#!/usr/bin/env python3
"""Build a self-contained preview from the actual README, not a hardcoded copy.

Local SVGs, live snake SVGs and shields badges are embedded as data URIs. The
result makes no external asset requests and supports dark/light switching.
This renderer covers the Markdown/HTML subset used by this profile README.

Usage:
    python3 scripts/gen_preview.py
    python3 scripts/gen_preview.py --offline   # no network; graceful fallbacks
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fetch(url: str) -> bytes | None:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "profile-local-preview"})
        with urllib.request.urlopen(request, timeout=25) as response:
            return response.read(5_000_000)
    except Exception:
        return None


def image_bytes(src: str, offline: bool) -> tuple[bytes, str] | None:
    parsed = urllib.parse.urlparse(src)
    if parsed.scheme == "data":
        return None
    if parsed.netloc == "raw.githubusercontent.com":
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 5:
            # /owner/repo/ref/assets/file.svg -> ROOT/assets/file.svg
            local = ROOT.joinpath(*parts[3:]).resolve()
            if local.is_relative_to(ROOT) and local.is_file():
                return local.read_bytes(), "image/svg+xml" if local.suffix == ".svg" else "image/png"
    if offline:
        return None
    data = fetch(src)
    if data:
        mime = "image/svg+xml" if data.lstrip().startswith((b"<svg", b"<?xml")) else "image/png"
        return data, mime
    return None


def render_image(tag: str, offline: bool) -> str:
    attrs = dict(re.findall(r'([\w:-]+)\s*=\s*"([^"]*)"', tag))
    src, alt = attrs.get("src", ""), html.escape(attrs.get("alt", "Profile asset"), quote=True)
    if src.startswith("data:"):
        return tag
    embedded = image_bytes(src, offline)
    if not embedded:
        label = alt
        if "shields.io" in src:
            label = urllib.parse.unquote(src.split("/badge/")[-1].split("?")[0]).replace("-", " ")
        return f'<span class="asset-placeholder">{html.escape(label)}</span>'
    data, mime = embedded
    uri = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    if attrs.get("width") == "100%":
        style = "width:100%;height:auto;display:block"
    elif attrs.get("height", "").isdigit():
        style = f'height:{attrs["height"]}px;width:auto;vertical-align:middle'
    else:
        style = "max-width:100%;height:auto"
    return f'<img src="{uri}" alt="{alt}" style="{style}">'


def render_html_block(block: str, offline: bool) -> str:
    def picture(match: re.Match) -> str:
        html_block = match.group(0)
        sources = re.findall(r'<source\b[^>]*>', html_block)
        image = re.search(r'<img\b[^>]*>', html_block)
        if not image:
            return html_block
        dark = light = None
        for source in sources:
            src = re.search(r'srcset="([^"]+)"', source)
            if not src:
                continue
            tag = re.sub(r'\bsrc="[^"]*"', f'src="{src.group(1)}"', image.group(0))
            if "dark" in source:
                dark = render_image(tag, offline)
            elif "light" in source:
                light = render_image(tag, offline)
        if dark or light:
            dark, light = dark or light, light or dark
            return f'<div class="dark-only">{dark}</div><div class="light-only">{light}</div>'
        return render_image(image.group(0), offline)

    block = re.sub(r"<picture\b[^>]*>.*?</picture>", picture, block, flags=re.DOTALL)
    block = re.sub(r"<img\b[^>]*>", lambda m: render_image(m.group(0), offline), block)
    block = re.sub(r'<a\s+href="([^"]+)"',
                   r'<a href="\1" target="_blank" rel="noopener noreferrer"', block)
    return block


def inline_markdown(text: str) -> str:
    codes: list[str] = []

    def code(match: re.Match) -> str:
        codes.append("<code>" + html.escape(match.group(1)) + "</code>")
        return f"\x00CODE{len(codes)-1}\x00"

    text = re.sub(r"`([^`]+)`", code, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
                  r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', text)
    for index, code_html in enumerate(codes):
        text = text.replace(f"\x00CODE{index}\x00", code_html)
    return text


def render_markdown(markdown: str, offline: bool = False) -> str:
    """Render the headings, lists, fences and HTML blocks used in this README."""
    lines = markdown.splitlines()
    output: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("<!--"):
            i += 1
            continue
        if line.strip().startswith("<div"):
            block, depth = [], 0
            while i < len(lines):
                current = lines[i]
                block.append(current)
                depth += len(re.findall(r"<div\b", current)) - len(re.findall(r"</div>", current))
                i += 1
                if depth <= 0:
                    break
            output.append(render_html_block("\n".join(block), offline))
            continue
        if line.startswith("```"):
            language = line[3:].strip()
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            code_html = html.escape("\n".join(code))
            if language == "yaml":
                code_html = re.sub(r"(?m)^([a-z_]+)(:)", r'<span class="code-key">\1</span>\2', code_html)
            output.append(f'<pre><code class="language-{html.escape(language)}">{code_html}</code></pre>')
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level, text = len(heading.group(1)), heading.group(2)
            slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            output.append(f'<h{level} id="{slug}">{inline_markdown(text)}</h{level}>')
            i += 1
            continue
        if re.fullmatch(r"\s*---+\s*", line):
            output.append("<hr>")
            i += 1
            continue
        if line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append("<li>" + inline_markdown(lines[i][2:].strip()) + "</li>")
                i += 1
            output.append("<ul>" + "".join(items) + "</ul>")
            continue
        paragraph = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|```|- |<div|<!--|---+$)", lines[i]):
            paragraph.append(lines[i].strip())
            i += 1
        if paragraph:
            output.append("<p>" + inline_markdown(" ".join(paragraph)) + "</p>")
        else:
            i += 1
    return "\n".join(output)


def build(offline: bool = False, with_snake: bool = True) -> str:
    markdown = (ROOT / "README.md").read_text(encoding="utf-8")
    content = render_markdown(markdown, offline=offline or not with_snake)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Local preview of Yash-Tripath1's GitHub profile with live open-source contribution counters.">
<title>Yash-Tripath1 · GitHub profile preview</title>
<style>
  :root {{
    color-scheme:dark; --page:#0d1117; --canvas:#0d1117; --border:#30363d;
    --text:#e6edf3; --muted:#9198a1; --link:#8cb4ff; --code:#161b22; --accent:#c6f477;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:30px 20px 50px; background:var(--page); color:var(--text);
    font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
    transition:background .2s,color .2s; }}
  body.lightmode {{ color-scheme:light; --page:#f6f8fa; --canvas:#fff; --border:#d1d9e0;
    --text:#1f2328; --muted:#59636e; --link:#0969da; --code:#f6f8fa; --accent:#397313; }}
  .wrap {{ max-width:960px; margin:0 auto; }}
  .toolbar {{ display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:14px; }}
  .identity {{ display:flex; align-items:center; gap:10px; min-width:0; font:13px ui-monospace,SFMono-Regular,Consolas,monospace; }}
  .identity svg {{ flex:none; color:var(--muted); }}
  .identity a {{ color:var(--text); text-decoration:none; }}
  .identity .slash {{ color:var(--muted); }}
  .theme {{ display:flex; align-items:center; gap:9px; flex:none; cursor:pointer; color:var(--muted); font-size:12px; }}
  .theme input {{ position:absolute; opacity:0; width:1px; height:1px; }}
  .switch {{ width:38px; height:22px; padding:3px; border:1px solid var(--border); border-radius:20px; background:var(--code); }}
  .switch::after {{ content:""; display:block; width:14px; height:14px; border-radius:50%; background:var(--muted); transition:transform .2s,background .2s; }}
  .theme input:checked + .switch::after {{ transform:translateX(16px); background:var(--accent); }}
  .theme input:focus-visible + .switch {{ outline:2px solid var(--link); outline-offset:3px; }}
  .preview-note {{ display:flex; align-items:center; gap:8px; margin:0 0 18px; color:var(--muted); font:11px ui-monospace,SFMono-Regular,Consolas,monospace; letter-spacing:.35px; }}
  .status-dot {{ width:6px; height:6px; border-radius:50%; background:var(--accent); box-shadow:0 0 10px color-mix(in srgb,var(--accent) 35%,transparent); }}
  .markdown-body {{ background:var(--canvas); border:1px solid var(--border); border-radius:12px; padding:30px 32px; overflow:hidden; }}
  h1,h2,h3,h4 {{ line-height:1.3; margin:30px 0 16px; font-weight:600; }}
  h3 {{ font-size:20px; padding-bottom:9px; border-bottom:1px solid var(--border); }}
  p,li {{ font-size:15px; }}
  p {{ margin:0 0 16px; }}
  ul {{ margin:0 0 20px; padding-left:25px; }}
  li {{ margin:5px 0; padding-left:3px; }}
  li::marker {{ color:var(--muted); }}
  a {{ color:var(--link); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  code {{ background:var(--code); padding:.16em .38em; border-radius:5px; font:12.5px ui-monospace,SFMono-Regular,Consolas,monospace; }}
  pre {{ background:var(--code); border:1px solid var(--border); border-radius:8px; padding:16px 18px; overflow:auto; line-height:1.8; }}
  pre code {{ padding:0; background:none; }}
  .code-key {{ color:var(--link); }}
  hr {{ border:0; border-top:1px solid var(--border); margin:28px 0; }}
  sub {{ color:var(--muted); font-size:11.5px; }}
  .light-only {{ display:none; }}
  body.lightmode .light-only {{ display:block; }}
  body.lightmode .dark-only {{ display:none; }}
  .asset-placeholder {{ display:inline-block; padding:18px; border:1px dashed var(--border); border-radius:8px; color:var(--muted); font-size:13px; }}
  .footer {{ margin-top:16px; text-align:center; color:var(--muted); font-size:11px; }}
  @media(max-width:640px) {{
    body {{ padding:18px 10px 30px; }}
    .toolbar {{ flex-wrap:wrap; gap:12px; }}
    .identity {{ font-size:11px; }}
    .markdown-body {{ padding:18px 14px; border-radius:9px; }}
    .preview-note {{ font-size:10px; letter-spacing:0; }}
    p,li {{ font-size:14px; }}
    pre {{ padding:12px; }}
  }}
  @media(prefers-reduced-motion:reduce) {{ *,*::after {{ transition:none!important; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header class="toolbar">
    <div class="identity">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .8a11.2 11.2 0 0 0-3.54 21.83c.56.1.77-.24.77-.54v-2.17c-3.13.68-3.79-1.33-3.79-1.33-.51-1.3-1.25-1.65-1.25-1.65-1.02-.7.08-.69.08-.69 1.13.08 1.72 1.16 1.72 1.16 1 1.72 2.63 1.22 3.27.93.1-.73.39-1.22.71-1.5-2.5-.28-5.13-1.25-5.13-5.57 0-1.23.44-2.24 1.16-3.03-.12-.28-.5-1.43.11-2.98 0 0 .95-.3 3.08 1.16a10.7 10.7 0 0 1 5.61 0c2.13-1.46 3.07-1.16 3.07-1.16.61 1.55.23 2.7.11 2.98.72.79 1.16 1.8 1.16 3.03 0 4.33-2.64 5.28-5.15 5.56.4.35.76 1.03.76 2.08v3.18c0 .3.2.65.78.54A11.2 11.2 0 0 0 12 .8Z"/></svg>
      <a href="https://github.com/Yash-Tripath1" target="_blank" rel="noopener noreferrer">Yash-Tripath1</a>
      <span class="slash">/</span><span>README.md</span>
    </div>
    <label class="theme"><span>Dark</span><input id="theme-toggle" type="checkbox" role="switch" aria-label="Use light theme"><span class="switch" aria-hidden="true"></span><span>Light</span></label>
  </header>
  <div class="preview-note"><span class="status-dot"></span>LOCAL PREVIEW <span>·</span> REAL PUBLIC GITHUB DATA <span>·</span> NOT YET PUSHED</div>
  <article class="markdown-body">{content}</article>
  <div class="footer">Built from README.md · Assets embedded for offline viewing · GitHub controls the final rendering</div>
</div>
<script>
  const toggle = document.getElementById('theme-toggle');
  toggle.addEventListener('change', () => {{
    document.body.classList.toggle('lightmode', toggle.checked);
  }});
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-snake", action="store_true", help="Skip remote snake/asset fetches.")
    parser.add_argument("--offline", action="store_true", help="Use only local assets.")
    parser.add_argument("--out", type=Path, default=ROOT / "preview.html")
    args = parser.parse_args()
    content = build(offline=args.offline, with_snake=not args.no_snake)
    args.out.write_text(content, encoding="utf-8")
    print(f"wrote {args.out} ({len(content):,} characters)")


if __name__ == "__main__":
    main()
