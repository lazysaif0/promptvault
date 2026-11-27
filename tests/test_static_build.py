"""
Tests for tools/build_static.py (the GitHub Pages export).
These prove the exported site is plain files with working relative links.
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build_static  # noqa: E402
from app import store  # noqa: E402


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


class StaticBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = os.path.join(cls.tmp.name, "dist")
        cls.pages = build_static.build(cls.out, base="/promptvault", repo="demo/promptvault",
                                       site_url="https://demo.github.io/promptvault")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_expected_files_exist(self):
        n_prompts, n_cats = len(store.get_prompts()), len(store.get_categories())
        self.assertEqual(self.pages, 7 + n_cats + n_prompts)
        for rel in ["index.html", "404.html", "robots.txt", "sitemap.xml", ".nojekyll",
                    "explore/index.html", "categories/index.html", "contribute/index.html",
                    "favorites/index.html", "about/index.html", "github/index.html",
                    "static/css/style.css", "static/js/app.js", "static/img/favicon.svg",
                    "data/prompts.json"]:
            self.assertTrue(os.path.isfile(os.path.join(self.out, rel)), rel)
        for p in store.get_prompts():
            self.assertTrue(os.path.isfile(os.path.join(self.out, "prompt", p["slug"], "index.html")))
        for c in store.get_categories():
            self.assertTrue(os.path.isfile(os.path.join(self.out, "category", c["slug"], "index.html")))

    def test_no_python_needed_at_runtime(self):
        """Every file is plain HTML/CSS/JS/JSON/text. No Python, templates or server code."""
        for dirpath, _d, files in os.walk(self.out):
            for f in files:
                self.assertNotIn(os.path.splitext(f)[1], (".py", ".pyc"), f)
        html = read(self.out, "index.html")
        self.assertNotIn("{{", html)
        self.assertNotIn("{%", html)

    def test_links_are_relative_and_resolve(self):
        self.assertEqual(build_static.check_links(self.out), [])

    def test_relative_prefix_matches_page_depth(self):
        self.assertIn('href="static/css/style.css"', read(self.out, "index.html"))
        self.assertIn('href="../static/css/style.css"', read(self.out, "explore", "index.html"))
        detail = read(self.out, "prompt", "prompt-improver", "index.html")
        self.assertIn('href="../../static/css/style.css"', detail)
        self.assertIn('src="../../static/js/app.js"', detail)
        self.assertIn('href="../../explore/index.html?q=', detail)

    def test_404_uses_absolute_base_path(self):
        html = read(self.out, "404.html")
        self.assertIn('href="/promptvault/static/css/style.css"', html)
        self.assertIn('href="/promptvault/index.html"', html)

    def test_site_url_and_repo_are_used(self):
        self.assertIn("https://demo.github.io/promptvault/prompt/prompt-improver", read(self.out, "sitemap.xml"))
        self.assertIn("https://github.com/demo/promptvault", read(self.out, "github", "index.html"))
        self.assertIn('rel="canonical" href="https://demo.github.io/promptvault/about"', read(self.out, "about", "index.html"))

    def test_prompts_json_is_published_unchanged(self):
        self.assertEqual(json.loads(read(self.out, "data", "prompts.json")),
                         json.loads(read(os.path.dirname(store.DATA_FILE), "prompts.json")))

    def test_explore_cards_carry_data_for_browser_side_search(self):
        html = read(self.out, "explore", "index.html")
        self.assertEqual(html.count('class="card win"'), len(store.get_prompts()))
        self.assertIn('data-prompt="', html)
        self.assertIn('id="explore-form"', html)

    def test_contribute_page_is_self_contained(self):
        html = read(self.out, "contribute", "index.html")
        self.assertIn('id="contribute-form"', html)
        self.assertIn('data-repo-url="https://github.com/demo/promptvault"', html)

    # ---------- the link rewriter and checker themselves ----------
    def test_rewrite_links(self):
        f = build_static.rewrite_links
        self.assertEqual(f('<a href="/">', ""), '<a href="index.html">')
        self.assertEqual(f('<a href="/explore?q=a b#x">', "../"), '<a href="../explore/index.html?q=a b#x">')
        self.assertEqual(f('<link href="/static/css/a.css">', "../../"), '<link href="../../static/css/a.css">')
        self.assertEqual(f('<a href="/data/prompts.json">', "../"), '<a href="../data/prompts.json">')
        self.assertEqual(f('<a href="https://x.dev/a">', "../"), '<a href="https://x.dev/a">')
        self.assertEqual(f('<a href="//cdn.x.dev/a">', "../"), '<a href="//cdn.x.dev/a">')
        self.assertEqual(f('<a href="#main">', "../"), '<a href="#main">')

    def test_link_checker_catches_problems(self):
        with tempfile.TemporaryDirectory() as t:
            with open(os.path.join(t, "index.html"), "w") as fh:
                fh.write('<a href="missing/index.html">x</a><a href="/oops">y</a><a href="#ok">z</a>')
            problems = build_static.check_links(t)
            self.assertEqual(len(problems), 2, problems)


if __name__ == "__main__":
    unittest.main()
