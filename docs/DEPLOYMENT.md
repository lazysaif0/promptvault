# Publishing PromptVault

## 1. GitHub repository vs GitHub Pages vs Flask hosting

**A GitHub repository** stores your code and its history and lets other people suggest changes (pull requests).
It does not make a website by itself.

**GitHub Pages** is a free service that serves **static files** (HTML, CSS, JavaScript, images) from a repository.
It **cannot run Python or Flask**. A Flask app pushed to Pages simply will not work.

**Flask hosting** (Render, Railway, PythonAnywhere, Fly.io...) is a server that keeps Python running.

PromptVault is designed so you do not need a server: `tools/build_static.py` runs Flask once, saves every page as an
HTML file in `dist/`, and GitHub Pages serves those files. The browser handles search, filters, copying, favorites,
dark mode and the Contribute form on its own.

| | GitHub Pages (recommended) | Flask hosting (optional) |
|---|---|---|
| Needs a server | No | Yes |
| Cost | Free | Free tiers exist |
| Search, filters, copy, favorites, theme | Works | Works |
| Contribute form | Works (JSON, download, GitHub issue) | Works (the same) |
| Updates | Push to `main`, rebuilt automatically | Push to `main`, redeploys |

---

## 2. Create the repository and push

1. Go to https://github.com/new, name it `promptvault`, leave "Add a README" **unchecked**, click **Create repository**.
2. In your project folder:

```bash
git init
git add .
git commit -m "PromptVault: pixel redesign + static build"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/promptvault.git
git push -u origin main
```

If Git asks for a password, GitHub needs a **personal access token** or the GitHub CLI login (`gh auth login`).
Account passwords are not accepted for pushing.

## 3. Turn on GitHub Pages (one time)

1. Repository **Settings > Pages**.
2. **Build and deployment > Source: GitHub Actions**.
3. Go to the **Actions** tab and open **Deploy to GitHub Pages**. If it has not run yet (or ran before you changed the setting), click **Run workflow**.
4. Wait for the green check. The address appears in the `deploy` job and in **Settings > Pages**:
   `https://YOUR-USERNAME.github.io/promptvault/`

What the workflow (`.github/workflows/pages.yml`) does on every push to `main`:

1. Installs Python and Flask on a temporary GitHub machine.
2. Validates `data/prompts.json` and runs the tests.
3. Runs `python tools/build_static.py` with your repository name and address.
4. Checks that every internal link in the generated site points to a real file (the build fails if not).
5. Uploads `dist/` and publishes it.

## 4. Test it on your computer first

```bash
python tools/build_static.py --serve --base /promptvault
```

Open http://127.0.0.1:8000/promptvault/ . This is the same set of files GitHub Pages will serve, behind the same
`/promptvault/` sub-path. You can also open `dist/index.html` directly in a browser: links are relative, so that works too.

Useful options:

| Option | Meaning |
|---|---|
| `--out folder` | Where to write the site (default `dist`) |
| `--base /name` | Sub-path used by the preview and by `404.html` |
| `--repo you/promptvault` | Repository used for GitHub links |
| `--site-url https://you.github.io/promptvault` | Used in the sitemap and canonical links |
| `--serve --port 8000` | Preview after building |
| `--no-check` | Skip the link check (not recommended) |

## 5. Maintain it with commits

```bash
git status                        # what changed?
git add data/prompts.json         # pick files (or "git add ." for everything)
git commit -m "Add prompt: Interview Question Generator"
git push                          # the site rebuilds automatically
```

Use short messages that start with a verb. For bigger work, use a branch:

```bash
git checkout -b feature/new-category-icons
# ...edit, commit...
git push -u origin feature/new-category-icons     # then open a pull request on GitHub
```

## 6. Accept contributions

People can contribute in three ways:

1. **The Contribute page.** It builds a JSON entry in their browser. They can open a pre-filled GitHub issue (labelled `prompt-submission`), or download the JSON.
2. **A pull request** that adds an entry to `data/prompts.json` (see CONTRIBUTING.md).
3. **The "Edit prompts.json on GitHub" button** on the Contribute page, which opens GitHub's web editor. GitHub forks the repository for them and offers to open a pull request.

To review a pull request: open it, click **Files changed**, read the new prompt, check the **Validate** workflow is green
(a red cross means the data or the build has a problem), then **Merge pull request**. The site republishes itself.

To publish a prompt that arrived as an **issue**: copy the JSON from the issue, paste it at the end of the `"prompts"`
list in `data/prompts.json` (add a comma before it), run `python tools/validate_prompts.py`, commit and push.

Tip: in **Settings > Branches**, protect `main` and require the **Validate** check so nothing broken can be merged.

---

## 7. Optional: host the Flask app instead

You only need this if you want to run Flask itself (for example to use the `/api/prompts` endpoint). Example with Render:

1. Push to GitHub, then at https://render.com choose **New > Web Service** and pick the repository.
2. **Build command:** `pip install -r requirements.txt`  **Start command:** `gunicorn run:app`
3. Environment variables: `SECRET_KEY` (a long random string), `PV_GITHUB_REPO=you/promptvault`, `PV_SITE_URL=https://your-app.onrender.com`

Never use `python run.py` (debug mode) on a public server.

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| Actions run fails at **Deploy** with "Pages not enabled" | Do step 3 (Settings > Pages > Source: GitHub Actions), then re-run the workflow. |
| The site shows my README instead of the website | Pages Source is set to "Deploy from a branch". Change it to **GitHub Actions**. |
| Page loads but has no styling or images | Rebuild with `python tools/build_static.py --serve --base /promptvault` and test locally. If it works there, clear your browser cache. |
| `Link check failed: broken link -> ...` | A template links to a page that does not exist. The message names the file and the link. |
| `python: command not found` | Use `python3`, or install Python from python.org (tick "Add to PATH" on Windows). |
| `ModuleNotFoundError: flask` | Activate the virtual environment, then `pip install -r requirements.txt`. |
| PowerShell will not activate `.venv` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use Command Prompt. |
| Port 5000 or 8000 already in use | `python tools/build_static.py --serve --port 8001`, or edit the port in `run.py`. |
| `git push` rejected | `git pull --rebase origin main`, then push again. |
| A new prompt does not appear | Run `python tools/validate_prompts.py`. A missing comma in the JSON is the usual cause. |
| Fonts look like plain monospace | The pixel fonts load from Google Fonts. If you are offline or they are blocked, the fallback is used. |
