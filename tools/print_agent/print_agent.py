#!/usr/bin/env python3
"""
IIL Print Agent — LLM-gestützter PDF-Generator mit Design-Switcher
Usage: python3 print_agent.py <input.md> [output_dir] [--design meiki|iil]

Designs: meiki (Standard), iil (IIL GmbH Corporate)
LLM (Default): cerebras/llama3.1-8b (schnell+günstig), Fallback groq/llama-3.1-8b-instant.
  Override via ENV PRINT_AGENT_LLM_PRIMARY und PRINT_AGENT_LLM_FALLBACK
  (litellm-Modellstring; leerer Fallback = kein Fallback).
  Für höhere Qualität auf Cerebras: PRINT_AGENT_LLM_PRIMARY=cerebras/qwen-3-235b-a22b-instruct-2507
Fallback: Ohne LLM direkt PDF erzeugen
"""

import sys
import re
import json
import os
import argparse
import subprocess
import tempfile
from pathlib import Path

import yaml

import litellm
import markdown
from weasyprint import HTML, CSS

OUTPUT_DIR = Path.home() / "pdf-output"
SECRETS_DIRS = [
    Path("/home/devuser/shared/secrets"),
    Path("/home/devuser/shared/inbox/secrets"),
    Path.home() / ".secrets",
]
_TEMPLATES_DIR = Path(__file__).parent / "print_templates"
_BASE_CSS_FILE = _TEMPLATES_DIR / "base.css"
_BASE_CSS_STATIC = _BASE_CSS_FILE.read_text(encoding="utf-8") if _BASE_CSS_FILE.exists() else ""

from jinja2 import Environment, FileSystemLoader, select_autoescape
_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape([]),
    trim_blocks=True,
    lstrip_blocks=True,
)

# ---------------------------------------------------------------------------
# Design Profiles — loaded from print_designs.yaml (SSoT)
# ---------------------------------------------------------------------------

_DESIGNS_FILE = Path(__file__).parent / "print_designs.yaml"


def _load_designs(override_file: Path | None = None) -> dict:
    """Lädt Platform-Designs, merged optional ein repo-spezifisches Override-YAML.

    Override-Regeln:
    - Repo-YAML kann neue Designs definieren (werden ergänzt)
    - Repo-YAML kann bestehende Designs überschreiben (repo-Werte gewinnen)
    - Repo-YAML Format identisch zu print_designs.yaml: {designs: {key: {...}}}
    """
    base: dict = {}
    if _DESIGNS_FILE.exists():
        with _DESIGNS_FILE.open(encoding="utf-8") as f:
            base = yaml.safe_load(f).get("designs", {})
    else:
        print(f"⚠️  {_DESIGNS_FILE} nicht gefunden — keine Designs verfügbar")
    if override_file and Path(override_file).exists():
        with Path(override_file).open(encoding="utf-8") as f:
            overrides = yaml.safe_load(f).get("designs", {})
        for key, vals in overrides.items():
            if key in base:
                base[key] = {**base[key], **vals}
            else:
                base[key] = vals
        print(f"🎨 Repo-Design-Override geladen: {override_file}")
    return base


DESIGNS = _load_designs()


def build_css(d: dict, extra_css: str = "", design_name: str = "") -> str:
    """Injiziert :root-Variablen + @page; Rest aus base.css + optionalem design.css + extra_css."""
    p, hl = d["primary"], d["header_left"]
    root_and_page = f"""
:root {{
    --primary:     {p};
    --bg-light:    {d["bg_light"]};
    --border:      {d["border"]};
    --border-dark: {d["border_dark"]};
    --row-even:    {d["row_even"]};
    --row-odd:     {d["row_odd"]};
    --gantt-bg:    {d["gantt_bg"]};
    --flow-s1:     {d["flow_s1"]};
    --flow-s2:     {d["flow_s2"]};
    --flow-s3:     {d["flow_s3"]};
}}
@page {{
    @top-left {{
        content: "{hl}";
        font-family: Arial, Helvetica, sans-serif;
        font-size: 8pt; font-weight: 700;
        letter-spacing: 0.12em; color: {p}; padding-top: 8mm;
    }}
}}
"""
    design_css = ""
    if design_name:
        design_css_path = _TEMPLATES_DIR / f"{design_name}.css"
        if design_css_path.exists():
            design_css = f"\n/* --- design-spezifisches CSS ({design_name}) ---*/\n" + design_css_path.read_text(encoding="utf-8")
    repo_css = f"\n/* --- repo-spezifisches CSS ---*/\n{extra_css}" if extra_css.strip() else ""
    return root_and_page + _BASE_CSS_STATIC + design_css + repo_css


def get_secret(name: str) -> str | None:
    val = os.environ.get(name.upper())
    if val:
        return val
    for base in SECRETS_DIRS:
        path = base / name.lower()
        if path.exists():
            return path.read_text().strip()
    return None


_DEFAULT_PRIMARY = "cerebras/llama3.1-8b"
_DEFAULT_FALLBACK = "groq/llama-3.1-8b-instant"


def _secret_name_for_model(model: str) -> str | None:
    """Mappt litellm-Modellstring auf Secret-Name (cerebras_api_key etc.)."""
    m = model.lower()
    if m.startswith("cerebras/"):
        return "cerebras_api_key"
    if m.startswith("groq/"):
        return "groq_api_key"
    if m.startswith("anthropic/") or m.startswith("claude-"):
        return "anthropic_api_key"
    if m.startswith("mistral/"):
        return "mistral_api_key"
    if m.startswith("together/") or m.startswith("together_ai/"):
        return "together_api_key"
    if m.startswith("openai/") or m.startswith("gpt-"):
        return "openai_api_key"
    return None


