# PromptVault

A cute, pixel-art library of reusable AI prompts for ChatGPT, Claude, Gemini and other assistants.
Browse, search, fill in the blanks, copy, save favorites and contribute your own.

- 36 hand-written prompts across 12 categories
- Search by title, description, tags and prompt text. Filter by category and difficulty. Sort by newest, most popular or A to Z
- **Fill-in blanks:** text in `[SQUARE BRACKETS]` becomes editable yellow fields, and Copy copies your filled-in version
- Pixel-art design with a pastel light mode and a cozy dark mode. Favorites are saved in your browser (no accounts)
- **Runs on GitHub Pages with no Python server.** Flask is only used while building and for local development

---

## What changed in this version (plain language)

**The look.** The whole site now has a pixel-art style: chunky stepped borders, hard offset shadows (no blur),
window-style cards with little title-bar buttons, pixel hearts, stars and clouds, and three pixel fonts
(Press Start 2P for headings, Silkscreen for buttons and labels, VT323 for text). Light mode is cream, lavender,
mint, pink and sky blue. Dark mode is a cozy night-purple that keeps text easy to read.

**How it is hosted.** Before, the site needed Flask running on a server. Now the pages are *baked into plain
HTML files* ahead of time, and the browser handles everything interactive. Think of it like this:

```
 data/prompts.json  --(build step, runs once)-->  dist/  = plain HTML + CSS + JS files
                                                          |
                                      GitHub Pages serves these files. No Python needed to visit the site.
```

- **Search, filters, sorting, copy, fill-in blanks, favorites and dark mode** all run in your browser, using the
  prompt data that is already inside each page (generated from `data/prompts.json`).
- **Contribute** no longer saves files on a server. The form builds your prompt as a JSON entry *in the browser*. You can
  copy it, download it, open a pre-filled GitHub issue, or open `prompts.json` on GitHub to send a pull request.
- **Links are relative**, so the site works at `https://you.github.io/promptvault/`, at a custom domain, or even if you
  double-click `dist/index.html`.
- **A GitHub Action rebuilds and publishes the site** every time you push to `main`.

**Local development is unchanged.** `python run.py` still starts the Flask dev server.

---

## 1. Run it on your computer

You need **Python 3.9 or newer** and **Git**. Check with `python --version` (on macOS/Linux you may need `python3`).

```bash
# 1. Get the code
git clone https://github.com/YOUR-USERNAME/promptvault.git
cd promptvault

# 2. Create an isolated Python environment
python -m venv .venv

# 3. Activate it
#    macOS / Linux:
source .venv/bin/activate
#    Windows (PowerShell):
.venv\Scripts\Activate.ps1
#    Windows (Command Prompt):
.venv\Scripts\activate.bat

# 4. Install the requirements
pip install -r requirements.txt

# 5. Start the development server
python run.py
```

Open **http://127.0.0.1:5000**. Press `Ctrl+C` to stop.

### Test the static site (exactly what GitHub Pages will serve)

```bash
python tools/build_static.py --serve --base /promptvault
```

This builds the static files into `dist/`, checks every link, and previews the result at
**http://127.0.0.1:8000/promptvault/**. The `--base /promptvault` part makes the preview behave like a GitHub
project site, so you can see that sub-path URLs work. Press `Ctrl+C` to stop.
No Flask is running while you browse this preview. It is only a file server.

### Quick test checklist

1. Home: watch the example prompt fill itself in, press Copy, paste somewhere to check.
2. Click the moon icon for dark mode. Reload the page: it remembers.
3. Explore: type `resume`. Results change as you type. Try the category, difficulty and sort menus.
4. Open a prompt, type into the yellow blanks, press **Copy prompt**.
5. Click hearts on a few cards, then open **Favorites** (heart in the top bar).
6. Contribute: fill in the form and press **Create my entry**. Try Copy JSON, Download JSON and Open GitHub issue.
7. Make the window phone-sized and open the menu.

### Run the automated tests

```bash
python -m unittest discover tests      # 27 tests: pages, links, search, filters, Contribute, static build
python tools/validate_prompts.py       # checks data/prompts.json for mistakes
```

---

## 2. Publish on GitHub Pages

