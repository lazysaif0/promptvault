"""
store.py - the "database layer" of PromptVault.

All prompts live in data/prompts.json. This module loads that file and offers
simple functions for searching, filtering, sorting and finding related prompts.

Why JSON instead of SQLite?
  * Contributors can add a prompt by editing one text file (easy pull requests).
  * No database setup is needed to run the project.
  * 36 prompts (or even a few thousand) fit comfortably in memory.
If the library ever grows very large, only this file needs to change.
"""
import json
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "prompts.json")

DIFFICULTIES = ["Beginner", "Intermediate", "Advanced"]
SORT_OPTIONS = {
    "newest": "Newest",
    "popular": "Most popular",
    "alpha": "A to Z",
}

# Cache so the file is only re-read when it changes on disk.
_cache = {"mtime": None, "data": None}


def _load():
    """Load prompts.json, reloading automatically if the file was edited."""
    mtime = os.path.getmtime(DATA_FILE)
    if _cache["mtime"] != mtime:
        with open(DATA_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        categories = raw["categories"]
        by_slug = {c["slug"]: c for c in categories}
        prompts = raw["prompts"]
        for p in prompts:
            # Attach the full category object to each prompt for easy use in templates.
            p["category_info"] = by_slug[p["category"]]
            # Pre-compute lowercase text used by the search function.
            p["_title"] = p["title"].lower()
            p["_tags"] = " ".join(p["tags"]).lower()
            p["_desc"] = p["description"].lower()
            p["_body"] = p["prompt"].lower()
        for c in categories:
            c["count"] = sum(1 for p in prompts if p["category"] == c["slug"])
        _cache.update(mtime=mtime, data={"categories": categories, "prompts": prompts})
    return _cache["data"]


def get_categories():
    return _load()["categories"]


def get_category(slug):
    return next((c for c in get_categories() if c["slug"] == slug), None)


def get_prompts():
    return _load()["prompts"]


def get_prompt(slug):
    return next((p for p in get_prompts() if p["slug"] == slug), None)


def _score(prompt, tokens):
    """
    Relevance score for a search. Every word the user typed must appear
    somewhere (title, tags, description or prompt text), otherwise the prompt
    is excluded (returns 0). Title matches count the most.
    """
    total = 0
    for t in tokens:
        s = 0
        if t in prompt["_title"]:
            s += 5
        if t in prompt["_tags"]:
            s += 3
        if t in prompt["_desc"]:
            s += 2
        if t in prompt["_body"]:
            s += 1
        if s == 0:
            return 0
        total += s
    return total


def search(q="", category="", difficulty="", sort=""):
    """
    Filter and sort prompts.
    Returns a list of (prompt, matched) pairs for ALL prompts, in display order,
    where `matched` says whether the prompt passes the filters. The Explore page
    renders non-matching cards as hidden so the JavaScript can re-filter instantly
    without another request (and so the static GitHub Pages build works too).
    """
    tokens = q.lower().split()
    scores = {}
    results = []
    for p in get_prompts():
        ok = True
        if category and p["category"] != category:
            ok = False
        if difficulty and p["difficulty"] != difficulty:
            ok = False
        if tokens:
            sc = _score(p, tokens)
            scores[p["slug"]] = sc
            if sc == 0:
                ok = False
        results.append((p, ok))

    if not sort:
        sort = "relevance" if tokens else "newest"

    if sort == "popular":
        key = lambda r: -r[0]["popularity"]
    elif sort == "alpha":
        key = lambda r: r[0]["title"].lower()
    elif sort == "relevance":
        key = lambda r: (-scores.get(r[0]["slug"], 0), -r[0]["popularity"])
    else:  # newest
        key = lambda r: datetime.strptime(r[0]["date_added"], "%Y-%m-%d").toordinal() * -1
    results.sort(key=key)
    return results


def featured(limit=6):
    items = [p for p in get_prompts() if p["featured"]]
    items.sort(key=lambda p: -p["popularity"])
    return items[:limit]


def recent(limit=6):
    return sorted(get_prompts(), key=lambda p: p["date_added"], reverse=True)[:limit]


def related(prompt, limit=3):
    """Prompts sharing tags (weight 2) or the same category (weight 1)."""
    scored = []
    for p in get_prompts():
        if p["slug"] == prompt["slug"]:
            continue
        s = 2 * len(set(p["tags"]) & set(prompt["tags"]))
        if p["category"] == prompt["category"]:
            s += 1
        if s:
            scored.append((s, p["popularity"], p))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [p for _, _, p in scored[:limit]]
