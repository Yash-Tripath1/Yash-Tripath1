# GitHub profile: open-source mission control

Target repository: **`Yash-Tripath1/Yash-Tripath1`**, default branch `main`.

This update adds a custom open-source impact panel between **about** and
**featured work**. It uses real public GitHub data, not sample counters or a
third-party stats image. The existing banner, featured strip, activity scripts,
and contribution snake are retained. **Featured work** now also calls out the
Bendlab and sequential-matching research with direct repository and project-page
links above the rotating strip.

## What the panel shows

- **PRs opened:** public pull requests authored by you outside your own account.
- **PRs merged:** the subset of those pull requests that were merged.
- **Issues opened:** public issues authored by you outside your own account.
- **External repos:** distinct repositories reached by at least one of those PRs or issues.
- **Merge rate:** merged PRs divided by opened PRs.
- A small repository footprint and the last refresh date.

The default exclusion is your own account, `Yash-Tripath1`. Organization repos,
including `glymph-studio`, count as external unless explicitly excluded. Private
activity is not included. Closed-but-unmerged PRs do not count as merged.

## 1. Preview locally

Python 3.10+ is enough. There are no pip dependencies for the profile generators.

```bash
python3 scripts/fetch_open_source.py
python3 scripts/gen_open_source.py --update-readme
python3 scripts/gen_preview.py
python3 scripts/serve_preview.py --port 8000
```

Open `http://localhost:8000`, or open `preview.html` directly. The ZIP already
includes a generated preview with the real SVGs and badges embedded.

For an entirely offline rebuild:

```bash
python3 scripts/gen_open_source.py --update-readme
python3 scripts/gen_preview.py --offline
```

Offline mode uses local assets and a placeholder for the remote snake. The
prebuilt `preview.html` in this ZIP already contains the fetched snake.

## 2. Put the update on GitHub

Extract the ZIP and copy its contents into your existing profile repository,
including the hidden `.github` folder. Do not delete the existing `assets`,
`data`, or `scripts` folders. Then review and push:

```bash
cd Yash-Tripath1
git status
git diff
git add .github README.md SETUP.md .gitignore assets data scripts tests preview.html
git commit -m "feat: add open-source mission-control panel"
git push origin main
```

The new images are served from this repository, so the section appears after
the generated SVGs are pushed. GitHub's image proxy may cache an older image;
a hard refresh can help.

## 3. Automatic refresh

The existing **Refresh Profile Assets** workflow now also:

1. Runs the offline unit tests.
2. Fetches public PRs and issues using GitHub's Search API.
3. Rebuilds both mission-control SVGs.
4. Updates the README image alt text and verification links.
5. Commits changed assets, data, and README content.

It runs daily at **02:17 UTC**, on relevant pushes to `main`, and manually via
**Actions → Refresh Profile Assets → Run workflow**.

The workflow uses the built-in `GITHUB_TOKEN`; no additional secret is needed
for these public-only queries. A failed or incomplete fetch stops before the
new snapshot is written, so the last good data is not replaced with partial
counts. The existing calendar/banner refresh steps are unchanged.

## 4. Change the counting scope

To also exclude your studio's repositories, change the workflow's fetch command
and run the same command locally:

```bash
python3 scripts/fetch_open_source.py --user Yash-Tripath1 --exclude-owner glymph-studio
python3 scripts/gen_open_source.py --update-readme
```

`--exclude-owner` is repeatable. Owner matching is case-insensitive. Your own
account is always excluded. The exact queries and exclusions are recorded in
`data/open-source.json` and the README verification links.

## 5. Edit the design

- Panel layout and colors: `scripts/gen_open_source.py`, `PALETTES` and `build_svg`.
- Fetching and metric definitions: `scripts/fetch_open_source.py`.
- Profile copy and section order: `README.md`.
- Local preview styling: `scripts/gen_preview.py`.

After design changes:

```bash
python3 scripts/gen_open_source.py --update-readme
python3 scripts/gen_preview.py --offline
python3 -m unittest discover -s tests -v
```

Keep the `OPEN_SOURCE:START` and `OPEN_SOURCE:END` markers in the README. The
generator replaces only that section, preserving the rest of your profile.

## Files added or updated

```text
README.md                         new open-source section and updated footer
SETUP.md                          this guide
.github/workflows/update.yml      tests + public stats refresh + asset commits
assets/open-source-dark.svg       dark mission-control panel
assets/open-source-light.svg      light mission-control panel
data/open-source.json             last complete public-data snapshot
scripts/fetch_open_source.py      paginated GitHub Search API fetcher
scripts/gen_open_source.py        SVG and README section generator
scripts/gen_preview.py            README-driven, self-contained local preview
scripts/serve_preview.py          local preview server
tests/test_open_source.py         offline pipeline and preview tests
preview.html                      ready-to-open preview
```

## Verification

```bash
python3 -m unittest discover -s tests -v
```

The tests cover external-only counting, organization exclusions, PR/issue
separation, pagination, incomplete responses, zero states, SVG escaping,
README idempotency, and offline preview rendering. The preview is a local
approximation; GitHub controls the final Markdown rendering on your profile.
