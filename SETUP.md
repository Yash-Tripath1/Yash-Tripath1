# Profile rebuild: where to push

Target repo: **`Yash-Tripath1/Yash-Tripath1`** (the special repo whose name equals
your username, default branch `main`). Right now it only contains `README.md` and
`.github/workflows/snake.yml`, so everything else is new.

## 1. Push the files

Paste this in Git Bash / PowerShell, one block:

```bash
git clone https://github.com/Yash-Tripath1/Yash-Tripath1.git
cd Yash-Tripath1

# copy from this workspace folder: README.md, assets/, data/, scripts/, .github/, SETUP.md
# (drag the folders in Explorer, or:)
# cp -r /path/to/this/folder/{README.md,assets,data,scripts,.github,SETUP.md} .

git add .
git commit -m "feat: rebuild profile (custom animated banner, featured strip, self hosted activity graph)"
git push
```

That's it for the upload. Until you push `assets/`, the images 404.

## 2. Two settings clicks

1. `Settings → Actions → General → Workflow permissions` → **Read and write permissions** → Save.
   (This is what let you commit the snake before. `update.yml` needs it too.)
2. `Actions → Refresh Profile Assets → Run workflow`, then
   `Actions → Generate Snake → Run workflow` once so both snake themes exist.

Then open your profile with a hard refresh (`Ctrl + Shift + R`).

## 3. What each generated image is

| file | README section | how it updates |
| :--- | :--- | :--- |
| `assets/banner-{dark,light}.svg` | top banner, animated terminal | nightly job |
| `assets/featured-{dark,light}.svg` | rotating featured strip | nightly job, content from `scripts/gen_showcase.py` |
| `assets/activity-{dark,light}.svg` | contribution graph, animated | nightly job, pulls live data |
| `output` branch snake | bottom animation | every 12 hours |

## 4. Editing things later

**featured strip content** (the rotating list): `scripts/gen_showcase.py`, the
`PROJECTS` list. Each line is `(name, description, stack)`. Then:

```bash
python3 scripts/gen_showcase.py
git add assets/featured-*.svg && git commit -m "chore: refresh featured" && git push
```

**banner text** (the terminal commands): `scripts/gen_banner.py`, the `LINES`
list at the top. Then run `python3 scripts/gen_banner.py` and push `assets/`.

**projects table, about bullets, stack block**: plain Markdown in `README.md`.

**activity graph numbers**: nothing to do, the workflow recalculates totals and
streaks from your public calendar every day at 02:17 UTC.

**local preview before pushing**: `python3 scripts/gen_preview.py` then open
`preview.html`. It inlines the real SVGs, so animation and the dark/light toggle
work offline.

## 5. Things that intentionally are not there

- no GitHub stats / streak cards and no view counter: those services kept
  returning errors and blank images
- no third party graph service for the heatmap: it used to return `402` and break.
  It is generated from your own repo data now, so it cannot go dark
- no emoji headers and no em dashes anywhere in the visible text
