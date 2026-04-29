#!/usr/bin/env python3
"""
IIL Print Agent — LLM-gestützter PDF-Generator mit Design-Switcher
Usage: python3 print_agent.py <input.md> [output_dir] [--design meiki|iil]

Designs: meiki (Standard), iil (IIL GmbH Corporate)
LLM: OpenAI gpt-4o-mini (~$0.00005/Dokument)
Fallback: Ohne LLM direkt PDF erzeugen
"""

import sys
import re
import json
import os
import argparse
from pathlib import Path

import yaml

import litellm
import markdown
from weasyprint import HTML, CSS

OUTPUT_DIR = Path.home() / "pdf-output"
SECRETS_DIRS = [
    Path("/home/devuser/shared/secrets"),
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


def _load_designs() -> dict:
    if _DESIGNS_FILE.exists():
        with _DESIGNS_FILE.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("designs", {})
    print(f"⚠️  {_DESIGNS_FILE} nicht gefunden — keine Designs verfügbar")
    return {}


DESIGNS = _load_designs()


def build_css(d: dict) -> str:
    """Injiziert nur :root-Variablen + @page @top-left; Rest kommt aus base.css."""
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
    return root_and_page + _BASE_CSS_STATIC


def get_secret(name: str) -> str | None:
    val = os.environ.get(name.upper())
    if val:
        return val
    for base in SECRETS_DIRS:
        path = base / name.lower()
        if path.exists():
            return path.read_text().strip()
    return None


def llm_enrich(title: str, md_text: str, design: dict) -> dict:
    """gpt-4o-mini — Executive Summary + Keywords (~$0.00005/Dokument)."""
    api_key = get_secret("openai_api_key")
    if not api_key:
        print("⚠️  Kein OpenAI API-Key — LLM-Schritt übersprungen")
        return {}

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

    try:
        response = litellm.completion(
            model="gpt-4o-mini",
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
    except Exception as e:
        print(f"⚠️  LLM-Fehler: {e} — fahre ohne Summary fort")
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


def preprocess_md(md_text: str) -> str:
    """Ersetzt ```gantt / ```tree / ```flow / ```arch / ```layer durch HTML."""
    def replace_gantt(m):  return parse_gantt_block(m.group(1))
    def replace_tree(m):   return parse_tree_block(m.group(1))
    def replace_flow(m):   return parse_flow_block(m.group(1))
    def replace_arch(m):   return parse_arch_block(m.group(1))
    def replace_layer(m):  return parse_layer_block(m.group(1))
    text = re.sub(r"```gantt\n(.*?)```", replace_gantt, md_text, flags=re.DOTALL)
    text = re.sub(r"```tree\n(.*?)```",  replace_tree,  text,    flags=re.DOTALL)
    text = re.sub(r"```flow\n(.*?)```",  replace_flow,  text,    flags=re.DOTALL)
    text = re.sub(r"```arch\n(.*?)```",  replace_arch,  text,    flags=re.DOTALL)
    text = re.sub(r"```layer\n(.*?)```", replace_layer, text,    flags=re.DOTALL)
    return text


_INLINE_PATTERNS = {
    "stand":       r"\*\*Stand:\*\*\s*([^|\n]+)",
    "zielgruppe":  r"\*\*Zielgruppe:\*\*\s*([^\n]+)",
    "angebot_nr":  r"\*\*Angebot Nr\.:\*\*\s*([^\n]+)",
    "datum":       r"\*\*Datum:\*\*\s*([^\n]+)",
    "gueltig_bis": r"\*\*Gültig bis:\*\*\s*([^\n]+)",
    "auftraggeber":r"\*\*Auftraggeber\*\*\s*\n+(.+)",
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


def _build_meta_rows(meta: dict, design: dict, stem: str) -> list:
    """Return list of (label, value) tuples for the meta table."""
    template = design.get("meta_template", "meiki")
    if template == "iil":
        rows = []
        if meta.get("angebot_nr"):  rows.append(("Angebot-Nr.", meta["angebot_nr"]))
        if meta.get("datum"):       rows.append(("Datum", meta["datum"]))
        if meta.get("gueltig_bis"): rows.append(("Gültig bis", meta["gueltig_bis"]))
        if meta.get("auftraggeber"): rows.append(("Auftraggeber", meta["auftraggeber"]))
        rows.append(("Auftragnehmer", "IIL GmbH · Achim Dehnert · kontakt@iil.gmbh"))
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
        date_line = f"Angebot · {meta.get('datum', '')}"
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


def convert(input_path: Path, output_dir: Path, design_name: str = "meiki") -> Path:
    design = DESIGNS.get(design_name, DESIGNS["meiki"])
    print(f"🎨 Design: {design_name}")

    md_text = input_path.read_text(encoding="utf-8")
    md_text_processed = preprocess_md(md_text)
    md = markdown.Markdown(extensions=["tables", "attr_list", "meta"])
    body_html = md.convert(md_text_processed)
    fm = {k: v for k, v in md.Meta.items()} if hasattr(md, "Meta") else {}
    meta = extract_meta(md_text, fm=fm)

    m = re.search(r"<h1>(.*?)</h1>", body_html)
    title = m.group(1) if m else input_path.stem
    body_html = re.sub(r"<h1>.*?</h1>", "", body_html, count=1)
    body_html = re.sub(r"<p><strong>Stand:</strong>.*?</p>", "", body_html, count=1)

    print("🤖 LLM-Anreicherung …")
    enrichment = llm_enrich(title, md_text, design)
    if enrichment.get("summary"):
        print(f"   ✅ Summary: {enrichment['summary'][:80]}…")
        print(f"   🏷️  Keywords: {', '.join(enrichment.get('keywords', []))}")

    html = build_html(title, body_html, meta, input_path.stem, enrichment, design)
    css = build_css(design)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{input_path.stem}.pdf"
    HTML(string=html, base_url="/").write_pdf(str(out_path), stylesheets=[CSS(string=css)])
    return out_path


def main():
    parser = argparse.ArgumentParser(description="IIL Print Agent — Markdown → PDF")
    parser.add_argument("input", help="Markdown-Quelldatei")
    parser.add_argument("output_dir", nargs="?", help="Ausgabeverzeichnis (optional)")
    parser.add_argument("--design", choices=list(DESIGNS.keys()), default="meiki",
                        help="Design-Profil: meiki (Standard) oder iil")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"❌ Datei nicht gefunden: {input_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else OUTPUT_DIR
    out = convert(input_path, output_dir, design_name=args.design)
    print(f"✅ PDF erstellt: {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