GitHub Pages **cannot run Python or Flask**. That is why the site is exported to static files first. The included
workflow does this for you automatically.

```bash
# In the project folder:
git init
git add .
git commit -m "PromptVault: pixel redesign + static build"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/promptvault.git
git push -u origin main
```

(Create an **empty** repository named `promptvault` on https://github.com/new first, without a README.)

Then, once, on GitHub:

1. Open your repository, then **Settings > Pages**.
2. Under **Build and deployment > Source**, choose **GitHub Actions**.
3. Open the **Actions** tab. The **Deploy to GitHub Pages** workflow runs (re-run it from there if it ran before you changed the setting).
4. When it turns green, your site is live at **https://YOUR-USERNAME.github.io/promptvault/**.

From now on, every `git push` to `main` rebuilds and republishes the site. Step by step, with troubleshooting, in
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

The workflow reads your repository name by itself, so GitHub links on the site always point to the right place.
(For local runs, set `PV_GITHUB_REPO=you/promptvault`, see section 6.)

---

## 3. Project structure

```
promptvault/
├── run.py                       Starts the Flask development server
├── requirements.txt             Flask (+ gunicorn for optional Flask hosting)
├── app/
│   ├── __init__.py              Creates and configures the Flask app
│   ├── routes.py                Pages and URLs
│   ├── store.py                 Loads prompts.json; search, sort, related prompts
│   ├── templates/               HTML (Jinja2). base.html is the shared layout
│   │   └── partials/
│   │       ├── card.html        The window-style prompt card
│   │       └── sprites.html     Pixel-art icons (generated, see tools/make_sprites.py)
│   └── static/
│       ├── css/style.css        The pixel theme (tokens, borders, light/dark)
│       ├── js/app.js            Theme, menu, copy, favorites, search, fill-in blanks, Contribute form
│       └── img/favicon.svg
├── data/prompts.json            The whole library: categories + 36 prompts
├── tools/
│   ├── build_static.py          Exports the static site to dist/ and checks every link
│   ├── validate_prompts.py      Checks data/prompts.json
│   └── make_sprites.py          Draws the pixel icons from ASCII maps
├── tests/                       Automated tests
├── docs/DEPLOYMENT.md           Publishing guide
├── .github/workflows/
│   ├── pages.yml                Builds and deploys to GitHub Pages on every push to main
│   └── ci.yml                   Checks pull requests (data, tests, static build)
├── CONTRIBUTING.md  LICENSE  .gitignore
```

**How a page is made:** `build_static.py` asks the Flask app for each page, `routes.py` and `store.py` fill a
template with data from `prompts.json`, and the result is saved as an HTML file. `style.css` and `app.js` make it
look good and interactive in the visitor's browser.

## 4. Adding or editing prompts

Everything lives in `data/prompts.json`. Add an entry to the `"prompts"` list (copy an existing one), run
`python tools/validate_prompts.py`, then commit and push. The workflow rebuilds the site. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the field list.

## 5. Changing the look

- Colours: the variables at the top of `app/static/css/style.css`. Light mode is `:root`, dark mode is `[data-theme="dark"]`.
- Pixel icons: edit the ASCII maps in `tools/make_sprites.py`, then run `python tools/make_sprites.py`.
- Fonts: loaded from Google Fonts in `base.html`. If they cannot load (offline), the site falls back to clean system
  monospace fonts and stays fully usable. To host the fonts yourself, download Press Start 2P, Silkscreen and VT323
  (all open source, SIL OFL) into `app/static/fonts/`, add `@font-face` rules to `style.css`, and remove the Google Fonts links.

## 6. Configuration

| Environment variable | Purpose | Default |
|---|---|---|
| `PV_GITHUB_REPO` | `owner/name` of your repository (footer, issue and edit links) | `your-username/promptvault` |
| `PV_SITE_URL` | Public address (sitemap and canonical links) | `http://127.0.0.1:5000` |
| `SECRET_KEY` | Flask secret, only relevant if you host Flask yourself | dev placeholder |

The GitHub Pages workflow sets the first two for you automatically.

## License

MIT, see [LICENSE](LICENSE). Prompts are contributed under the same license.
