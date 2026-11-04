#!/usr/bin/env python3
"""Fetch public, all-time open-source activity from GitHub's Search API.

Only PRs/issues authored by the user in repositories outside the excluded owners
are counted. By default, only the user's own account is excluded; organization
repositories (including Glymph Studio) count as external. Add --exclude-owner to
exclude an organization too.

No third-party service or Python dependency is required. GITHUB_TOKEN is used
when available. A failed or incomplete fetch never overwrites the last good JSON.

Usage:
    python3 scripts/fetch_open_source.py
    python3 scripts/fetch_open_source.py --exclude-owner glymph-studio
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USER = "Yash-Tripath1"
API = "https://api.github.com"
PAGE_SIZE = 100
SEARCH_LIMIT = 1000


class FetchError(RuntimeError):
    """The public data could not be fetched completely and safely."""


def validate_login(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", value):
        raise ValueError(f"Invalid GitHub owner name: {value!r}")
    return value


def owner_from_repository_url(url: str) -> str:
    match = re.fullmatch(r"https://api\.github\.com/repos/([^/]+/[^/]+)", url)
    if not match:
        raise FetchError(f"Unexpected repository URL in GitHub response: {url!r}")
    return match.group(1)


class GitHubClient:
    def __init__(self, token: str | None = None):
        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Yash-Tripath1-profile-open-source",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def get_json(self, url: str, params: dict | None = None) -> dict:
        if params:
            url += "?" + urllib.parse.urlencode(params)
        for attempt in range(4):
            request = urllib.request.Request(url, headers=self.headers)
            try:
                with urllib.request.urlopen(request, timeout=35) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                retryable = exc.code in (403, 429) or exc.code >= 500
                if not retryable or attempt == 3:
                    hint = " Check GITHUB_TOKEN / API rate limits." if exc.code in (401, 403, 429) else ""
                    raise FetchError(f"GitHub returned HTTP {exc.code}.{hint}") from exc
                delay = min(90, 2 ** (attempt + 1))
                retry_after = exc.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    delay = min(90, max(1, int(retry_after)))
                elif exc.headers.get("X-RateLimit-Remaining") == "0":
                    try:
                        reset = int(exc.headers.get("X-RateLimit-Reset", "0"))
                        delay = min(90, max(1, reset - int(time.time()) + 1))
                    except ValueError:
                        pass
                time.sleep(delay)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                if attempt == 3:
                    raise FetchError(f"Could not read GitHub response: {exc}") from exc
                time.sleep(2 ** (attempt + 1))
        raise FetchError("GitHub request exhausted its retries.")

    def search_page(self, query: str, page: int = 1) -> dict:
        for attempt in range(3):
            payload = self.get_json(f"{API}/search/issues", {
                "q": query, "per_page": PAGE_SIZE, "page": page,
                "sort": "created", "order": "asc",
            })
            if not payload.get("incomplete_results", False):
                if not isinstance(payload.get("items"), list):
                    raise FetchError("GitHub search response has no items list.")
                return payload
            time.sleep(attempt + 1)
        raise FetchError("GitHub search remained incomplete. Keeping the previous stats.")

    def search_all(self, query: str, start: date | None = None,
                   end: date | None = None) -> list[dict]:
        """Paginate, splitting creation-date ranges if a query exceeds 1,000 hits."""
        scoped = query
        if start is not None and end is not None:
            scoped += f" created:{start.isoformat()}..{end.isoformat()}"
        first = self.search_page(scoped)
        total = int(first["total_count"])
        if total >= SEARCH_LIMIT:
            start = start or date(2008, 1, 1)
            end = end or datetime.now(timezone.utc).date()
            if start >= end:
                raise FetchError("More than 1,000 results in one day; cannot safely partition.")
            middle = start + (end - start) / 2
            return (self.search_all(query, start, middle)
                    + self.search_all(query, middle + timedelta(days=1), end))

        items = list(first["items"])
        for page in range(2, math.ceil(total / PAGE_SIZE) + 1):
            items.extend(self.search_page(scoped, page)["items"])
        unique = {item["id"]: item for item in items}
        if len(unique) != total:
            raise FetchError(
                f"Search changed while paginating ({len(unique)} of {total} unique results). "
                "Keeping the previous stats; retry the workflow."
            )
        return list(unique.values())


def build_payload(user: str, prs: list[dict], issues: list[dict],
                  excluded_owners: set[str], fetched_at: datetime | None = None) -> dict:
    excluded = {owner.casefold() for owner in excluded_owners}
    excluded.add(user.casefold())
    repositories: dict[str, dict] = {}

    def accept(item: dict, kind: str) -> bool:
        if item.get("user", {}).get("login", "").casefold() != user.casefold():
            return False
        if ("pull_request" in item) != (kind == "pr"):
            return False
        name = owner_from_repository_url(item["repository_url"])
        if name.split("/")[0].casefold() in excluded:
            return False
        repo = repositories.setdefault(name, {
            "name": name, "url": "https://github.com/" + name,
            "prs_opened": 0, "prs_merged": 0, "issues_opened": 0,
        })
        if kind == "pr":
            repo["prs_opened"] += 1
            repo["prs_merged"] += int(bool(item["pull_request"].get("merged_at")))
        else:
            repo["issues_opened"] += 1
        return True

    accepted_prs = [item for item in prs if accept(item, "pr")]
    accepted_issues = [item for item in issues if accept(item, "issue")]
    merged = sum(bool(item["pull_request"].get("merged_at")) for item in accepted_prs)
    ordered = sorted(repositories.values(), key=lambda repo: (
        -repo["prs_merged"], -(repo["prs_opened"] + repo["issues_opened"]),
        repo["name"].casefold(),
    ))
    query = f"author:{user} is:public " + " ".join(
        f"-user:{owner}" for owner in sorted(excluded)
    )
    return {
        "schema_version": 1,
        "user": user,
        "fetched_at": (fetched_at or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "scope": {
            "visibility": "public",
            "period": "all-time",
            "excluded_owners": sorted(excluded),
            "issues_include_prs": False,
        },
        "stats": {
            "prs_opened": len(accepted_prs),
            "prs_merged": merged,
            "issues_opened": len(accepted_issues),
            "external_repos": len(ordered),
        },
        "repositories": ordered,
        "queries": {"prs": query + " is:pr", "issues": query + " is:issue"},
        "complete": True,
    }


def fetch(user: str, extra_exclusions: list[str] | None = None) -> dict:
    user = validate_login(user)
    excluded = {user.casefold()}
    for owner in extra_exclusions or []:
        excluded.add(validate_login(owner).casefold())
    client = GitHubClient(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    query = f"author:{user} is:public " + " ".join(
        f"-user:{owner}" for owner in sorted(excluded)
    )
    prs = client.search_all(query + " is:pr")
    issues = client.search_all(query + " is:issue")
    return build_payload(user, prs, issues, excluded)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--exclude-owner", action="append", default=[],
                        help="Additional repository owner to exclude; repeatable.")
    parser.add_argument("--out", type=Path, default=ROOT / "data/open-source.json")
    args = parser.parse_args()
    try:
        payload = fetch(args.user, args.exclude_owner)
        atomic_write(args.out, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    except (FetchError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    stats = payload["stats"]
    print(f"{stats['prs_opened']} external PRs opened / {stats['prs_merged']} merged / "
          f"{stats['issues_opened']} issues / {stats['external_repos']} repositories")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