def _try_completion(model: str, prompt: str) -> dict | None:
    """Ein LLM-Versuch — gibt {} bei No-Key zurück, None bei Fehler, dict bei Erfolg."""
    secret_name = _secret_name_for_model(model)
    api_key = get_secret(secret_name) if secret_name else None
    if not api_key:
        print(f"⚠️  Kein API-Key für {model} ({secret_name}) — übersprungen")
        return None
    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
            api_key=api_key,
            timeout=15,
        )
        raw = response.choices[0].message.content.strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        print(f"⚠️  {model}: kein JSON in Antwort")
    except Exception as e:
        print(f"⚠️  {model}: {e}")
    return None


def llm_enrich(title: str, md_text: str, design: dict) -> dict:
    """Executive Summary + Keywords. Default Cerebras Llama-3.3-70b → Groq 8B-Fallback.

    ENV-Overrides:
      PRINT_AGENT_LLM_PRIMARY   (Default: cerebras/llama3.1-8b)
      PRINT_AGENT_LLM_FALLBACK  (Default: groq/llama-3.1-8b-instant, leer = aus)
    """
    primary = os.environ.get("PRINT_AGENT_LLM_PRIMARY", _DEFAULT_PRIMARY).strip()
    fallback = os.environ.get("PRINT_AGENT_LLM_FALLBACK", _DEFAULT_FALLBACK).strip()

    context = design.get("llm_context", "Technologie und KI")
    preview = md_text[:1200].strip()
    prompt = f"""Du bist Assistent für {context}.
Analysiere dieses Dokument und antworte NUR mit einem JSON-Objekt (kein Markdown, kein Text davor/danach):

Titel: {title}
Inhalt (Auszug):
{preview}

Antworte mit:
{{
  "summary": "<2-3 Sätze Zusammenfassung, sachlich, deutsch>",
  "keywords": ["<Stichwort1>", "<Stichwort2>", "<Stichwort3>", "<Stichwort4>", "<Stichwort5>"]
}}"""

    for attempt, model in enumerate([primary, fallback], start=1):
        if not model:
            continue
        label = "Primary" if attempt == 1 else "Fallback"
        print(f"   🤖 {label}: {model}")
        result = _try_completion(model, prompt)
        if result is not None:
            return result
    print("⚠️  Alle LLM-Versuche fehlgeschlagen — fahre ohne Summary fort")
    return {}


GANTT_COLORS = ["#2E7D32","#1565C0","#6A1B9A","#E65100",
                "#00695C","#283593","#4527A0","#558B2F"]
MONTHS_13 = ["Mär\n2026","Apr","Mai","Jun","Jul","Aug",
             "Sep","Okt","Nov","Dez","Jan\n2027","Feb","Mär"]


MONTH_NAME_TO_NUM = {
    "jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4, "mai": 5,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dez": 12,
}


def _cal_to_pos(cal_month: int, start_cal: int, total: int) -> int:
    """Kalendermonat → 1-basierte Chart-Position mit Jahresüberlauf."""
    pos = (cal_month - start_cal) % 12 + 1
    return pos


def parse_gantt_block(block: str) -> str:
    """Wandelt gantt-Codefence in HTML-Tabelle um."""
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    if not lines:
        return ""

    title_line = lines[0]  # z.B. "März 2026 – März 2027"

    # Startmonat aus Titelzeile ermitteln (z.B. "März" → 3)
    start_cal = 3  # Fallback: März
    for name, num in MONTH_NAME_TO_NUM.items():
        if title_line.lower().startswith(name):
            start_cal = num
            break

    phases = []
    for line in lines[1:]:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 4:
            num, label, start, end = parts
            phases.append((int(num), label, int(start), int(end)))

    months = MONTHS_13
    header_cells = "".join(
        f'<th>{m.replace(chr(10), "<br>")}</th>' for m in months
    )
    total_months = len(months)
    rows = ""
    for i, (num, label, cal_start, cal_end) in enumerate(phases):
        color = GANTT_COLORS[i % len(GANTT_COLORS)]
        # Kalendermonat → Chart-Position (1-basiert, Jahresüberlauf beachten)
        pos_start = _cal_to_pos(cal_start, start_cal, total_months)
        pos_end   = _cal_to_pos(cal_end,   start_cal, total_months)
        if pos_end < pos_start:            # Überlauf: Jan/Feb/Mär 2027
            pos_end += 12
        pos_end = min(pos_end, total_months + 1)
        cells = ""
        for m in range(1, total_months + 1):
            if pos_start <= m < pos_end:
                cells += f'<td style="background:{color};border:1px solid #D0D8E4;height:14pt"></td>'
            else:
                cells += '<td style="border:1px solid #D0D8E4;height:14pt"></td>'
        rows += f'<tr><td class="gantt-label">{num} – {label}</td>{cells}</tr>\n'

    return f"""<div class="gantt-wrapper">
<table class="gantt">
<thead><tr>
  <th class="gantt-label">{title_line}</th>{header_cells}
</tr></thead>
<tbody>
{rows}</tbody>
</table>
</div>"""


