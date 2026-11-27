"""
routes.py - every page and endpoint of PromptVault.

A "route" connects a URL (like /explore) to a Python function that returns
a page. Pages are built from Jinja2 templates in app/templates/.
"""
from datetime import datetime

from flask import (Blueprint, abort, current_app, jsonify, render_template,
                   request, Response, send_file, url_for)

from . import store

bp = Blueprint("main", __name__)


def register_helpers(app):
    """Make some values available in every template."""

    @app.context_processor
    def inject_globals():
        repo = current_app.config["GITHUB_REPO"]
        return {
            "site_name": current_app.config["SITE_NAME"],
            "github_repo": repo,
            "github_url": f"https://github.com/{repo}",
            "all_categories": store.get_categories(),
            "difficulties": store.DIFFICULTIES,
            "year": datetime.now().year,
        }

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html", title="Page not found"), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("404.html", title="Submission too large",
                               message="That submission was too large."), 413


# ---------------------------------------------------------------- pages
@bp.route("/")
def home():
    return render_template(
        "home.html",
        title="PromptVault - Open-source library of AI prompts",
        description="Discover, copy and contribute high-quality prompts for ChatGPT, Claude, Gemini and other AI assistants.",
        categories=store.get_categories(),
        featured=store.featured(6),
        recent=store.recent(6),
        total=len(store.get_prompts()),
    )


@bp.route("/explore")
def explore():
    q = request.args.get("q", "").strip()[:100]
    category = request.args.get("category", "")
    difficulty = request.args.get("difficulty", "")
    sort = request.args.get("sort", "")
    if category and not store.get_category(category):
        category = ""
    if difficulty not in store.DIFFICULTIES:
        difficulty = ""
    if sort not in store.SORT_OPTIONS and sort != "relevance":
        sort = ""
    results = store.search(q, category, difficulty, sort)
    return render_template(
        "explore.html",
        title="Explore prompts - PromptVault",
        description="Search and filter the PromptVault library by keyword, category and difficulty.",
        results=results,
        matched=sum(1 for _, ok in results if ok),
        q=q, category=category, difficulty=difficulty, sort=sort or ("relevance" if q else "newest"),
        sort_options=store.SORT_OPTIONS,
    )


@bp.route("/categories")
def categories():
    return render_template(
        "categories.html",
        title="Prompt categories - PromptVault",
        description="Browse AI prompts by category: education, programming, career, writing and more.",
        categories=store.get_categories(),
    )


@bp.route("/category/<slug>")
def category(slug):
    cat = store.get_category(slug)
    if not cat:
        abort(404)
    prompts = [p for p in store.get_prompts() if p["category"] == slug]
    prompts.sort(key=lambda p: -p["popularity"])
    return render_template(
        "category.html",
        title=f"{cat['name']} prompts - PromptVault",
        description=cat["description"],
        cat=cat, prompts=prompts,
    )


@bp.route("/prompt/<slug>")
def prompt_detail(slug):
    p = store.get_prompt(slug)
    if not p:
        abort(404)
    return render_template(
        "prompt.html",
        title=f"{p['title']} - PromptVault",
        description=p["description"],
        p=p, related=store.related(p, 3),
    )


@bp.route("/favorites")
def favorites():
    # Favorites are stored in the visitor's browser (localStorage). The server
    # renders every prompt hidden; app.js reveals only the saved ones.
    return render_template(
        "favorites.html",
        title="Your favorites - PromptVault",
        description="Prompts you have saved in this browser.",
        prompts=store.get_prompts(),
    )


@bp.route("/about")
def about():
    return render_template(
        "about.html",
        title="About PromptVault",
        description="Why PromptVault exists, how it works and how it is built.",
    )


@bp.route("/github")
def github_page():
    return render_template(
        "github.html",
        title="Contribute on GitHub - PromptVault",
        description="Step-by-step guide to adding a prompt to PromptVault with a GitHub pull request.",
    )


# ---------------------------------------------------------------- contribute
@bp.route("/contribute")
def contribute():
    """
    The Contribute page is a plain page: the form is handled entirely in the
    browser (app.js). It builds a JSON entry that can be copied, downloaded or
    sent as a pre-filled GitHub issue. Nothing is posted to a server, so this
    works identically on a static host like GitHub Pages.
    """
    return render_template(
        "contribute.html",
        title="Contribute a prompt - PromptVault",
        description="Submit your own AI prompt to PromptVault with a short form or a GitHub pull request.",
        slugs=[p["slug"] for p in store.get_prompts()],
    )


# ---------------------------------------------------------------- API + SEO
@bp.route("/api/prompts")
def api_prompts():
    """Read-only JSON API with the same filters as the Explore page."""
    results = store.search(request.args.get("q", ""), request.args.get("category", ""),
                           request.args.get("difficulty", ""), request.args.get("sort", ""))
    keep = ("slug", "title", "description", "category", "tags", "difficulty",
            "prompt", "popularity", "date_added")
    return jsonify([{k: p[k] for k in keep} for p, ok in results if ok])


@bp.route("/data/prompts.json")
def prompts_json():
    """The raw library file, handy for anyone who wants to reuse the data."""
    return send_file(store.DATA_FILE, mimetype="application/json", max_age=0)


@bp.route("/robots.txt")
def robots():
    base = current_app.config["SITE_URL"].rstrip("/")
    return Response(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap():
    base = current_app.config["SITE_URL"].rstrip("/")
    paths = ["/", "/explore", "/categories", "/contribute", "/about", "/github"]
    paths += [url_for("main.category", slug=c["slug"]) for c in store.get_categories()]
    paths += [url_for("main.prompt_detail", slug=p["slug"]) for p in store.get_prompts()]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"<url><loc>{base}{p}</loc></url>" for p in paths]
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")
