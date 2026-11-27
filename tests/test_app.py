"""
Tests for the Flask app (used for local development and as the source for the static build).
Run:   python -m unittest discover tests
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, store  # noqa: E402


class PromptVaultTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    # ---------- data ----------
    def test_has_30_plus_prompts_and_12_categories(self):
        self.assertGreaterEqual(len(store.get_prompts()), 30)
        self.assertEqual(len(store.get_categories()), 12)
        for c in store.get_categories():
            self.assertGreater(c["count"], 0, c["slug"])

    # ---------- every page ----------
    def test_all_pages_load(self):
        paths = ["/", "/explore", "/categories", "/contribute", "/about", "/github", "/favorites",
                 "/robots.txt", "/sitemap.xml", "/api/prompts", "/data/prompts.json"]
        paths += [f"/category/{c['slug']}" for c in store.get_categories()]
        paths += [f"/prompt/{p['slug']}" for p in store.get_prompts()]
        for p in paths:
            r = self.client.get(p)
            self.assertEqual(r.status_code, 200, p)
            r.close()

    def test_unknown_pages_404(self):
        for p in ("/nope", "/prompt/nope", "/category/nope"):
            self.assertEqual(self.client.get(p).status_code, 404, p)

    def test_no_broken_internal_links(self):
        """Crawl every page and make sure each internal link resolves."""
        seen, queue = set(), ["/"]
        while queue:
            path = queue.pop()
            if path in seen:
                continue
            seen.add(path)
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"broken link: {path}")
            if "text/html" in res.content_type:
                for href in re.findall(r'href="(/[^"#]*)"', res.get_data(as_text=True)):
                    queue.append(href)
            res.close()
        self.assertGreater(len(seen), 60)

    def test_seo_title_and_description_on_every_page(self):
        for p in store.get_prompts():
            html = self.client.get(f"/prompt/{p['slug']}").get_data(as_text=True)
            self.assertRegex(html, r"<title>.+ - PromptVault</title>")
            self.assertIn('<meta name="description"', html)
        for path in ["/", "/explore", "/categories", "/contribute", "/about", "/github"]:
            html = self.client.get(path).get_data(as_text=True)
            self.assertRegex(html, r"<title>.+</title>", path)
            self.assertRegex(html, r'<meta name="description" content=".{20,}', path)

    def test_pixel_theme_is_wired_up(self):
        html = self.client.get("/").get_data(as_text=True)
        for needle in ("Press+Start+2P", "VT323", "Silkscreen", 'id="px-heart-fill"', "win-bar"):
            self.assertIn(needle, html)

    # ---------- search / filter / sort ----------
    def _matches(self, **kw):
        return [p["slug"] for p, ok in store.search(**kw) if ok]

    def test_search_by_title_description_and_body(self):
        self.assertIn("resume-bullet-booster", self._matches(q="resume"))
        self.assertIn("scamper-idea-generator", self._matches(q="substitute"))   # only in prompt text
        self.assertEqual(self._matches(q="zzzxqy"), [])

    def test_all_words_must_match(self):
        both = self._matches(q="email tone")
        self.assertIn("email-tone-rewriter", both)
        self.assertNotIn("resume-bullet-booster", both)

    def test_title_match_ranks_first(self):
        self.assertEqual(self._matches(q="reviewer")[0], "senior-code-reviewer")

    def test_filter_category_and_difficulty(self):
        for slug in self._matches(category="programming-development"):
            self.assertEqual(store.get_prompt(slug)["category"], "programming-development")
        for slug in self._matches(difficulty="Advanced"):
            self.assertEqual(store.get_prompt(slug)["difficulty"], "Advanced")
        combined = self._matches(category="career-professional-growth", difficulty="Advanced")
        self.assertEqual(combined, ["salary-negotiation-script"])

    def test_sorting(self):
        pop = [store.get_prompt(s)["popularity"] for s in self._matches(sort="popular")]
        self.assertEqual(pop, sorted(pop, reverse=True))
        titles = [store.get_prompt(s)["title"].lower() for s in self._matches(sort="alpha")]
        self.assertEqual(titles, sorted(titles))
        dates = [store.get_prompt(s)["date_added"] for s in self._matches(sort="newest")]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_explore_route_applies_filters(self):
        expected = len(self._matches(category="general-purpose", difficulty="Beginner"))
        self.assertGreater(expected, 0)
        html = self.client.get("/explore?category=general-purpose&difficulty=Beginner").get_data(as_text=True)
        self.assertIn(f"<strong>{expected}</strong> prompts", html)
        # Non-matching cards stay in the page, hidden, so JavaScript can re-filter with no server.
        self.assertEqual(html.count('<article class="card win" hidden'), len(store.get_prompts()) - expected)

    def test_related_prompts(self):
        p = store.get_prompt("senior-code-reviewer")
        rel = store.related(p, 3)
        self.assertEqual(len(rel), 3)
        self.assertNotIn(p["slug"], [r["slug"] for r in rel])

    # ---------- contribute: handled in the browser, not on a server ----------
    def test_contribute_page_has_client_side_form(self):
        html = self.client.get("/contribute").get_data(as_text=True)
        self.assertIn('id="contribute-form"', html)
        self.assertIn('data-slugs=', html)
        self.assertIn("prompt-improver", html)          # existing slugs, for duplicate detection
        for cat in store.get_categories():
            self.assertIn(f'value="{cat["slug"]}"', html)

    def test_contribute_does_not_accept_posts(self):
        """There is no server-side saving, so a static host and Flask behave identically."""
        self.assertEqual(self.client.post("/contribute", data={"title": "x"}).status_code, 405)

    def test_raw_data_route_matches_file(self):
        with open(store.DATA_FILE, "rb") as f:
            self.assertEqual(self.client.get("/data/prompts.json").data, f.read())


if __name__ == "__main__":
    unittest.main()