def parse_tree_block(block: str) -> str:
    """Wandelt eingerückten Dateibaum-Text (```tree) in HTML .file-tree um."""
    lines = [l.rstrip() for l in block.strip().splitlines()]
    if not lines:
        return ""

    def split_note(text: str):
        if " -- " in text:
            n, c = text.split(" -- ", 1)
            return n.strip(), c.strip()
        return text.strip(), ""

    def indent_of(line: str) -> int:
        return len(line) - len(line.lstrip())

    root_name, root_note = split_note(lines[0])
    root_note_html = f' <span class="ft-note">— {root_note}</span>' if root_note else ""

    items: list[tuple[int, str, str]] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        items.append((indent_of(line), *split_note(line)))

    if not items:
        return f'<div class="file-tree"><span class="ft-root">{root_name}</span>{root_note_html}</div>'

    base = items[0][0]

    def build(pos: int, min_indent: int):
        html = "<ul>\n"
        i = pos
        while i < len(items):
            ind, name, note = items[i]
            if ind < min_indent:
                break
            is_dir = name.endswith("/")
            note_html = f' <span class="ft-note">— {note}</span>' if note else ""
            tag = f'<span class="ft-dir">{name}</span>' if is_dir else name
            if i + 1 < len(items) and items[i + 1][0] > ind:
                child_html, i = build(i + 1, ind + 1)
                html += f"  <li>{tag}{note_html}\n{child_html}  </li>\n"
            else:
                html += f"  <li>{tag}{note_html}</li>\n"
                i += 1
        html += "</ul>\n"
        return html, i

    ul_html, _ = build(0, base)
    return f'<div class="file-tree">\n<span class="ft-root">{root_name}</span>{root_note_html}\n{ul_html}</div>'


def parse_flow_block(block: str) -> str:
    """Wandelt ```flow DSL in HTML .flow-diagram um."""
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    entry_text = ""
    stages: list[tuple] = []
    target_text = ""

    for line in lines:
        if line.startswith("entry:"):
            entry_text = line[6:].strip()
        elif line.startswith("target:"):
            target_text = line[7:].strip()
        elif len(line) >= 3 and line[0] == "s" and line[1].isdigit() and line[2] == ":":
            num = line[1]
            parts = [p.strip() for p in line[3:].split("|")]
            badge = parts[0] if parts else ""
            title = parts[1] if len(parts) > 1 else ""
            desc  = parts[2] if len(parts) > 2 else ""
            yes_text = no_text = rate_text = ""
            for p in parts[3:]:
                if p.startswith("yes:"):   yes_text  = p[4:].strip()
                elif p.startswith("no:"):  no_text   = p[3:].strip()
                elif p.startswith("rate:"): rate_text = p[5:].strip()
            stages.append((num, badge, title, desc, yes_text, no_text, rate_text))

    html = '<div class="flow-diagram">\n'
    if entry_text:
        html += f'<div class="flow-entry">{entry_text}</div>\n<div class="flow-connector">▼</div>\n'
    for num, badge, title, desc, yes_text, no_text, rate_text in stages:
        html += f'<div class="flow-stage s{num}">\n'
        html += f'  <div class="flow-badge"><span class="badge-num">{num}</span>{badge}</div>\n'
        html += f'  <div class="flow-body">\n    <strong>{title}</strong><br>\n'
        if desc:       html += f'    {desc}<br>\n'
        if yes_text:   html += f'    <span class="flow-yes">{yes_text}</span><br>\n'
        if no_text:    html += f'    <span class="flow-no">{no_text}</span>\n'
        if rate_text:  html += f'    <span class="flow-rate">&nbsp;(Ziel: {rate_text})</span>\n'
        html += '  </div>\n</div>\n'
    if target_text:
        html += f'<div class="flow-connector">▼</div>\n<div class="flow-target">{target_text}</div>\n'
    html += '</div>'
    return html


def parse_arch_block(block: str) -> str:
    """Wandelt ```arch DSL in HTML .arch-diagram (Pipeline-Komponenten) um.

    Syntax:
      title: <text>
      row: Box1 | Sub1 | Sub2 ;; Box2 | Sub1 | Sub2
      split:
        left: BoxL | Sub >> Ext-Label
        right: BoxR | Sub >> Ext-Label
    """
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    title = ""
    rows: list[str] = []
    split_left = split_right = ""
    for line in lines:
        if line.startswith("title:"):   title = line[6:].strip()
        elif line.startswith("row:"):   rows.append(line[4:].strip())
        elif line.startswith("left:"):  split_left  = line[5:].strip()
        elif line.startswith("right:"): split_right = line[6:].strip()

    def render_box(spec: str) -> str:
        bits = [b.strip() for b in spec.split("|")]
        inner = f'<div class="arch-box-title">{bits[0]}</div>\n'
        inner += "".join(f'<div class="arch-box-sub">{s}</div>\n' for s in bits[1:])
        return f'<div class="arch-box">\n{inner}</div>\n'

    html = '<div class="arch-diagram">\n'
    if title:
        html += f'<div class="arch-title">{title}</div>\n'
    for row in rows:
        html += '<div class="arch-row">\n'
        for j, part in enumerate([p.strip() for p in row.split(";;")]):
            if j > 0:
                html += '<div class="arch-arrow">→</div>\n'
            html += render_box(part)
        html += '</div>\n'
    if split_left or split_right:
        html += '<div class="arch-split">\n'
        for spec in (split_left, split_right):
            if not spec:
                continue
            html += '<div class="arch-branch">\n<div class="arch-arrow-down">↓</div>\n'
            box_spec, _, ext = spec.partition(">>")
            html += render_box(box_spec.strip())
            if ext.strip():
                html += f'<div class="arch-ext">{ext.strip()}</div>\n'
            html += '</div>\n'
        html += '</div>\n'
    html += '</div>'
    return html


