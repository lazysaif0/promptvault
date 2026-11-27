# Contributing to PromptVault

Thank you for helping. There are three easy ways to contribute: add a prompt, improve a prompt, or fix the site.

## Guidelines for prompts

1. **Original or properly attributed.** Write it yourself. If it is adapted from someone else's work, name them in `author` and make sure their license lets you share it.
2. **Clear purpose.** The title and description should tell a stranger what the prompt does and who it is for.
3. **Tested.** Run it with at least one AI assistant and check the result is useful. Mention which one in your pull request.
4. **Organized.** Choose the closest category, add 3 to 6 specific tags and set an honest difficulty:
   - **Beginner**: fill in a few fields and go.
   - **Intermediate**: needs some context or a multi-step conversation.
   - **Advanced**: needs domain knowledge or careful follow-up.
5. **Reusable.** Put everything the user must change in `[SQUARE BRACKETS]`, for example `[TOPIC]`. The site turns these into fill-in fields. Keep each placeholder short (under 80 characters, one line).
6. **Safe and respectful.** No personal data, nothing designed to deceive, harass or cause harm.
7. **Avoid duplicates.** Search the library first. Improve an existing prompt if yours is similar.

## Option 1: the form (no Git needed)

Use the **Contribute** page on the site. It checks your prompt and builds a ready-to-send JSON entry in your
browser (nothing is uploaded). Then you can open a pre-filled GitHub issue, copy the JSON, or download it.
A maintainer will review it and add it to the library.

## Option 2: pull request

```bash
# fork the repo on GitHub, then:
git clone https://github.com/YOUR-USERNAME/promptvault.git
cd promptvault
git checkout -b add-my-prompt
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Edit `data/prompts.json` and add an entry at the end of `"prompts"`:

```json
{
  "slug": "my-prompt-title",
  "title": "My Prompt Title",
  "description": "One or two sentences on what it does.",
  "category": "writing-communication",
  "tags": ["email", "tone"],
  "difficulty": "Beginner",
  "prompt": "Full prompt text with [PLACEHOLDERS].",
  "instructions": ["Replace the bracketed fields.", "Answer the questions one at a time."],
  "example_input": "What a user might type.",
  "example_output": "An abridged example of the result.",
  "popularity": 0,
  "date_added": "2026-01-31",
  "featured": false,
  "author": "your-github-username"
}
```

| Field | Rules |
|---|---|
| `slug` | Unique, lowercase words joined by hyphens. Becomes the URL. |
| `category` | One of: `education-learning`, `programming-development`, `career-professional-growth`, `writing-communication`, `productivity-organization`, `creativity-brainstorming`, `research-analysis`, `business-entrepreneurship`, `science-technology`, `personal-development`, `design-marketing`, `general-purpose` |
| `difficulty` | `Beginner`, `Intermediate` or `Advanced` |
| `tags` | 1 to 6 lowercase words |
| `popularity` | Leave `0`. Maintainers adjust it. |
| `featured` | Leave `false`. Maintainers choose featured prompts. |
| `date_added` | `YYYY-MM-DD` |

Then check, commit and push:

```bash
python tools/validate_prompts.py
python run.py                       # look at your prompt in the browser
python -m unittest discover tests
git add data/prompts.json
git commit -m "Add prompt: My Prompt Title"
git push origin add-my-prompt
```

Open a pull request on GitHub. Say what the prompt does and which AI you tested it with.

## Code changes

Keep changes focused, comment non-obvious code, run `python -m unittest discover tests` before pushing,
and describe what you changed and why in the pull request.

## Reporting problems

Open an issue and include what you expected, what happened, and your browser or Python version.

## Code of conduct

Be kind, assume good intent, give specific and constructive feedback. Harassment is not tolerated.
