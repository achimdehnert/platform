/**
 * Klickdummy Feedback-Widget v0.5 (platform:ADR-211 Rev 13)
 * — Standalone, repo-agnostisch, Plugin-Architektur, GitHub-Direkt-API
 *
 * Aus meiki-hub v0.4-Stand portiert. v0.5-Neuerungen: Categories-Hook,
 * Persona-Hook, GitHub-Direkt-API statt zentraler Endpoint (Decider-Pivot B,
 * 2026-05-20 — Service-Boundary verworfen).
 *
 * Konfiguration (vor Widget-Script setzen):
 *   window.KLICKDUMMY_SPEC = { id, version, klickdummy_class }
 *   window.KLICKDUMMY_FEEDBACK_REPO = "owner/repo"     // GitHub-Ziel-Repo
 *   window.KLICKDUMMY_CATEGORIES = [{value,label}]     // optional, default 5
 *   window.KLICKDUMMY_PERSONA_HOOK = () => string|null // optional
 *   window.KLICKDUMMY_VERFAHREN_HOOK = () => string|null // optional
 *   window.KLICKDUMMY_FEEDBACK_FORCE = true             // bypass opt-in
 *
 * Mount: opt-in via URL ?feedback=on (Default off — class-erhaltend).
 * Submit-Modes:
 *   download   — Markdown-Datei (offline, kein GitHub nötig)
 *   clipboard  — navigator.clipboard
 *   github     — POST api.github.com/.../issues (User-PAT in LocalStorage)
 *                 KEY: localStorage.klickdummy_github_token
 */