def parse_layer_block(block: str) -> str:
    """Wandelt ```layer DSL in HTML .layer-diagram (Schichtenmodell) um.

    Syntax:
      top: Titel | Item1 | Item2 | ...
      bridge: Verbindungstext
      left:  Titel | Item1 | Item2
      right: Titel | Item1 | Item2
    """
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    top_items: list[str] = []
    bridge = ""
    left_items: list[str] = []
    right_items: list[str] = []
    for line in lines:
        if line.startswith("top:"):    top_items   = [p.strip() for p in line[4:].split("|")]
        elif line.startswith("bridge:"): bridge    = line[7:].strip()
        elif line.startswith("left:"):  left_items  = [p.strip() for p in line[5:].split("|")]
        elif line.startswith("right:"): right_items = [p.strip() for p in line[6:].split("|")]

    def render_list(items: list[str]) -> str:
        if len(items) <= 1:
            return ""
        return "<ul>\n" + "".join(f"  <li>{i}</li>\n" for i in items[1:]) + "</ul>\n"

    html = '<div class="layer-diagram">\n'
    if top_items:
        html += f'<div class="layer-top">\n<div class="layer-top-title">{top_items[0]}</div>\n'
        html += render_list(top_items)
        html += '</div>\n'
    if bridge:
        html += f'<div class="layer-bridge">↓&nbsp; {bridge} &nbsp;↓</div>\n'
    if left_items or right_items:
        html += '<div class="layer-columns">\n'
        for items in (left_items, right_items):
            if not items:
                continue
            html += f'<div class="layer-box">\n<div class="layer-box-title">{items[0]}</div>\n'
            html += render_list(items)
            html += '</div>\n'
        html += '</div>\n'
    html += '</div>'
    return html


def parse_tiers_block(block: str) -> str:
    """Wandelt ```tiers DSL in HTML .tier-list (farbcodierte Tier-Karten) um.

    Syntax (eine Tier pro Zeile, Pipe-getrennt):
      tier1 | <Label> | <Bedingung> | <Aktion>
      tier2 | <Label> | <Bedingung> | <Aktion>
      tier3 | <Label> | <Bedingung> | <Aktion>
      info  | <Label> | — | <Aktion>     ← neutraler Block ohne Ampel

    Renderiert als Karte mit farbiger Klassen-Spange links.
    """
    html = '<div class="tier-list">\n'
    for line in [l.strip() for l in block.strip().splitlines() if l.strip()]:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        kind = parts[0].lower()
        label = parts[1] if len(parts) > 1 else ""
        cond = parts[2] if len(parts) > 2 else ""
        action = parts[3] if len(parts) > 3 else ""
        cls = {"tier1": "tier-1", "tier2": "tier-2", "tier3": "tier-3",
               "info": "tier-info", "ok": "tier-ok"}.get(kind, "tier-info")
        html += f'<div class="tier-item {cls}">\n'
        html += f'  <div class="tier-label">{label}</div>\n'
        if cond:
            html += f'  <div class="tier-cond"><strong>Bedingung:</strong> {cond}</div>\n'
        if action:
            html += f'  <div class="tier-action"><strong>Aktion:</strong> {action}</div>\n'
        html += '</div>\n'
    html += '</div>'
    return html


def parse_compare_block(block: str) -> str:
    """Wandelt ```compare DSL in HTML .compare-grid (zwei-/dreispaltig) um.

    Syntax:
      title: <optionaler Übertitel>
      left:  <Titel> :: <Item1> :: <Item2> :: …
      right: <Titel> :: <Item1> :: <Item2> :: …
      verdict: <Empfehlungs-Text>     ← optional, unter Spalten

    Verwendung typisch für Pro/Contra, Variante A/B, Status quo/Ziel.
    """
    title = ""
    left_title = ""
    left_items: list[str] = []
    right_title = ""
    right_items: list[str] = []
    verdict = ""
    for line in [l.rstrip() for l in block.strip().splitlines() if l.strip()]:
        if line.startswith("title:"):
            title = line[6:].strip()
        elif line.startswith("left:"):
            parts = [p.strip() for p in line[5:].split("::")]
            left_title = parts[0] if parts else ""
            left_items = parts[1:] if len(parts) > 1 else []
        elif line.startswith("right:"):
            parts = [p.strip() for p in line[6:].split("::")]
            right_title = parts[0] if parts else ""
            right_items = parts[1:] if len(parts) > 1 else []
        elif line.startswith("verdict:"):
            verdict = line[8:].strip()

    html = '<div class="compare-block">\n'
    if title:
        html += f'  <div class="compare-title">{title}</div>\n'
    html += '  <div class="compare-grid">\n'
    for side_class, side_title, items in (
        ("compare-left",  left_title,  left_items),
        ("compare-right", right_title, right_items),
    ):
        if not side_title and not items:
            continue
        html += f'    <div class="compare-col {side_class}">\n'
        if side_title:
            html += f'      <div class="compare-col-title">{side_title}</div>\n'
        if items:
            html += '      <ul>\n'
            for it in items:
                html += f'        <li>{it}</li>\n'
            html += '      </ul>\n'
        html += '    </div>\n'
    html += '  </div>\n'
    if verdict:
        html += f'  <div class="compare-verdict"><strong>Empfehlung:</strong> {verdict}</div>\n'
    html += '</div>'
    return html


_PUPPETEER_CFG = Path(__file__).parent / ".puppeteer.json"


def _ensure_puppeteer_config() -> str:
    """Erstellt einmalig eine Puppeteer-Config mit --no-sandbox (für Container/WSL)."""
    if not _PUPPETEER_CFG.exists():
        _PUPPETEER_CFG.write_text(json.dumps({
            "args": ["--no-sandbox", "--disable-setuid-sandbox"]
        }), encoding="utf-8")
    return str(_PUPPETEER_CFG)


