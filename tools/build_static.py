"""
build_static.py - export PromptVault as plain HTML files for GitHub Pages.

GitHub Pages can only serve static files (HTML, CSS, JS). It cannot run Python
or Flask. This script runs the Flask app ONCE, on your computer (or in GitHub
Actions), saves every page as an HTML file, and writes the result to ./dist.
After that, no Python is needed: the browser does the searching, filtering,
copying, favorites and theme switching with the JavaScript in static/js/app.js.

Where do prompts come from?  data/prompts.json. Edit it, rebuild, and every
page (cards, categories, detail pages, sitemap) is regenerated from it.

How links work:  every internal link is rewritten to a RELATIVE path
(for example "../../static/css/style.css" or "explore/index.html"), so the
site works at ANY address: https://you.github.io/promptvault/, a custom
domain, or even by double-clicking dist/index.html. You do not need to know
the repository name at build time.

Usage:
    python tools/build_static.py                     # writes ./dist
    python tools/build_static.py --serve             # build, then preview at http://127.0.0.1:8000
    python tools/build_static.py --serve --base /promptvault
                                                     # preview exactly like a GitHub project site
    python tools/build_static.py --repo you/promptvault --site-url https://you.github.io/promptvault

The build FAILS (non-zero exit) if any page cannot be rendered or any
internal link points to a file that does not exist.
"""
import argparse
import http.server
import os
import re
import shutil
import socketserver
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app, store  # noqa: E402

URL_ATTR = re.compile(r'\b(href|src|action)="(/[^"]*)"')
ANY_ATTR = re.compile(r'\b(?:href|src|action)="([^"]*)"')


def _target(url_path):
    """Map a root-relative URL path to the file it is saved as in dist/."""
    p = url_path.lstrip("/")
    if p == "":
        return "index.html"
    last = p.rsplit("/", 1)[-1]
    if p.startswith("static/") or "." in last:      # real files: css, js, svg, json...
        return p
    return p.rstrip("/") + "/index.html"            # pages: /explore -> explore/index.html


def rewrite_links(html, prefix):
    """
    Turn root-relative links ("/explore?q=a") into prefix + file path
    ("../explore/index.html?q=a"). `prefix` is "../" repeated for the page's
    depth, or an absolute base such as "/promptvault/" (used only for 404.html,
    which GitHub Pages serves from any depth).
    """
    def fix(m):
        attr, url = m.group(1), m.group(2)
        if url.startswith("//"):
            return m.group(0)
        mm = re.match(r"^(/[^?#]*)(.*)$", url)
        return f'{attr}="{prefix}{_target(mm.group(1))}{mm.group(2)}"'
    return URL_ATTR.sub(fix, html)


def check_links(out):
    """Verify every internal link in dist/ resolves to a real file. Returns a list of problems."""
    problems = []
    for dirpath, _dirs, files in os.walk(out):
        for name in files:
            if not name.endswith(".html") or (dirpath == out and name == "404.html"):
                continue
            path = os.path.join(dirpath, name)
            html = open(path, encoding="utf-8").read()
            rel = os.path.relpath(path, out)
            for m in re.finditer(r'\b(?:href|src|action)="(/[^"]*)"', html):
                if not m.group(1).startswith("//"):
                    problems.append(f"{rel}: root-relative link left in page: {m.group(1)}")
            for url in ANY_ATTR.findall(html):
                if re.match(r"^(?:[a-z][a-z0-9+.-]*:|/|#|$)", url, re.I):
                    continue   # external, mailto:, data:, anchors, empty (root-relative links were reported above)
                clean = re.split(r"[?#]", url, maxsplit=1)[0]
                if not clean:
                    continue
                target = os.path.normpath(os.path.join(dirpath, clean))
                if os.path.isdir(target):
                    target = os.path.join(target, "index.html")
                if not os.path.isfile(target):
                    problems.append(f"{rel}: broken link -> {url}")
    return problems


