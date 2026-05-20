/**
 * Klickdummy Feedback-Widget v0.4 — Shared Snippet (platform:ADR-214)
 *
 * Configuration (set BEFORE this script loads):
 *   window.KLICKDUMMY_FEEDBACK_ENDPOINT  — POST URL (Pfad A), default null → download-Fallback
 *   window.KLICKDUMMY_FEEDBACK_FORCE     — bool: bypass ?feedback=on opt-in
 *   window.KLICKDUMMY_SPEC               — { id, version, klickdummy_class }
 *
 * Mount target: any <body>. Widget injects #fb-fab and #fb-panel itself.
 * Repo MUST opt-in via URL ?feedback=on (default off — class-erhaltend).
 *
 * Empirie-Basis: meiki-hub PR #23, 7 Iterationen, v0.1→v0.4. Original-Code
 * in meiki-hub/.../shell.html; hier konsolidiert + repo-agnostisch gemacht.
 */

(function () {
  'use strict';
  if (window.__klickdummyFeedbackLoaded) return;
  window.__klickdummyFeedbackLoaded = true;

  const SPEC = window.KLICKDUMMY_SPEC || {
    id: 'unknown', version: '0.0', klickdummy_class: 'mock'
  };
  const ENDPOINT = window.KLICKDUMMY_FEEDBACK_ENDPOINT || null;

  function fbEnabled() {
    const qs = new URLSearchParams(location.search);
    return qs.get('feedback') === 'on' || window.KLICKDUMMY_FEEDBACK_FORCE === true;
  }

  function injectStyles() {
    if (document.getElementById('fb-styles')) return;
    const css = `
#fb-fab{position:fixed;right:20px;bottom:20px;z-index:200;background:#1a3a6c;color:#fff;width:54px;height:54px;border-radius:50%;border:none;font-size:22px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);display:none}
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
#fb-panel .fb-foot{font-size:10px;color:#8893a3;margin-top:8px;line-height:1.5}
`;
    const s = document.createElement('style');
    s.id = 'fb-styles';
    s.textContent = css;
    document.head.appendChild(s);
  }

  function injectMarkup() {
    if (document.getElementById('fb-fab')) return;
    const wrap = document.createElement('div');
    wrap.innerHTML = `
<button id="fb-fab" title="Feedback (Co-Development-Loop, ADR-211 Rev 12)">💬</button>
<div id="fb-panel">
  <h3>💬 Klickdummy-Feedback</h3>
  <div class="meta">Screen <code id="fb-screen">—</code> · Spec <code>${SPEC.id} v${SPEC.version}</code> · Klasse <code>${SPEC.klickdummy_class}</code></div>
  <label class="meta">Kategorie</label>
  <select id="fb-cat">
    <option value="bug">🐛 Fehler</option>
    <option value="feature" selected>💡 Funktion / Anforderung</option>
    <option value="ux">🎨 UX</option>
    <option value="spec">📋 Spec-Lücke</option>
    <option value="ki">🤖 KI-Idee</option>
  </select>
  <textarea id="fb-text" placeholder="Was beobachtest, vermisst, schlägst vor?"></textarea>
  <div class="fb-actions">
    <button id="fb-dl">⬇ Download .md</button>
    <button id="fb-cb">📋 Clipboard</button>
    <button class="primary" id="fb-ep">🚀 Senden</button>
  </div>
  <div class="fb-foot">Pfad A: ${ENDPOINT ? 'Endpoint ' + ENDPOINT : 'kein Endpoint konfiguriert — Download-Fallback'}</div>
</div>`;
    document.body.appendChild(wrap);
    document.getElementById('fb-fab').addEventListener('click', toggle);
    document.getElementById('fb-dl').addEventListener('click', () => submit('download'));
    document.getElementById('fb-cb').addEventListener('click', () => submit('clipboard'));
    document.getElementById('fb-ep').addEventListener('click', () => submit('endpoint'));
  }

  function currentScreen() {
    const s = document.querySelector('section.active, [data-screen]');
    return s ? (s.getAttribute('data-screen') || null) : null;
  }

  function toggle() {
    const p = document.getElementById('fb-panel');
    p.classList.toggle('open');
    if (p.classList.contains('open')) {
      document.getElementById('fb-screen').textContent = currentScreen() || '—';
    }
  }

  function payload() {
    return {
      screen: currentScreen(),
      category: document.getElementById('fb-cat').value,
      text: document.getElementById('fb-text').value.trim(),
      spec_id: SPEC.id,
      spec_version: SPEC.version,
      klickdummy_class: SPEC.klickdummy_class,
      user_agent: navigator.userAgent,
      viewport: { w: window.innerWidth, h: window.innerHeight },
      timestamp: new Date().toISOString(),
      url: location.href
    };
  }

  function asMarkdown(p) {
    return `---
type: klickdummy-feedback
spec_id: ${p.spec_id}
spec_version: ${p.spec_version}
klickdummy_class: ${p.klickdummy_class}
screen: ${p.screen || '(n/a)'}
category: ${p.category}
timestamp: ${p.timestamp}
---

## [${p.category}] Klickdummy-Feedback · ${p.screen || '?'}

${p.text}

---
*Quelle: \`${p.url}\` · UA: \`${p.user_agent}\`*
`;
  }

  function toast(msg) {
    // Fallback if host has no toast
    if (typeof window.toast === 'function') return window.toast(msg);
    console.log('[klickdummy-feedback]', msg);
  }

  async function submit(mode) {
    const p = payload();
    if (!p.text) { toast('Bitte Text eingeben'); return; }
    const md = asMarkdown(p);
    if (mode === 'download') {
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `klickdummy-feedback-${p.screen || 'unknown'}-${Date.now()}.md`;
      document.body.appendChild(a); a.click(); a.remove();
      toast('Markdown heruntergeladen');
    } else if (mode === 'clipboard') {
      try { await navigator.clipboard.writeText(md); toast('In Clipboard'); }
      catch (e) { toast('Clipboard nicht verfügbar — Download'); }
    } else if (mode === 'endpoint') {
      if (!ENDPOINT) { toast('Kein Endpoint — Download-Fallback'); return submit('download'); }
      try {
        const r = await fetch(ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ payload: p, markdown: md })
        });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const j = await r.json().catch(() => ({}));
        toast('Gesendet · ' + (j.issue_url || 'OK'));
        document.getElementById('fb-text').value = '';
        toggle();
      } catch (e) { toast('Senden fehlgeschlagen — ' + e.message); }
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
