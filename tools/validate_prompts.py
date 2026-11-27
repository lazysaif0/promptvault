"""
validate_prompts.py - checks data/prompts.json for mistakes.

Run it before every commit that touches the prompts:
    python tools/validate_prompts.py

It exits with an error code if anything is wrong, so the GitHub Actions
workflow can use it to block broken pull requests.
"""
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "prompts.json")
DIFFICULTIES = {"Beginner", "Intermediate", "Advanced"}
REQUIRED = ["slug", "title", "description", "category", "tags", "difficulty", "prompt",
            "instructions", "example_input", "example_output", "popularity",
            "date_added", "featured", "author"]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DATA   # optional: validate another file
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: prompts.json is not valid JSON: {e}")
        return 1

    errors = []
    categories = {c["slug"] for c in data["categories"]}
    seen = set()

    for i, p in enumerate(data["prompts"], 1):
        name = p.get("slug", f"#{i}")
        for key in REQUIRED:
            if key not in p:
                errors.append(f"{name}: missing field '{key}'")
        if errors and any(e.startswith(f"{name}: missing") for e in errors):
            continue
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", p["slug"]):
            errors.append(f"{name}: slug must be lowercase words joined by hyphens")
        if p["slug"] in seen:
            errors.append(f"{name}: duplicate slug")
        seen.add(p["slug"])
        if p["category"] not in categories:
            errors.append(f"{name}: unknown category '{p['category']}'")
        if p["difficulty"] not in DIFFICULTIES:
            errors.append(f"{name}: difficulty must be one of {sorted(DIFFICULTIES)}")
        if not isinstance(p["tags"], list) or not (1 <= len(p["tags"]) <= 6):
            errors.append(f"{name}: tags must be a list of 1 to 6 items")
        if not isinstance(p["instructions"], list):
            errors.append(f"{name}: instructions must be a list of strings")
        if len(p["title"]) < 5 or len(p["title"]) > 80:
            errors.append(f"{name}: title should be 5 to 80 characters")
        if len(p["description"]) < 20 or len(p["description"]) > 240:
            errors.append(f"{name}: description should be 20 to 240 characters")
        if len(p["prompt"]) < 40:
            errors.append(f"{name}: prompt text is too short")
        try:
            datetime.strptime(p["date_added"], "%Y-%m-%d")
        except ValueError:
            errors.append(f"{name}: date_added must look like 2026-01-31")
        if not isinstance(p["popularity"], int):
            errors.append(f"{name}: popularity must be a whole number")

    if errors:
        print("Found problems:")
        for e in errors:
            print("  -", e)
        return 1
    print(f"OK: {len(data['prompts'])} prompts in {len(categories)} categories look good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