def render_mermaid_to_png(mermaid_code: str) -> str:
    """Rendert Mermaid-Code zu PNG via mmdc und bettet es als base64 data-URI ein.

    PNG statt SVG, weil WeasyPrint <foreignObject> in SVGs nicht korrekt rendert
    (Text in Mermaid-Boxen verschwindet).
    """
    import base64
    pp_cfg = _ensure_puppeteer_config()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f_in:
        f_in.write(mermaid_code)
        in_path = f_in.name
    out_path = in_path.replace(".mmd", ".png")
    try:
        result = subprocess.run(
            ["npx", "--yes", "@mermaid-js/mermaid-cli", "-i", in_path, "-o", out_path,
             "-p", pp_cfg, "--backgroundColor", "white", "--scale", "3", "--quiet"],
            capture_output=True, text=True, timeout=45,
        )
        if result.returncode == 0 and os.path.exists(out_path):
            png_data = Path(out_path).read_bytes()
            b64 = base64.b64encode(png_data).decode("ascii")
            return (f'<div class="mermaid-diagram">'
                    f'<img src="data:image/png;base64,{b64}" '
                    f'style="max-width:100%;height:auto;" />'
                    f'</div>')
        else:
            err = result.stderr[:200] if result.stderr else "unknown error"
            print(f"\u26a0\ufe0f  Mermaid-Rendering fehlgeschlagen: {err}")
            return f'<pre class="mermaid-fallback"><code>{mermaid_code}</code></pre>'
    except subprocess.TimeoutExpired:
        print("\u26a0\ufe0f  Mermaid-Rendering: Timeout")
        return f'<pre class="mermaid-fallback"><code>{mermaid_code}</code></pre>'
    finally:
        for p in (in_path, out_path):
            try:
                os.unlink(p)
            except OSError:
                pass


def preprocess_md(md_text: str) -> str:
    """Ersetzt ```gantt / ```tree / ```flow / ```arch / ```layer / ```tiers / ```compare / ```mermaid durch HTML."""
    def replace_gantt(m):   return parse_gantt_block(m.group(1))
    def replace_tree(m):    return parse_tree_block(m.group(1))
    def replace_flow(m):    return parse_flow_block(m.group(1))
    def replace_arch(m):    return parse_arch_block(m.group(1))
    def replace_layer(m):   return parse_layer_block(m.group(1))
    def replace_tiers(m):   return parse_tiers_block(m.group(1))
    def replace_compare(m): return parse_compare_block(m.group(1))
    def replace_mermaid(m):
        code = m.group(1).strip()
        print(f"   \U0001f4ca Mermaid-Diagramm rendern ({code.split(chr(10))[0][:40]}\u2026)")
        return render_mermaid_to_png(code)
    text = re.sub(r"```gantt\n(.*?)```",   replace_gantt,   md_text, flags=re.DOTALL)
    text = re.sub(r"```tree\n(.*?)```",    replace_tree,    text,    flags=re.DOTALL)
    text = re.sub(r"```flow\n(.*?)```",    replace_flow,    text,    flags=re.DOTALL)
    text = re.sub(r"```arch\n(.*?)```",    replace_arch,    text,    flags=re.DOTALL)
    text = re.sub(r"```layer\n(.*?)```",   replace_layer,   text,    flags=re.DOTALL)
    text = re.sub(r"```tiers\n(.*?)```",   replace_tiers,   text,    flags=re.DOTALL)
    text = re.sub(r"```compare\n(.*?)```", replace_compare, text,    flags=re.DOTALL)
    text = re.sub(r"```mermaid\n(.*?)```", replace_mermaid, text,    flags=re.DOTALL)
    return text


_INLINE_PATTERNS = {
    "stand":           r"\*\*Stand:\*\*\s*([^|\n]+)",
    "zielgruppe":      r"\*\*Zielgruppe:\*\*\s*([^\n]+)",
    "angebot_nr":      r"\*\*Angebot Nr\.:\*\*\s*([^\n]+)",
    "datum":           r"\*\*Datum:\*\*\s*([^\n]+)",
    "gueltig_bis":     r"\*\*Gültig bis:\*\*\s*([^\n]+)",
    "auftraggeber":    r"\*\*Auftraggeber\*\*\s*\n+(.+)",
    # Generic document fields (used by konzept/briefing templates)
    "doc_type":        r"\*\*(?:Typ|Doc[- ]?Type|Dokumenttyp):\*\*\s*([^\n]+)",
    "status":          r"\*\*Status:\*\*\s*([^\n]+)",
    "adressat":        r"\*\*Adressat:\*\*\s*([^\n]+)",
    "zielentscheidung":r"\*\*Zielentscheidung:\*\*\s*([^\n]+)",
    "autor":           r"\*\*Autor(?:in)?:\*\*\s*([^\n]+)",
    "anlass":          r"\*\*Anlass:\*\*\s*([^\n]+)",
    # DB internal-doc fields (used by db template)
    "klassifizierung": r"\*\*Klassifizierung:\*\*\s*([^\n]+)",
    "eigentuemer":     r"\*\*Eigent(?:ü|ue)mer:\*\*\s*([^\n]+)",
    "version":         r"\*\*Version:\*\*\s*([^\n]+)",
    "geltungsbereich": r"\*\*Geltungsbereich:\*\*\s*([^\n]+)",
    "basisdokument":   r"\*\*Basisdokument:\*\*\s*([^\n]+)",
}


def extract_meta(md_text: str, fm: dict | None = None) -> dict:
    """Merge markdown.meta frontmatter (primary) with inline-bold regex (fallback)."""
    meta = {}
    # 1. Frontmatter from markdown.meta extension (key already lowercase)
    if fm:
        for k, v in fm.items():
            meta[k] = " ".join(v) if isinstance(v, list) else v
    # 2. Regex fallback for keys not found in frontmatter
    for key, pattern in _INLINE_PATTERNS.items():
        if key not in meta:
            m = re.search(pattern, md_text)
            if m:
                meta[key] = m.group(1).strip()
    return meta