def build(out, base="", repo=None, site_url=None, check=True):
    """Render every page into `out`. Returns the number of pages written."""
    base = "/" + base.strip("/") if base.strip("/") else ""
    config = {}
    if repo:
        config["GITHUB_REPO"] = repo
    if site_url:
        config["SITE_URL"] = site_url
    app = create_app(config)
    client = app.test_client()

    pages = ["/", "/explore", "/categories", "/contribute", "/about", "/github", "/favorites"]
    pages += [f"/category/{c['slug']}" for c in store.get_categories()]
    pages += [f"/prompt/{p['slug']}" for p in store.get_prompts()]

    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    for path in pages:
        res = client.get(path)
        if res.status_code != 200:
            raise SystemExit(f"Could not render {path}: HTTP {res.status_code}")
        target = _target(path)
        depth = target.count("/")          # how many folders deep the file is
        html = rewrite_links(res.get_data(as_text=True), "../" * depth)
        res.close()
        dest = os.path.join(out, target)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(html)

    # 404.html is served by GitHub Pages for ANY missing address, at any depth,
    # so relative links would break. It uses the absolute base path instead.
    res = client.get("/this-page-does-not-exist")
    with open(os.path.join(out, "404.html"), "w", encoding="utf-8") as f:
        f.write(rewrite_links(res.get_data(as_text=True), base + "/"))
    res.close()

    for name in ("robots.txt", "sitemap.xml"):
        res = client.get("/" + name)
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(res.get_data(as_text=True))
        res.close()

    os.makedirs(os.path.join(out, "data"))
    shutil.copy(store.DATA_FILE, os.path.join(out, "data", "prompts.json"))
    shutil.copytree(os.path.join(ROOT, "app", "static"), os.path.join(out, "static"))
    open(os.path.join(out, ".nojekyll"), "w").close()   # tell GitHub Pages not to run Jekyll

    if check:
        problems = check_links(out)
        if problems:
            raise SystemExit("Link check failed:\n  " + "\n  ".join(problems[:30]))
    return len(pages)


def serve(out, base, port):
    """Tiny preview server that behaves like GitHub Pages (including the /repo-name/ prefix)."""
    base = "/" + base.strip("/") if base.strip("/") else ""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=out, **kw)

        def translate_path(self, path):
            if base and path.startswith(base):
                path = path[len(base):] or "/"
            return super().translate_path(path)

        def do_GET(self):
            if base and self.path == "/":
                self.send_response(302)
                self.send_header("Location", base + "/")
                self.end_headers()
            elif base and not self.path.startswith(base + "/") and self.path != base:
                self.send_error(404, "Outside the base path (just like GitHub Pages)")
            else:
                super().do_GET()

        def log_message(self, *a):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"\nPreview: http://127.0.0.1:{port}{base}/   (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


def main():
    ap = argparse.ArgumentParser(description="Export PromptVault as a static site for GitHub Pages.")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"), help="output folder (default: ./dist)")
    ap.add_argument("--base", default="", help="repository sub-path, e.g. /promptvault (used for 404.html and --serve)")
    ap.add_argument("--repo", default=os.environ.get("PV_GITHUB_REPO"), help="GitHub repo as owner/name")
    ap.add_argument("--site-url", default=os.environ.get("PV_SITE_URL"), help="public address, used in sitemap and canonical links")
    ap.add_argument("--no-check", action="store_true", help="skip the link checker")
    ap.add_argument("--serve", action="store_true", help="after building, preview the site locally")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    n = build(args.out, args.base, args.repo, args.site_url, check=not args.no_check)
    print(f"Built {n} pages (+404, sitemap, data) into {args.out}")
    if not args.no_check:
        print("Link check passed: every internal link points to a real file.")
    if not args.repo:
        print("Note: no --repo given, so GitHub links say 'your-username/promptvault'.")
    if args.serve:
        serve(args.out, args.base, args.port)


if __name__ == "__main__":
    main()
