"""Offline tests for the contribution pipeline and local preview."""

import copy
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_open_source as fetcher
import gen_open_source as generator
import gen_preview as preview
import gen_showcase as showcase


def item(number, repo="other/project", kind="pr", merged=False, author="Yash-Tripath1"):
    value = {
        "id": number,
        "number": number,
        "repository_url": "https://api.github.com/repos/" + repo,
        "user": {"login": author},
    }
    if kind == "pr":
        value["pull_request"] = {"merged_at": "2026-11-01T00:00:00Z" if merged else None}
    return value


def payload():
    return fetcher.build_payload(
        "Yash-Tripath1",
        [item(1, merged=True), item(2, "another/repo"), item(3, "Yash-Tripath1/own")],
        [item(4, kind="issue"), item(5, "Third/repo", kind="issue")],
        {"Yash-Tripath1"},
        datetime(2026, 11, 4, tzinfo=timezone.utc),
    )


class FetchTests(unittest.TestCase):
    def test_external_counts_and_repository_union(self):
        data = payload()
        self.assertEqual(data["stats"], {
            "prs_opened": 2, "prs_merged": 1, "issues_opened": 2, "external_repos": 3,
        })
        self.assertEqual(data["repositories"][0]["name"], "other/project")
        self.assertEqual(data["repositories"][0]["issues_opened"], 1)
        self.assertTrue(data["complete"])

    def test_extra_owner_exclusion_is_case_insensitive(self):
        data = fetcher.build_payload("Yash-Tripath1", [item(1, "Glymph-Studio/tool")],
                                     [item(2, "GLYMPH-STUDIO/other", kind="issue")],
                                     {"glymph-studio"})
        self.assertEqual(data["stats"]["external_repos"], 0)
        self.assertEqual(data["stats"]["prs_opened"], 0)

    def test_prs_are_not_double_counted_as_issues(self):
        data = fetcher.build_payload("Yash-Tripath1", [], [item(1)], {"Yash-Tripath1"})
        self.assertEqual(data["stats"]["issues_opened"], 0)

    def test_other_authors_are_not_counted(self):
        data = fetcher.build_payload("Yash-Tripath1", [item(1, author="someone")], [], set())
        self.assertEqual(data["stats"]["prs_opened"], 0)

    def test_pagination_deduplicates(self):
        class FakeClient(fetcher.GitHubClient):
            def search_page(self, query, page=1):
                items = [item(i) for i in range(100)] if page == 1 else [item(99), item(100)]
                return {"total_count": 101, "incomplete_results": False, "items": items}
        result = FakeClient().search_all("test")
        self.assertEqual(len(result), 101)

    def test_thousand_result_boundary_is_partitioned(self):
        class FakeClient(fetcher.GitHubClient):
            def search_page(self, query, page=1):
                if "created:" not in query:
                    return {"total_count": 1000, "incomplete_results": False, "items": []}
                number = 1 if "..2017-" in query else 2
                return {"total_count": 1, "incomplete_results": False, "items": [item(number)]}
        result = FakeClient().search_all("test")
        self.assertEqual({value["id"] for value in result}, {1, 2})

    def test_incomplete_search_fails_without_writing(self):
        class FakeClient(fetcher.GitHubClient):
            def search_page(self, query, page=1):
                return {"total_count": 1, "incomplete_results": True, "items": []}
        with patch.object(fetcher.time, "sleep"), self.assertRaises(fetcher.FetchError):
            FakeClient().search_all("test")

    def test_invalid_owner_rejected(self):
        with self.assertRaises(ValueError):
            fetcher.validate_login("owner is:private")


class GeneratorTests(unittest.TestCase):
    def test_both_themes_are_valid_svg_with_real_stats(self):
        for theme in ("dark", "light"):
            svg = generator.build_svg(payload(), theme)
            root = ET.fromstring(svg)
            self.assertEqual(root.attrib["viewBox"], "0 0 1200 420")
            self.assertIn("OPEN SOURCE", svg)
            self.assertIn("50%", svg)
            self.assertNotIn("<script", svg)
            self.assertNotIn("http://", svg.replace('xmlns="http://www.w3.org/2000/svg"', ''))

    def test_zero_state_has_no_division_by_zero(self):
        data = fetcher.build_payload("Yash-Tripath1", [], [], set())
        svg = generator.build_svg(data)
        self.assertIn("No external PRs yet", svg)
        self.assertIn("The next contribution starts here.", svg)

    def test_repository_names_are_escaped(self):
        data = fetcher.build_payload("Yash-Tripath1", [item(1, 'other/<script>"repo')], [], set())
        svg = generator.build_svg(data)
        ET.fromstring(svg)
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)

    def test_invalid_counts_rejected(self):
        data = copy.deepcopy(payload())
        data["stats"]["prs_merged"] = 99
        with self.assertRaises(ValueError):
            generator.build_svg(data)

    def test_readme_update_is_idempotent(self):
        original = "before\n" + generator.START + "\nold\n" + generator.END + "\nafter"
        block = generator.readme_block(payload())
        once = generator.update_readme(original, block)
        self.assertEqual(generator.update_readme(once, block), once)
        self.assertIn("pull requests merged: 1", once)
        self.assertTrue(once.startswith("before"))
        self.assertTrue(once.endswith("after"))

    def test_missing_markers_fail_clearly(self):
        with self.assertRaises(ValueError):
            generator.update_readme("# Profile", generator.readme_block(payload()))

    def test_checked_in_snapshot_is_complete_and_consistent(self):
        data = json.loads((ROOT / "data/open-source.json").read_text())
        generator.validate(data)
        self.assertEqual(data["scope"]["visibility"], "public")
        self.assertFalse(data["scope"]["issues_include_prs"])


class FeaturedWorkTests(unittest.TestCase):
    def test_readme_calls_out_both_research_projects(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        section = text.split("### featured work", 1)[1].split("### stack", 1)[0]
        self.assertIn("https://github.com/Yash-Tripath1/Bendlab", section)
        self.assertIn("https://github.com/Yash-Tripath1/sequential-matching-public-simulator-lab", section)
        self.assertIn("https://yash-tripath1.github.io/Bendlab/", section)
        self.assertIn("https://yash-tripath1.github.io/sequential-matching-public-simulator-lab/", section)

    def test_showcase_strip_includes_research_projects(self):
        names = [project[0] for project in showcase.PROJECTS]
        self.assertIn("Bendlab", names)
        self.assertIn("sequential-matching", names)
        for theme in ("dark", "light"):
            svg = showcase.build(theme, preview=True)
            ET.fromstring(svg)
            self.assertIn("Bendlab", svg)
            self.assertIn("sequential-matching", svg)


class PreviewTests(unittest.TestCase):
    def test_offline_preview_uses_actual_readme_and_embedded_assets(self):
        html = preview.build(offline=True)
        self.assertIn("running open research alongside the apps", html)
        self.assertLess(html.index('id="open-source"'), html.index('id="featured-work"'))
        self.assertIn("data:image/svg+xml;base64,", html)
        self.assertNotIn('src="https://', html)
        self.assertIn('id="theme-toggle"', html)
        self.assertIn('role="switch"', html)

    def test_code_fences_and_inline_markdown(self):
        html = preview.render_markdown("### hello\n\n- **bold** and `code`\n\n```yaml\nkey: value\n```", offline=True)
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<code>code</code>", html)
        self.assertIn('class="code-key"', html)


if __name__ == "__main__":
    unittest.main()
