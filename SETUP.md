# Profile rebuild: monochrome edition

Target repo: **`Yash-Tripath1/Yash-Tripath1`** (the repo whose name equals your
username, default branch `main`).

## 0. If you already pushed the previous version

Some files from the last version are no longer used. Delete them first:

```powershell
cd C:\Users\tripa\Yash-Tripath1
git rm -r --ignore-unmatch data scripts/gen_hero.py scripts/fetch_contributions.py `
  assets/activity-dark.svg assets/activity-light.svg .github/workflows/update.yml
git commit -m "chore: drop custom activity graph and nightly workflow"
git push
```

(If that commit has nothing to remove, you never pushed those files. Fine either way.)

## 1. Copy the new files in

```powershell
cd C:\Users\tripa
Expand-Archive .\Downloads\profile-rebuild.zip -DestinationPath .\profile-extract -Force
Copy-Item .\profile-extract\profile-rebuild\.github .\Yash-Tripath1\ -Recurse -Force
Copy-Item .\profile-extract\profile-rebuild\*       .\Yash-Tripath1\ -Recurse -Force

cd .\Yash-Tripath1
Get-ChildItem -Force -Name      # must show .github, assets, scripts, README.md, SETUP.md
git status --short              # must show changes
git add .
git commit -m "feat: monochrome theme, rotating featured strip, no activity graph"
git push
```

## 2. Run the snake once

`Actions → Generate Snake → Run workflow`. It now writes **both** `snake.svg`
(light) and `snake-dark.svg` (dark) in a monochrome palette, so the README can
pick the right one per theme.

If the image looks stale after that, hard refresh (`Ctrl + Shift + R`); GitHub's
image proxy can cache for a few hours.

## 3. What's in the repo now

```
README.md                        profile readme
assets/
  banner-dark.svg                animated banner, dark
  banner-light.svg               animated banner, light
  featured-{dark,light}.svg      rotating featured strip
scripts/
  gen_banner.py                  banner generator
  gen_showcase.py                featured strip generator
  gen_preview.py                 local preview builder
.github/workflows/snake.yml      contribution snake, both themes
SETUP.md                         this file
```

Nothing else. No nightly workflow, because nothing needs refreshing anymore.

## 4. Editing things later

**featured strip content:** `scripts/gen_showcase.py`, the `PROJECTS` list. Each
entry is `(name, description, stack)`. Then:

```powershell
python3 scripts/gen_showcase.py
git add assets/featured-*.svg
git commit -m "chore: refresh featured"
git push
```

**banner terminal text:** `scripts/gen_banner.py`, the `LINES` list at the top.
Run `python3 scripts/gen_banner.py` and push `assets/`.

**about bullets and stack block:** plain Markdown in `README.md`.

**local preview:** `python3 scripts/gen_preview.py`, then open `preview.html`.
Real SVGs are inlined, so animation and the dark/light toggle work offline.

## 5. Theme rules

- Banner, featured strip and snake are monochrome: white on black for dark mode,
  black on white for light mode.
- The only colour on the profile is GitHub's own contribution graph, which stays
  green. That's the intended accent.
- No third party image services anywhere, so nothing can 404 or rate limit.
- No emoji headers and no em dashes in the visible text.