# Bold-prefix patterns that should NOT appear in the body — they're already in the cover.
_META_PREFIX_RE = re.compile(
    r"^\*\*(?:Stand|Status|Datum|Adressat|Zielentscheidung|Anlass|Autor(?:in)?|"
    r"Typ|Dokumenttyp|Doc[- ]?Type|Zielgruppe|Angebot Nr\.|Gültig bis|Auftraggeber|"
    r"Begleitdokument|Klassifizierung|Eigent(?:ü|ue)mer|Version|Geltungsbereich|"
    r"Basisdokument):\*\*",
    re.IGNORECASE,
)


def strip_meta_prefix_lines(md_text: str) -> str:
    """Remove lines like '**Status:** Konzept' from MD body — they're already on the cover.

    Keeps everything else intact, including the trailing blank-line separator
    so that downstream markdown parsing doesn't merge paragraphs.
    """
    out_lines = []
    for line in md_text.splitlines():
        if _META_PREFIX_RE.match(line.strip()):
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def _build_meta_rows(meta: dict, design: dict, stem: str) -> list:
    """Return list of (label, value) tuples for the meta table."""
    template = design.get("meta_template", "meiki")
    if template == "db":
        rows = []
        doc_id = stem.upper().replace("_", "-")
        rows.append(("Dokument-ID", doc_id))
        rows.append(("Klassifizierung", meta.get("klassifizierung", "Vertraulich – Nur für den internen Gebrauch")))
        if meta.get("stand"):           rows.append(("Stand", meta["stand"]))
        if meta.get("eigentuemer"):     rows.append(("Eigentümer", meta["eigentuemer"]))
        if meta.get("version"):         rows.append(("Version", meta["version"]))
        if meta.get("geltungsbereich"): rows.append(("Geltungsbereich", meta["geltungsbereich"]))
        if meta.get("basisdokument"):   rows.append(("Basisdokument", meta["basisdokument"]))
        return rows
    if template == "iil":
        rows = []
        # Angebot-specific fields (only shown if filled)
        if meta.get("angebot_nr"):       rows.append(("Angebot-Nr.", meta["angebot_nr"]))
        # Generic Konzept/Briefing-Felder (always shown if present)
        if meta.get("status"):           rows.append(("Status", meta["status"]))
        if meta.get("datum"):            rows.append(("Datum", meta["datum"]))
        if meta.get("gueltig_bis"):      rows.append(("Gültig bis", meta["gueltig_bis"]))
        if meta.get("adressat"):         rows.append(("Adressat", meta["adressat"]))
        if meta.get("anlass"):           rows.append(("Anlass", meta["anlass"]))
        if meta.get("zielentscheidung"): rows.append(("Zielentscheidung", meta["zielentscheidung"]))
        if meta.get("auftraggeber"):     rows.append(("Auftraggeber", meta["auftraggeber"]))
        rows.append(("Auftragnehmer", "IIL GmbH · Achim Dehnert · achim.dehnert@iil.gmbh"))
        return rows
    # meiki default
    stand = meta.get("stand", "")
    if not stand:
        return []
    doc_id = stem.upper().replace("_", "-")
    return [
        ("Dokument-ID", doc_id),
        ("Konsortium", "LRA Traunstein · LRA Günzburg · TH Rosenheim · HNU Neu-Ulm"),
        ("Stand", stand),
        ("Projektlaufzeit", "März 2026 – März 2027"),
        ("Vertraulichkeit", "Vertraulich – nur für Konsortium MEiKI"),
    ]


def build_html(title: str, body_html: str, meta: dict, stem: str, enrichment: dict, design: dict) -> str:
    stand = meta.get("stand", "")
    template = design.get("meta_template", "meiki")

    if template == "iil":
        # Document type drives the cover subtitle line.
        # Priority: explicit Typ: > explicit Status: > "Angebot" (backward-compat default).
        # New documents should set "**Typ:** Konzept|Briefing|Angebot|…" explicitly.
        doc_type = meta.get("doc_type") or meta.get("status") or "Angebot"
        datum = meta.get("datum", "")
        date_line = f"{doc_type} · {datum}".strip(" ·")
    else:
        zg = meta.get("zielgruppe", "Lenkungskreis, IT-Leitung, Entscheider LRA")
        date_line = f"Zielgruppe: {zg}"

    footer_text = (f"Stand: {stand} — " if stand else "") + design.get("footer_suffix", "")

    ctx = {
        "title":        title,
        "cover_label":  design.get("cover_label", ""),
        "subtitle":     design.get("subtitle", ""),
        "date_line":    date_line,
        "es_label":     design.get("es_label_text", "Executive Summary"),
        "enrichment":   enrichment,
        "meta_rows":    _build_meta_rows(meta, design, stem),
        "body_html":    body_html,
        "footer_text":  footer_text,
        "stand":        stand,
    }
    tpl = _JINJA_ENV.get_template("base.html.j2")
    return tpl.render(**ctx)


