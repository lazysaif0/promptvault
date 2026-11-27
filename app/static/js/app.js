/*
 * PromptVault - app.js
 * Plain JavaScript, no libraries and no server calls. Everything below runs
 * in the browser, so it works the same locally and on GitHub Pages.
 *
 *   1. Helpers (safe localStorage, toast)
 *   2. Theme toggle (dark / light)
 *   3. Mobile menu
 *   4. Copy to clipboard
 *   5. Favorites (localStorage)
 *   6. Explore page: live search, filters and sorting
 *   7. Fill-in-the-blanks prompt component
 *   8. Contribute page: build a JSON entry, copy/download it, open a GitHub issue
 */
(function () {
  'use strict';

  /* ---------- 1. Helpers ---------- */
  // localStorage can throw (private mode, blocked cookies), so always wrap it.
  var store = {
    get: function (k, fallback) {
      try { var v = localStorage.getItem(k); return v === null ? fallback : JSON.parse(v); }
      catch (e) { return fallback; }
    },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };

  var toastEl = document.getElementById('toast');
  var toastTimer;
  function toast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('show'); }, 2400);
  }

  var reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- 2. Theme ---------- */
  var themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('pv:theme', next); } catch (e) {}
    });
  }

  /* ---------- 3. Mobile menu ---------- */
  var menuBtn = document.getElementById('menu-toggle');
  var nav = document.getElementById('site-nav');
  function setMenu(open) {
    nav.classList.toggle('open', open);
    menuBtn.setAttribute('aria-expanded', String(open));
    menuBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  }
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', function () { setMenu(!nav.classList.contains('open')); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });
    nav.addEventListener('click', function (e) { if (e.target.tagName === 'A') setMenu(false); });
  }

  /* ---------- 4. Copy to clipboard ---------- */
  function copyText(text) {
    // Modern API first; fall back to a hidden textarea for older browsers / http pages.
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy') ? resolve() : reject(); }
      catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }

  function flashButton(btn) {
    if (!btn) return;
    var original = btn.getAttribute('data-label') || btn.textContent;
    btn.setAttribute('data-label', original);
    btn.textContent = 'Copied';
    btn.classList.add('is-done');
    setTimeout(function () { btn.textContent = original; btn.classList.remove('is-done'); }, 1600);
  }

  function doCopy(text, btn, message) {
    return copyText(text).then(function () {
      toast(message || 'Prompt copied to clipboard');
      flashButton(btn);
      return true;
    }, function () {
      toast('Could not copy. Select the text and press Ctrl+C.');
      return false;
    });
  }

  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-copy-card],[data-copy-fill]');
    if (!t) return;
    if (t.hasAttribute('data-copy-card')) {
      // Cards store the raw prompt in data-prompt (with the [BRACKETS]).
      doCopy(t.closest('[data-prompt]').getAttribute('data-prompt'), t);
    } else {
      var fill = document.querySelector(t.getAttribute('data-copy-fill'));
      doCopy(fill && fill._getText ? fill._getText() : '', t);
    }
  });

  /* ---------- 5. Favorites ---------- */
  var FAV_KEY = 'pv:favs';
  function getFavs() { var f = store.get(FAV_KEY, []); return Array.isArray(f) ? f : []; }

  function refreshFavUI() {
    var favs = getFavs();
    document.querySelectorAll('[data-fav]').forEach(function (b) {
      var on = favs.indexOf(b.getAttribute('data-fav')) !== -1;
      b.setAttribute('aria-pressed', String(on));
      if (b.classList.contains('fav-text')) b.textContent = on ? 'Saved' : 'Save';
    });
    var c = document.querySelector('[data-fav-count]');
    if (c) { c.textContent = favs.length; c.hidden = favs.length === 0; }
    renderFavoritesPage(favs);
  }

  function renderFavoritesPage(favs) {
    var grid = document.getElementById('fav-grid');
    if (!grid) return;
    var shown = 0;
    grid.querySelectorAll('.card').forEach(function (card) {
      var on = favs.indexOf(card.dataset.slug) !== -1;
      card.hidden = !on;
      if (on) shown++;
    });
    document.getElementById('fav-empty').hidden = shown > 0;
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-fav]');
    if (!b) return;
    var slug = b.getAttribute('data-fav');
    var favs = getFavs();
    var i = favs.indexOf(slug);
    if (i === -1) { favs.push(slug); toast('Saved to favorites'); }
    else { favs.splice(i, 1); toast('Removed from favorites'); }
    store.set(FAV_KEY, favs);
    refreshFavUI();
  });
  refreshFavUI();

  /* ---------- 6. Explore: live search, filters, sorting ---------- */
  var form = document.getElementById('explore-form');
  if (form) {
    var results = document.getElementById('results');
    var cards = Array.prototype.slice.call(results.querySelectorAll('.card'));
    var qEl = form.elements.q, catEl = form.elements.category,
        diffEl = form.elements.difficulty, sortEl = form.elements.sort;
    var countEl = document.getElementById('result-count');
    var emptyEl = document.getElementById('empty');
    var clearBtn = document.getElementById('clear-filters');

    // Score a card for the typed words. Every word must match somewhere.
    function score(card, tokens) {
      var d = card.dataset, title = d.title.toLowerCase(), tags = d.tags.toLowerCase(),
          desc = d.desc.toLowerCase(), body = d.prompt.toLowerCase(), total = 0;
      for (var i = 0; i < tokens.length; i++) {
        var t = tokens[i], s = 0;
        if (title.indexOf(t) > -1) s += 5;
        if (tags.indexOf(t) > -1) s += 3;
        if (desc.indexOf(t) > -1) s += 2;
        if (body.indexOf(t) > -1) s += 1;
        if (!s) return 0;
        total += s;
      }
      return total;
    }

    function ensureBestMatchOption(hasQuery) {
      var opt = sortEl.querySelector('option[value="relevance"]');
      if (hasQuery && !opt) {
        opt = new Option('Best match', 'relevance');
        sortEl.insertBefore(opt, sortEl.firstChild);
      } else if (!hasQuery && opt) {
        opt.remove();
      }
    }

    function apply() {
      var q = qEl.value.trim().toLowerCase();
      var tokens = q ? q.split(/\s+/) : [];
      ensureBestMatchOption(tokens.length > 0);

      // Default sort: "Best match" while searching, "Newest" otherwise,
      // unless the user has picked a sort order themselves.
      if (!sortEl.dataset.touched) sortEl.value = tokens.length ? 'relevance' : 'newest';
      else if (!tokens.length && sortEl.value === 'relevance') sortEl.value = 'newest';

      var scores = new Map(), visible = [];
      cards.forEach(function (card) {
        var ok = true, d = card.dataset;
        if (catEl.value && d.cat !== catEl.value) ok = false;
        if (diffEl.value && d.diff !== diffEl.value) ok = false;
        var sc = 0;
        if (tokens.length) { sc = score(card, tokens); if (!sc) ok = false; }
        scores.set(card, sc);
        card.hidden = !ok;
        if (ok) visible.push(card);
      });

      var by = sortEl.value;
      cards.sort(function (a, b) {
        if (by === 'popular') return b.dataset.pop - a.dataset.pop;
        if (by === 'alpha') return a.dataset.title.localeCompare(b.dataset.title);
        if (by === 'relevance') return (scores.get(b) - scores.get(a)) || (b.dataset.pop - a.dataset.pop);
        return b.dataset.date.localeCompare(a.dataset.date) || (b.dataset.pop - a.dataset.pop);
      });
      cards.forEach(function (c) { results.appendChild(c); });  // re-order in the DOM

      countEl.innerHTML = '<strong>' + visible.length + '</strong> ' + (visible.length === 1 ? 'prompt' : 'prompts');
      emptyEl.hidden = visible.length > 0;
      var filtered = !!(q || catEl.value || diffEl.value);
      clearBtn.hidden = !filtered;

      // Keep the address bar in sync so the search can be bookmarked or shared.
      var params = new URLSearchParams();
      if (qEl.value.trim()) params.set('q', qEl.value.trim());
      if (catEl.value) params.set('category', catEl.value);
      if (diffEl.value) params.set('difficulty', diffEl.value);
      if (sortEl.dataset.touched) params.set('sort', sortEl.value);
      var qs = params.toString();
      history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
    }

    // Read starting values from the URL (this is also what makes search links work on a static site).
    var p = new URLSearchParams(location.search);
    if (p.has('q')) qEl.value = p.get('q');
    if (p.has('category') && catEl.querySelector('option[value="' + p.get('category') + '"]')) catEl.value = p.get('category');
    if (p.has('difficulty')) diffEl.value = p.get('difficulty');
    if (p.has('sort')) { ensureBestMatchOption(!!qEl.value.trim()); sortEl.value = p.get('sort'); sortEl.dataset.touched = '1'; }

    qEl.addEventListener('input', apply);
    catEl.addEventListener('change', apply);
    diffEl.addEventListener('change', apply);
    sortEl.addEventListener('change', function () { sortEl.dataset.touched = '1'; apply(); });
    form.addEventListener('submit', function (e) { e.preventDefault(); apply(); });
    clearBtn.addEventListener('click', function () {
      qEl.value = ''; catEl.value = ''; diffEl.value = ''; sortEl.value = 'newest';
      delete sortEl.dataset.touched;
      apply();
      qEl.focus();
    });
    apply();
  }

  /* ---------- 7. Fill-in-the-blanks prompt component ---------- */
  /*
   * Markup: <div class="fill"><pre>Text with [PLACEHOLDERS]</pre></div>
   * Each [PLACEHOLDER] becomes an input. The same label shares one value.
   * el._getText() returns the prompt with the typed values substituted.
   * Empty blanks are copied as the original [PLACEHOLDER].
   */
  var BLANK = /\[([^\[\]\n]{1,80})\]/g;

  function initFill(el) {
    var pre = el.querySelector('pre');
    if (!pre) return;
    var raw = pre.textContent;
    var parts = [], last = 0, m, inputs = [], values = {};
    BLANK.lastIndex = 0;
    while ((m = BLANK.exec(raw))) {
      parts.push({ text: raw.slice(last, m.index) });
      parts.push({ key: m[1], token: m[0] });
      last = m.index + m[0].length;
    }
    parts.push({ text: raw.slice(last) });
    if (parts.length === 1) { el._getText = function () { return raw; }; return; }  // no blanks

    pre.textContent = '';
    parts.forEach(function (part) {
      if (part.key === undefined) { pre.appendChild(document.createTextNode(part.text)); return; }
      var input = document.createElement('input');
      input.type = 'text';
      input.className = 'blank';
      input.placeholder = part.key;
      input.setAttribute('aria-label', part.key);
      input.dataset.key = part.key;
      input.spellcheck = false;
      sizeInput(input);
      input.addEventListener('input', function () {
        values[part.key] = input.value;
        inputs.forEach(function (o) { if (o !== input && o.dataset.key === part.key) { o.value = input.value; sizeInput(o); } });
        sizeInput(input);
      });
      inputs.push(input);
      pre.appendChild(input);
    });

    el._inputs = inputs;
    el._getText = function () {
      return parts.map(function (part) {
        if (part.key === undefined) return part.text;
        var v = (values[part.key] || '').trim();
        return v ? v : part.token;
      }).join('');
    };
    var hint = el.parentElement && el.parentElement.querySelector('.fill-hint');
    if (hint) hint.hidden = false;
  }

  // Make the input as wide as its text (or its placeholder when empty).
  function sizeInput(input) {
    var n = Math.max(input.value.length, input.placeholder.length, 4);
    input.style.width = 'calc(' + n + 'ch + 16px)';  // text width + padding
  }

  document.querySelectorAll('.fill').forEach(initFill);

  // Hero demo: type example values into the blanks once, to show how it works.
  var demo = document.querySelector('.fill[data-autofill]');
  if (demo && demo._inputs && !reduceMotion) {
    var examples = JSON.parse(demo.getAttribute('data-autofill'));
    var stopped = false;
    demo.addEventListener('focusin', function () { stopped = true; });
    demo.addEventListener('pointerdown', function () { stopped = true; });

    var typeInto = function (input, text, done) {
      var i = 0;
      (function step() {
        if (stopped) return;
        input.value = text.slice(0, ++i);
        input.dispatchEvent(new Event('input'));
        if (i < text.length) setTimeout(step, 28); else setTimeout(done, 350);
      })();
    };
    var run = function (n) { if (n < examples.length && demo._inputs[n] && !stopped) typeInto(demo._inputs[n], examples[n], function () { run(n + 1); }); };
    setTimeout(function () { run(0); }, 900);
  }

  /* ---------- 8. Contribute: no server needed ---------- */
  /*
   * A static site cannot receive form posts, so the form works entirely here:
   *   validate -> build the JSON entry -> show it -> let the person copy it,
   *   download it, open a pre-filled GitHub issue, or edit prompts.json on GitHub.
   * The rules mirror tools/validate_prompts.py so entries pass the validator.
   */
  var cform = document.getElementById('contribute-form');
  if (cform) {
    var errBox = document.getElementById('form-errors');
    var resBox = document.getElementById('contrib-result');
    var jsonPre = document.getElementById('result-json');
    var btnIssue = document.getElementById('btn-issue');
    var btnEdit = document.getElementById('btn-edit');
    var currentJson = '', currentSlug = '';
    var existing = [];
    try { existing = JSON.parse(cform.getAttribute('data-slugs') || '[]'); } catch (e) {}
    var repoUrl = cform.getAttribute('data-repo-url');

    var slugify = function (t) { return t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, ''); };
    var field = function (name) { return cform.elements[name].value.trim(); };
    var today = function () {
      var d = new Date(), pad = function (n) { return (n < 10 ? '0' : '') + n; };
      return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
    };

    function showErrors(list) {
      var ul = errBox.querySelector('ul');
      ul.innerHTML = '';
      list.forEach(function (msg) { var li = document.createElement('li'); li.textContent = msg; ul.appendChild(li); });
      errBox.hidden = false;
      errBox.focus();
      errBox.scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' });
    }

    cform.addEventListener('submit', function (e) {
      e.preventDefault();
      var title = field('title'), desc = field('description'), cat = field('category'),
          diff = field('difficulty'), promptText = field('prompt'), errors = [];
      var slug = slugify(title);

      if (title.length < 5) errors.push('Give the prompt a title of at least 5 characters.');
      else if (existing.indexOf(slug) !== -1) errors.push('A prompt with the title "' + title + '" already exists. Pick a different title.');
      if (desc.length < 20) errors.push('The short description needs at least 20 characters.');
      if (!cat) errors.push('Choose a category.');
      if (!diff) errors.push('Choose a difficulty level.');
      var tags = [];
      field('tags').split(/[,\n]/).forEach(function (t) {
        t = t.trim().toLowerCase();
        if (t && tags.indexOf(t) === -1) tags.push(t);
      });
      tags = tags.slice(0, 6);
      if (!tags.length) errors.push('Add at least one tag, separated by commas.');
      if (promptText.length < 40) errors.push('The prompt text needs at least 40 characters.');
      if (!cform.elements.agree.checked) errors.push('Confirm that the prompt is original or properly attributed and that you tested it.');

      if (errors.length) { showErrors(errors); return; }
      errBox.hidden = true;

      // Same field order as data/prompts.json
      var entry = {
        slug: slug,
        title: title,
        description: desc,
        category: cat,
        tags: tags,
        difficulty: diff,
        prompt: promptText,
        instructions: field('instructions').split('\n').map(function (s) { return s.trim(); }).filter(Boolean),
        example_input: field('example_input'),
        example_output: field('example_output'),
        popularity: 0,
        date_added: today(),
        featured: false,
        author: field('author') || 'Anonymous'
      };
      currentJson = JSON.stringify(entry, null, 2);
      currentSlug = slug;
      jsonPre.textContent = currentJson;

      // Pre-filled GitHub issue. Browsers/servers cap URL length, so fall back to a short body.
      var issueBase = repoUrl + '/issues/new?labels=prompt-submission&title=' + encodeURIComponent('Prompt submission: ' + title) + '&body=';
      var body = 'Prompt submission from the PromptVault form.\n\n```json\n' + currentJson + '\n```\n';
      var url = issueBase + encodeURIComponent(body);
      if (url.length > 7000) url = issueBase + encodeURIComponent('Paste the JSON from your clipboard here (it was copied when you clicked the button).\n\n```json\n\n```\n');
      btnIssue.href = url;
      btnEdit.href = repoUrl + '/edit/main/data/prompts.json';

      cform.hidden = true;
      resBox.hidden = false;
      resBox.scrollIntoView({ block: 'start', behavior: reduceMotion ? 'auto' : 'smooth' });
    });

    // Opening the issue also copies the JSON, so nothing is lost if the pre-filled body was too long.
    btnIssue.addEventListener('click', function () { doCopy(currentJson, null, 'JSON copied. Paste it into the issue if the box is empty.'); });
    document.getElementById('btn-copy-json').addEventListener('click', function (e) { doCopy(currentJson, e.currentTarget, 'JSON copied to clipboard'); });
    document.getElementById('btn-download').addEventListener('click', function () {
      var blob = new Blob([currentJson + '\n'], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (currentSlug || 'prompt') + '.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
      toast('Downloaded ' + a.download);
    });
    document.getElementById('btn-again').addEventListener('click', function () {
      cform.reset();
      resBox.hidden = true;
      cform.hidden = false;
      cform.elements.title.focus();
    });
  }
})();