(function () {
  'use strict';
  if (window.__klickdummyFeedbackLoaded) return;
  window.__klickdummyFeedbackLoaded = true;

  // ---- Configuration ------------------------------------------------------
  const SPEC = window.KLICKDUMMY_SPEC || { id: 'unknown', version: '0.0', klickdummy_class: 'mock' };
  const REPO = window.KLICKDUMMY_FEEDBACK_REPO || null;
  const CATEGORIES = window.KLICKDUMMY_CATEGORIES || [
    { value: 'bug', label: '🐛 Fehler / Inkonsistenz' },
    { value: 'feature', label: '💡 Funktionsidee / Anforderung', default: true },
    { value: 'ux', label: '🎨 UX-/Layout-Vorschlag' },
    { value: 'spec', label: '📋 Spec-Lücke / Klärungsbedarf' },
    { value: 'ki', label: '🤖 KI-/Automatisierung-Idee' }
  ];
  const FB_ACTION_HANDLERS = ['go', 'ext', 'wizard', 'hemmung', 'hemmungDms', 'hemmungSpeichern',
    'applyWorklistFilter', 'sortWorklist', 'closeModal', 'toast'];
  const FB_FILE_MAX_BYTES = 1024 * 1024;
  const FB_FILE_MAX_COUNT = 5;

  function fbEnabled() {
    const qs = new URLSearchParams(location.search);
    return qs.get('feedback') === 'on' || window.KLICKDUMMY_FEEDBACK_FORCE === true;
  }

  // ---- DOM injection ------------------------------------------------------
  function injectStyles() {
    if (document.getElementById('fb-styles')) return;
    const css = `
#fb-fab{position:fixed;right:20px;bottom:20px;z-index:200;background:#1a3a6c;color:#fff;width:54px;height:54px;border-radius:50%;border:none;font-size:22px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);display:none;font-family:system-ui,-apple-system,sans-serif}
#fb-fab:hover{background:#005ea2}
#fb-panel{position:fixed;right:20px;bottom:84px;z-index:201;width:380px;max-width:calc(100vw - 40px);background:#fff;border:1px solid #d8e0e8;border-radius:10px;box-shadow:0 8px 32px rgba(0,0,0,.25);padding:16px;display:none;font-family:system-ui,-apple-system,sans-serif}
#fb-panel.open{display:block}
#fb-panel h3{margin:0 0 8px;font-size:14px;color:#1a3a6c}
#fb-panel .meta{font-size:11px;color:#6a7888;margin-bottom:10px}
#fb-panel textarea{width:100%;min-height:120px;border:1px solid #d8e0e8;border-radius:6px;padding:8px;font-family:inherit;font-size:13px;box-sizing:border-box;resize:vertical}
#fb-panel select{font-family:inherit;font-size:12px;padding:4px 6px;border-radius:6px;border:1px solid #d8e0e8;width:100%;margin-bottom:8px}
#fb-panel .fb-actions{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
#fb-panel .fb-actions button{flex:1;font-size:12px;padding:7px 10px;border-radius:6px;cursor:pointer;font-family:inherit;font-weight:600;border:1px solid #d8e0e8;background:#fff;color:#3a4a5a}
#fb-panel .fb-actions button.primary{background:#1a3a6c;border-color:#1a3a6c;color:#fff}
#fb-panel .fb-actions button:hover{background:#f3f4f6}
#fb-panel .fb-actions button.primary:hover{background:#005ea2;border-color:#005ea2}
#fb-panel .fb-foot{font-size:10px;color:#8893a3;margin-top:8px;line-height:1.5}
#fb-panel details.fb-rel{margin:8px 0 4px;font-size:12px}
#fb-panel details.fb-rel>summary{cursor:pointer;color:#3a4a5a;padding:4px 0;list-style:none;user-select:none}
#fb-panel details.fb-rel>summary::-webkit-details-marker{display:none}
#fb-panel details.fb-rel>summary::before{content:'▸ ';color:#8893a3}
#fb-panel details.fb-rel[open]>summary::before{content:'▾ '}
#fb-panel .fb-rel-grid{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0 2px;padding:6px;background:#f8fafc;border:1px solid #e5e9ef;border-radius:6px}
#fb-panel .fb-rel-chip{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border:1px solid #d8e0e8;border-radius:12px;background:#fff;cursor:pointer;font-size:11px;color:#3a4a5a;user-select:none}
#fb-panel .fb-rel-chip:hover{background:#f3f4f6}
#fb-panel .fb-rel-chip.on{background:#1a3a6c;border-color:#1a3a6c;color:#fff}
#fb-panel .fb-rel-chip input{display:none}
#fb-panel .fb-rel-hint{font-size:10px;color:#8893a3;margin-top:4px}
#fb-panel .fb-rel-empty{font-size:11px;color:#8893a3;font-style:italic;padding:4px 0}
#fb-panel .fb-rel-chip .fb-action-tgt{opacity:.6;font-size:10px;margin-left:4px}
`;
    const s = document.createElement('style');
    s.id = 'fb-styles';
    s.textContent = css;
    document.head.appendChild(s);
  }

  function categoryOptions() {
    return CATEGORIES.map(c =>
      `<option value="${c.value}"${c.default ? ' selected' : ''}>${c.label}</option>`
    ).join('');
  }

  function injectMarkup() {
    if (document.getElementById('fb-fab')) return;
    const wrap = document.createElement('div');
    wrap.innerHTML = `
<button id="fb-fab" title="Feedback geben (Co-Development-Loop)">💬</button>
<div id="fb-panel">
  <h3>💬 Feedback zum Klick-Dummy</h3>
  <div class="meta">Screen <code id="fb-screen">—</code> · Persona <code id="fb-persona">—</code> · Spec <code>${SPEC.id} v${SPEC.version}</code></div>
  <div style="display:flex;gap:8px">
    <div style="flex:1">
      <label class="meta">Scope</label>
      <select id="fb-scope" title="Worauf bezieht sich das Feedback?">
        <option value="app" selected>🏛 Fachanwendung</option>
        <option value="klickdummy-tool">🧰 Klickdummy / Widget selbst</option>
      </select>
    </div>
    <div style="flex:1">
      <label class="meta">Kategorie</label>
      <select id="fb-cat">${categoryOptions()}</select>
    </div>
  </div>
  <textarea id="fb-text" placeholder="Was beobachtest, vermisst, schlägst vor? Konkret bitte — Screen-bezogen ist am hilfreichsten."></textarea>
  <details class="fb-rel">
    <summary>Bezug zu anderen Screens (optional, Repro-Anker)</summary>
    <div id="fb-rel-grid" class="fb-rel-grid"></div>
    <div class="fb-rel-hint">Hilft, das Feedback in Beziehung zu anderen Screens zu lesen. Mehrfachauswahl.</div>
  </details>
  <details class="fb-rel">
    <summary>Bezug zu Aktionen im aktuellen Screen (optional)</summary>
    <div id="fb-act-grid" class="fb-rel-grid"></div>
    <div class="fb-rel-hint">Buttons / Aktionen — feinere Repro-Anker als Screen-Bezug allein.</div>
  </details>
  <details class="fb-rel">
    <summary>Anhänge (optional)</summary>
    <label class="fb-rel-chip" style="cursor:pointer">
      <input type="checkbox" id="fb-snapshot"> DOM-Snapshot des aktuellen Screens anhängen (HTML, 8 KB)
    </label>
    <div style="margin-top:8px">
      <label class="meta" style="display:block;margin-bottom:4px">Dateien (max. 5, je 1 MB)</label>
      <input type="file" id="fb-files" multiple accept="image/*,application/pdf,text/markdown,text/plain,application/json" style="font-size:11px">
      <div id="fb-files-list" class="fb-rel-hint"></div>
    </div>
  </details>
  <div class="fb-actions">
    <button id="fb-dl">⬇ Download .md</button>
    <button id="fb-cb">📋 Clipboard</button>
    <button class="primary" id="fb-gh">🚀 GitHub Issue</button>
  </div>
  <div class="fb-foot">
    <strong>GitHub Issue:</strong> User-PAT in <code>localStorage.klickdummy_github_token</code> (Scope: <code>repo</code> wenn privat, sonst <code>public_repo</code>). Issue-Author = realer GitHub-User; Audit native.
    ${REPO ? '<br>Repo: <code>' + REPO + '</code>' : '<br><em>Repo nicht konfiguriert — nur Download/Clipboard möglich.</em>'}
  </div>
</div>`;
    document.body.appendChild(wrap);
    document.getElementById('fb-fab').addEventListener('click', toggle);
    document.getElementById('fb-dl').addEventListener('click', () => submit('download'));
    document.getElementById('fb-cb').addEventListener('click', () => submit('clipboard'));
    document.getElementById('fb-gh').addEventListener('click', () => submit('github'));
    document.getElementById('fb-files').addEventListener('change', filesListUpdate);
  }

  // ---- Screen/Action discovery -------------------------------------------
  function currentScreen() {
    const s = document.querySelector('section.active[data-screen]') ||
              document.querySelector('[data-screen]');
    return s ? s.getAttribute('data-screen') : null;
  }

  function currentPersona() {
    if (typeof window.KLICKDUMMY_PERSONA_HOOK === 'function') {
      return window.KLICKDUMMY_PERSONA_HOOK();
    }
    return document.body.getAttribute('data-persona') || null;
  }

  function currentVerfahren() {
    if (typeof window.KLICKDUMMY_VERFAHREN_HOOK === 'function') {
      return window.KLICKDUMMY_VERFAHREN_HOOK();
    }
    return document.body.getAttribute('data-verfahren') || null;
  }

  function allScreens() {
    return Array.from(document.querySelectorAll('section[data-screen]'))
      .map(s => s.getAttribute('data-screen'))
      .filter((v, i, a) => v && a.indexOf(v) === i)
      .sort();
  }

  function actionsInCurrentScreen() {
    const sect = document.querySelector('section.active');
    if (!sect) return [];
    const seen = new Set(); const out = [];
    Array.from(sect.querySelectorAll('[onclick]')).forEach(el => {
      const onclick = el.getAttribute('onclick') || '';
      const m = onclick.match(/(?:event\.stopPropagation\(\);)?\s*(\w+)\s*\(([^)]*)\)/);
      if (!m) return;
      const fn = m[1];
      if (!FB_ACTION_HANDLERS.includes(fn)) return;
      let label = (el.textContent || '').trim().replace(/\s+/g, ' ');
      if (label.length < 2 || label.length > 60) return;
      if (/^[←→↑↓]\s*$/.test(label)) return;
      let target = null;
      const arg = (m[2] || '').trim();
      if (fn === 'go') {
        const t = arg.match(/^['"]([a-z0-9-]+)['"]/);
        target = t ? t[1] : null;
      } else if (fn === 'ext') {
        const t = arg.match(/^['"]([^'"]+)['"]/);
        target = t ? `target-mock:${t[1]}` : null;
      } else if (fn === 'wizard' || fn === 'hemmung') {
        target = `${fn}#step-${arg.replace(/['"]/g, '')}`;
      } else if (fn === 'applyWorklistFilter') {
        const t = arg.match(/^['"]([^'"]+)['"]/);
        target = t ? `worklist#filter:${t[1]}` : null;
      }
      const key = label + '|' + (target || fn);
      if (seen.has(key)) return; seen.add(key);
      out.push({ label, target, fn });
    });
    return out;
  }

  // ---- Panel population ---------------------------------------------------
  function populateRelated() {
    const grid = document.getElementById('fb-rel-grid');
    if (!grid) return;
    const cur = currentScreen();
    const screens = allScreens().filter(s => s !== cur);
    const prev = new Set(Array.from(grid.querySelectorAll('input:checked')).map(i => i.value));
    grid.innerHTML = screens.map(s => `
      <label class="fb-rel-chip${prev.has(s) ? ' on' : ''}" data-screen="${s}">
        <input type="checkbox" value="${s}"${prev.has(s) ? ' checked' : ''}>${s}
      </label>`).join('');
    grid.querySelectorAll('label.fb-rel-chip').forEach(lbl =>
      lbl.addEventListener('change', () =>
        lbl.classList.toggle('on', lbl.querySelector('input').checked)));
  }

  function populateActions() {
    const grid = document.getElementById('fb-act-grid');
    if (!grid) return;
    const actions = actionsInCurrentScreen();
    const prev = new Set(Array.from(grid.querySelectorAll('input:checked')).map(i => i.value));
    if (!actions.length) { grid.innerHTML = '<span class="fb-rel-empty">Keine erkannten Aktionen in diesem Screen.</span>'; return; }
    grid.innerHTML = actions.map(a => {
      const val = a.target ? `${a.label}→${a.target}` : a.label;
      const safe = val.replace(/"/g, '&quot;');
      const tgt = a.target ? `<span class="fb-action-tgt">→ ${a.target}</span>` : '';
      return `<label class="fb-rel-chip${prev.has(safe) ? ' on' : ''}">
        <input type="checkbox" value="${safe}"${prev.has(safe) ? ' checked' : ''}>${a.label}${tgt}
      </label>`;
    }).join('');
    grid.querySelectorAll('label.fb-rel-chip').forEach(lbl =>
      lbl.addEventListener('change', () =>
        lbl.classList.toggle('on', lbl.querySelector('input').checked)));
  }

  function getRelated() {
    const g = document.getElementById('fb-rel-grid');
    return g ? Array.from(g.querySelectorAll('input:checked')).map(i => i.value) : [];
  }

  function getActions() {
    const g = document.getElementById('fb-act-grid');
    if (!g) return [];
    return Array.from(g.querySelectorAll('input:checked')).map(i => {
      const arr = i.value.split('→');
      return arr.length === 2 ? { label: arr[0], target: arr[1] } : { label: i.value, target: null };
    });
  }

  function domSnapshot() {
    if (!document.getElementById('fb-snapshot')?.checked) return null;
    const sect = document.querySelector('section.active');
    if (!sect) return null;
    const clone = sect.cloneNode(true);
    clone.querySelectorAll('script, style').forEach(n => n.remove());
    clone.querySelectorAll('[onclick]').forEach(n => n.removeAttribute('onclick'));
    let html = clone.outerHTML.replace(/\s{2,}/g, ' ').replace(/>\s+</g, '><');
    const MAX = 8192;
    if (html.length > MAX) html = html.slice(0, MAX) + '\n<!-- … gekürzt -->';
    return html;
  }

  function readFiles() {
    const input = document.getElementById('fb-files');
    if (!input || !input.files || !input.files.length) return Promise.resolve([]);
    const files = Array.from(input.files).slice(0, FB_FILE_MAX_COUNT);
    return Promise.all(files.map(f => new Promise(resolve => {
      if (f.size > FB_FILE_MAX_BYTES) {
        resolve({ name: f.name, type: f.type, size: f.size, skipped: 'too-large', data_url: null });
        return;
      }
      const r = new FileReader();
      r.onload = () => resolve({ name: f.name, type: f.type, size: f.size, data_url: r.result });
      r.onerror = () => resolve({ name: f.name, type: f.type, size: f.size, skipped: 'read-error', data_url: null });
      r.readAsDataURL(f);
    })));
  }

  function filesListUpdate() {
    const input = document.getElementById('fb-files');
    const list = document.getElementById('fb-files-list');
    if (!input || !list) return;
    const files = Array.from(input.files || []);
    if (!files.length) { list.textContent = ''; return; }
    list.innerHTML = files.slice(0, FB_FILE_MAX_COUNT).map(f => {
      const big = f.size > FB_FILE_MAX_BYTES;
      const sz = (f.size / 1024).toFixed(1) + ' KB';
      return `<div>${big ? '⚠️ zu groß' : '✓'} <code>${f.name}</code> · ${sz}${big ? ' (übersprungen)' : ''}</div>`;
    }).join('');
  }

  function toggle() {
    const p = document.getElementById('fb-panel');
    p.classList.toggle('open');
    if (p.classList.contains('open')) {
      document.getElementById('fb-screen').textContent = currentScreen() || '—';
      document.getElementById('fb-persona').textContent = currentPersona() || '—';
      populateRelated();
      populateActions();
    }
  }

  function payload() {
    return {
      screen: currentScreen(),
      persona: currentPersona(),
      verfahren: currentVerfahren(),
      feedback_scope: document.getElementById('fb-scope')?.value || 'app',
      category: document.getElementById('fb-cat').value,
      text: document.getElementById('fb-text').value.trim(),
      related_screens: getRelated(),
      related_actions: getActions(),
      dom_snapshot: domSnapshot(),
      spec_id: SPEC.id,
      spec_version: SPEC.version,
      klickdummy_class: SPEC.klickdummy_class,
      user_agent: navigator.userAgent,
      viewport: { w: window.innerWidth, h: window.innerHeight },
      timestamp: new Date().toISOString(),
      url: location.href
    };
  }

  function asMarkdown(p, attachments) {
    const scopeLbl = p.feedback_scope === 'klickdummy-tool' ? 'Klickdummy/Widget' : 'Fachanwendung';
    const relYaml = p.related_screens.length
      ? 'related_screens: [' + p.related_screens.map(s => `"${s}"`).join(', ') + ']\n'
      : 'related_screens: []\n';
    const actYaml = p.related_actions.length
      ? 'related_actions:\n' + p.related_actions.map(a =>
          `  - { label: "${a.label.replace(/"/g, '\\"')}", target: ${a.target ? '"' + a.target + '"' : 'null'} }`).join('\n') + '\n'
      : 'related_actions: []\n';
    const relSec = p.related_screens.length ? `\n**Bezug zu Screens:** ${p.related_screens.map(s => '`' + s + '`').join(', ')}\n` : '';
    const actSec = p.related_actions.length ? `**Bezug zu Aktionen:** ${p.related_actions.map(a => '`' + a.label + (a.target ? ' → ' + a.target : '') + '`').join(', ')}\n` : '';
    const snap = p.dom_snapshot ? `\n<details><summary>DOM-Snapshot (${p.dom_snapshot.length} Zeichen)</summary>\n\n\`\`\`html\n${p.dom_snapshot}\n\`\`\`\n</details>\n` : '';
    const att = (attachments && attachments.length)
      ? '\n## Anhänge\n\n' + attachments.map(a =>
          a.skipped
            ? `- ⚠️ \`${a.name}\` (${a.type || '?'}, ${a.size} B) — ${a.skipped}`
            : `<details><summary>📎 ${a.name} · ${(a.size / 1024).toFixed(1)} KB</summary>\n\n\`\`\`\n${a.data_url}\n\`\`\`\n</details>`).join('\n') + '\n'
      : '';
    return `---
type: klickdummy-feedback
spec_id: ${p.spec_id}
spec_version: ${p.spec_version}
klickdummy_class: ${p.klickdummy_class}
feedback_scope: ${p.feedback_scope}
screen: ${p.screen || '(n/a)'}
persona: ${p.persona || '(n/a)'}
verfahren: ${p.verfahren || '(n/a)'}
category: ${p.category}
${relYaml}${actYaml}timestamp: ${p.timestamp}
viewport: { w: ${p.viewport.w}, h: ${p.viewport.h} }
attachments: ${attachments && attachments.length ? attachments.length : 0}
---

## [${p.category}] ${scopeLbl}-Feedback · Screen \`${p.screen || '?'}\` · Persona \`${p.persona || '?'}\`
${relSec}${actSec}
${p.text}
${snap}${att}
---
*Erfasst via Feedback-Widget v0.5 (platform:ADR-211 Rev 13). Quelle: \`${p.url}\`*
`;
  }

  function reset() {
    document.getElementById('fb-text').value = '';
    ['fb-rel-grid', 'fb-act-grid'].forEach(id => {
      const g = document.getElementById(id);
      if (g) g.querySelectorAll('input:checked').forEach(i => {
        i.checked = false; i.closest('label')?.classList.remove('on');
      });
    });
    const snap = document.getElementById('fb-snapshot'); if (snap) snap.checked = false;
    const files = document.getElementById('fb-files'); if (files) { files.value = ''; filesListUpdate(); }
  }

  function toast(msg) {
    if (typeof window.toast === 'function') return window.toast(msg);
    console.log('[klickdummy-feedback]', msg);
  }

  // ---- Submit -------------------------------------------------------------
  async function submit(mode) {
    const p = payload();
    if (!p.text) { toast('Bitte Text eingeben'); return; }
    const attachments = await readFiles();
    const md = asMarkdown(p, attachments);
    if (mode === 'download') {
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `klickdummy-feedback-${p.screen || 'unknown'}-${Date.now()}.md`;
      document.body.appendChild(a); a.click(); a.remove();
      toast('Markdown heruntergeladen');
    } else if (mode === 'clipboard') {
      try { await navigator.clipboard.writeText(md); toast('In Clipboard'); }
      catch (e) { toast('Clipboard nicht verfügbar — Download wählen'); }
    } else if (mode === 'github') {
      await submitGithub(p, md);
    }
  }

  async function submitGithub(p, md) {
    if (!REPO) { toast('window.KLICKDUMMY_FEEDBACK_REPO nicht gesetzt'); return; }
    let token = localStorage.getItem('klickdummy_github_token');
    if (!token) {
      token = prompt(
        'GitHub Personal Access Token (Scope: repo wenn privat, sonst public_repo).\n\n' +
        'Erstellen unter: https://github.com/settings/tokens?type=beta\n' +
        'Token wird nur in localStorage gespeichert (klickdummy_github_token).'
      );
      if (!token) return;
      localStorage.setItem('klickdummy_github_token', token);
    }
    const title = `[Klickdummy-Feedback] ${p.category} · ${p.screen || 'n/a'}`;
    try {
      const r = await fetch(`https://api.github.com/repos/${REPO}/issues`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28'
        },
        body: JSON.stringify({ title, body: md, labels: ['klickdummy-feedback'] })
      });
      if (r.status === 401 || r.status === 403) {
        localStorage.removeItem('klickdummy_github_token');
        toast('Token ungültig — bitte erneut beim nächsten Submit eingeben');
        return;
      }
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const issue = await r.json();
      toast('Issue erstellt: ' + issue.html_url);
      reset();
      toggle();
    } catch (e) {
      toast('GitHub-Submit fehlgeschlagen — ' + e.message + '. Fallback: Download.');
      submit('download');
    }
  }

  function init() {
    if (!fbEnabled()) return;
    injectStyles();
    injectMarkup();
    document.getElementById('fb-fab').style.display = 'block';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