def convert(input_path: Path, output_dir: Path, design_name: str = "meiki", extra_css: str = "") -> Path:
    design = DESIGNS.get(design_name, DESIGNS["meiki"])
    print(f"🎨 Design: {design_name}")

    md_text = input_path.read_text(encoding="utf-8")
    # Extract meta first (from original text), then strip those lines before HTML build.
    md_pre_meta = markdown.Markdown(extensions=["meta"])
    md_pre_meta.convert(md_text)
    fm = {k: v for k, v in md_pre_meta.Meta.items()} if hasattr(md_pre_meta, "Meta") else {}
    meta = extract_meta(md_text, fm=fm)

    # Strip meta-prefix lines so they don't appear as paragraph text in body.
    md_text_cleaned = strip_meta_prefix_lines(md_text)
    md_text_processed = preprocess_md(md_text_cleaned)
    md = markdown.Markdown(
        extensions=["tables", "attr_list", "meta", "toc", "fenced_code", "sane_lists"],
        extension_configs={
            "toc": {
                "title": "Inhaltsverzeichnis",
                "toc_class": "toc-list",
            },
        },
    )
    body_html = md.convert(md_text_processed)

    m = re.search(r"<h1[^>]*>(.*?)</h1>", body_html)
    title = m.group(1) if m else input_path.stem
    body_html = re.sub(r"<h1[^>]*>.*?</h1>", "", body_html, count=1)

    print("🤖 LLM-Anreicherung …")
    enrichment = llm_enrich(title, md_text, design)
    if enrichment.get("summary"):
        print(f"   ✅ Summary: {enrichment['summary'][:80]}…")
        print(f"   🏷️  Keywords: {', '.join(enrichment.get('keywords', []))}")

    html = build_html(title, body_html, meta, input_path.stem, enrichment, design)
    css = build_css(design, extra_css=extra_css, design_name=design_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{input_path.stem}.pdf"
    HTML(string=html, base_url="/").write_pdf(str(out_path), stylesheets=[CSS(string=css)])
    return out_path


def _design_hub_dir() -> Path:
    """Resolve DESIGN_HUB_DIR (env var oder Default ~/github/design-hub)."""
    return Path(os.environ.get("DESIGN_HUB_DIR", str(Path.home() / "github/design-hub"))).expanduser()


def _load_profile(profile_name: str) -> tuple[dict, Path]:
    """Lädt Profile aus design-hub/profiles/<name>.yaml.

    Returns (profile_dict, design_hub_dir).
    Wirft FileNotFoundError wenn Profile fehlt.
    """
    dh_dir = _design_hub_dir()
    profile_path = dh_dir / "profiles" / f"{profile_name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(
            f"Profile '{profile_name}' nicht gefunden unter {profile_path}\n"
            f"  Erwartet: {dh_dir}/profiles/<name>.yaml\n"
            f"  Verfügbar: {', '.join(p.stem for p in (dh_dir / 'profiles').glob('*.yaml'))}"
        )
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if profile.get("schema_version") != 1:
        print(f"⚠ Profile schema_version != 1 — kann fehlschlagen.")
    return profile, dh_dir


def _profile_to_design(profile: dict) -> dict:
    """Konvertiert Profile-Schema → Design-Dict (kompatibel mit bestehender convert())."""
    c = profile.get("colours", {})
    h = profile.get("header", {})
    f = profile.get("footer", {})
    return {
        "primary":       c.get("primary",      "#1A3A5C"),
        "bg_light":      c.get("bg_light",     "#EDF3FA"),
        "border":        c.get("border",       "#C8D8EC"),
        "border_dark":   c.get("primary_dark", "#0D2840"),
        "row_even":      c.get("zebra",        "#F3F7FC"),
        "row_odd":       "#FFFFFF",
        "gantt_bg":      c.get("bg_light",     "#F8FAFE"),
        "flow_s1":       c.get("primary",      "#1A3A5C"),
        "flow_s2":       c.get("accent_1",     "#2C5F8A"),
        "flow_s3":       c.get("accent_2",     "#3D7AB5"),
        "header_left":   h.get("text",          "IIL"),
        "cover_label":   h.get("cover_label",   "IIL"),
        "subtitle":      profile.get("description", ""),
        "footer_suffix": f.get("suffix",        ""),
        "llm_context":   profile.get("llm_context", ""),
        "es_label_text": profile.get("es_label_text", "Zusammenfassung"),
        "meta_template": "iil",   # bestehender Render-Pfad
        "_profile":      profile,  # Original-Profile durchreichen
    }


def _check_allowed_assets(profile: dict, asset_path: str) -> None:
    """Compliance-Check: wirft AssertionError wenn Asset-Pfad nicht erlaubt."""
    allowed = profile.get("allowed_assets") or {}
    if not asset_path:
        return
    # Erste Pfad-Komponente nach "assets/" ist der Bucket
    parts = asset_path.split("/")
    if len(parts) < 2 or parts[0] != "assets":
        return
    bucket = parts[1]
    if bucket in ("db", "iil", "shared") and not allowed.get(bucket, False):
        raise AssertionError(
            f"❌ Lizenz-Verstoß: Profile '{profile.get('name')}' darf '{bucket}'-Assets "
            f"nicht laden, aber Pfad zeigt darauf: {asset_path}\n"
            f"  Siehe design-hub/LICENSE_NOTES.md"
        )


def _build_profile_extra_css(profile: dict, dh_dir: Path) -> str:
    """Erzeugt: erst _base.css (mit Defaults), DANN Profile-Override-:root + @font-face.

    Reihenfolge ist wichtig: Profile-Variablen MÜSSEN nach _base.css kommen
    sonst überschreiben die Defaults die Profile-Werte (Color-Routing-Bug
    der ersten Iter — siehe Lessons-Learned).
    """
    c = profile.get("colours", {})
    fonts = profile.get("fonts", {})
    h = profile.get("header", {})
    classification = profile.get("classification") or {}

    parts: list[str] = []

    # 1) _base.css aus design-hub (mit Default-:root) — kommt ZUERST
    base_css_path = dh_dir / "templates" / "_base.css"
    if base_css_path.exists():
        parts.append("/* ── design-hub _base.css ── */")
        parts.append(base_css_path.read_text(encoding="utf-8"))

    # 2) Profile-:root mit !important — überschreibt _base.css Defaults
    root_vars = [
        f"--primary: {c.get('primary', '#1A3A5C')} !important;",
        f"--primary-dark: {c.get('primary_dark', '#0D2840')} !important;",
        f"--text: {c.get('text', '#1F2937')} !important;",
        f"--text-muted: {c.get('text_muted', '#6B7280')} !important;",
        f"--bg-light: {c.get('bg_light', '#EDF3FA')} !important;",
        f"--border: {c.get('border', '#C8D8EC')} !important;",
        f"--zebra: {c.get('zebra', '#F3F7FC')} !important;",
        f"--line: {c.get('line', '#E5E7EB')} !important;",
        f"--accent-1: {c.get('accent_1', '#2C5F8A')} !important;",
        f"--accent-2: {c.get('accent_2', '#3D7AB5')} !important;",
        # WeasyPrint Header/Footer-Variablen
        f'--header-text: "{h.get("text", "")}";',
        f'--footer-classification: "{(classification.get("footer_text") or "")}";',
        f'--classification-banner-text: "{(classification.get("banner_text") or "")}";',
    ]
    parts.append("/* ── profile override (wins over _base.css defaults) ── */")
    parts.append(":root {\n  " + "\n  ".join(root_vars) + "\n}")

    # 3) @font-face Embedding aus Profile
    primary = fonts.get("primary_path")
    bold = fonts.get("bold_path")
    italic = fonts.get("italic_path")
    primary_name = fonts.get("primary", "Inter")
    fontface_lines: list[str] = []
    for asset_path, weight, style in (
        (primary, "400", "normal"),
        (bold,    "700", "normal"),
        (italic,  "400", "italic"),
    ):
        if not asset_path:
            continue
        _check_allowed_assets(profile, asset_path)
        full = (dh_dir / asset_path).resolve()
        if not full.exists():
            print(f"⚠ Font-Datei fehlt: {full}")
            continue
        fontface_lines.append(
            f'@font-face {{ font-family: "{primary_name}"; '
            f'src: url("file://{full}") format("woff2"); '
            f'font-weight: {weight}; font-style: {style}; font-display: swap; }}'
        )
    if fontface_lines:
        parts.append("/* ── profile fonts (@font-face) ── */")
        parts.extend(fontface_lines)

    # Body-Font-Stack als !important damit print_agent base.css nicht durchschlägt
    fallbacks = ', '.join(f'"{x}"' for x in fonts.get('fallbacks', ['sans-serif']))
    parts.append(
        f'body, p, li, td, th, h1, h2, h3, h4, h5 '
        f'{{ font-family: "{primary_name}", {fallbacks} !important; }}'
    )

    return "\n\n".join(parts) + "\n"


def convert_with_profile(input_path: Path, output_dir: Path, profile_name: str,
                          extra_css_extra: str = "") -> Path:
    """Profile-basierter Render-Pfad — wrapper um convert().

    Lädt Profile aus design-hub, prüft allowed_assets, baut extra-CSS mit
    CSS-Variablen + @font-face, ruft bestehende convert() auf.
    """
    profile, dh_dir = _load_profile(profile_name)
    name = profile.get("name", profile_name)
    print(f"🎯 Profile: {name} (design-hub: {dh_dir})")
    print(f"  authorship: {profile.get('authorship', {}).get('owner')} → {profile.get('authorship', {}).get('recipient')}")
    print(f"  allowed_assets: {profile.get('allowed_assets')}")

    # Logo-Asset-Check (wenn Profile Logo definiert)
    logo = profile.get("logo") or {}
    if logo.get("url"):
        _check_allowed_assets(profile, logo["url"])

    # Profile → Design-Dict (für bestehende convert())
    design = _profile_to_design(profile)
    global DESIGNS
    # Inject als temporäres design (überschreibt nicht persistent)
    DESIGNS[f"_profile:{name}"] = design

    # Profile-Extra-CSS — _base.css + Profile-Override + @font-face
    # (Reihenfolge im _build_profile_extra_css garantiert Override-Win)
    profile_extra = _build_profile_extra_css(profile, dh_dir)
    combined_extra = profile_extra + "\n" + extra_css_extra

    out = convert(input_path, output_dir, design_name=f"_profile:{name}",
                  extra_css=combined_extra)
    return out


def main():
    parser = argparse.ArgumentParser(description="IIL Print Agent — Markdown → PDF")
    parser.add_argument("input", help="Markdown-Quelldatei")
    parser.add_argument("output_dir", nargs="?", help="Ausgabeverzeichnis (optional)")
    parser.add_argument("--design", default=None,
                        help="LEGACY: Design-Key aus print_designs.yaml (meiki/iil/ttz/db)")
    parser.add_argument("--profile", default=None,
                        help="design-hub Profile (iil-extern, db-hybrid, db-intern) — empfohlen")
    parser.add_argument("--designs", default=None,
                        help="Pfad zu repo-spezifischem designs.yaml (LEGACY)")
    parser.add_argument("--extra-css", default=None,
                        help="Pfad zu repo-spezifischem extra.css (wird nach base.css geladen)")
    args = parser.parse_args()

    if args.profile and args.design:
        print("❌ --profile und --design sind exklusiv. Bitte nur eins setzen.")
        sys.exit(1)

    if args.designs:
        global DESIGNS
        DESIGNS = _load_designs(override_file=Path(args.designs))

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"❌ Datei nicht gefunden: {input_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else OUTPUT_DIR
    extra_css = Path(args.extra_css).read_text(encoding="utf-8") if args.extra_css and Path(args.extra_css).exists() else ""

    if args.profile:
        out = convert_with_profile(input_path, output_dir, args.profile, extra_css_extra=extra_css)
    else:
        design_name = args.design or "meiki"
        out = convert(input_path, output_dir, design_name=design_name, extra_css=extra_css)
    print(f"✅ PDF erstellt: {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
