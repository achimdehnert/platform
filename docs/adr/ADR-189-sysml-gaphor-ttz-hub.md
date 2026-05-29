---
status: accepted
date: 2026-05-08
decision-makers:
  - Achim Dehnert
consulted:
  - Gunther May (TTZ Leipheim)
informed:
  - Andrea Wirmer (TTZ Leipheim)
repo: ttz-hub
domains:
  - documentation
  - architecture
scope:
  include_paths:
    - docs/sysml/**
    - docs/technische_dokumentation.md
decision_drivers:
  - id: D-1
    driver: "TTZ Leipheim will SysML/Gaphor als Standardtool für Modellierung der Modellfabrik etablieren"
    weight: critical
    category: strategic
  - id: D-2
    driver: "Architektur-Dokumentation muss für Nicht-Softwareentwickler lesbar sein (Werksleiter, Maschinenbauer)"
    weight: high
    category: ergonomic
  - id: D-3
    driver: "IIL-Platform nutzt Mermaid + ADRs — kein Grund, plattformweit umzusteigen"
    weight: high
    category: operational
---

# ADR-189: SysML/Gaphor-Architekturmodell für ttz-hub

## Kontext

Das TTZ Leipheim (Auftraggeber KI Werkleiterassistent) plant, **SysML mit dem Open-Source-Tool Gaphor** als Standardwerkzeug für die Modellierung der Modellfabrik einzusetzen. Gunther May (TTZ) hat als Anforderung an Phase 1 formuliert:

> *„Dokumentation der Architektur per sysML über Open-Source-Tool Gaphor. Dies kann man auch teilautomatisiert z.B. über ChatGPT machen."*

Die IIL-Platform nutzt standardmäßig **Mermaid-Diagramme** in Markdown und ADRs. SysML/Gaphor ist signifikant aufwändiger (eigenes Tool, eigenes Dateiformat, GUI-abhängig).

## Entscheidung

**SysML/Gaphor wird ausschließlich für ttz-hub als Liefergegenstand (LG-03) erstellt — NICHT als IIL-Platform-Standard übernommen.**

### Scope: Nur ttz-hub

- Architekturmodell als `.gaphor`-Datei unter `docs/sysml/`
- Block Definition Diagram (Systemübersicht)
- Internal Block Diagram (Datenfluss NL2SQL-Pipeline)
- Activity Diagram (NL-Abfrage → SQL → Antwort)

### IIL-Platform bleibt bei Mermaid + ADRs

- Mermaid rendert nativ in GitHub, Outline, Markdown-PDFs
- Keine zusätzliche Toolchain nötig
- Alle Entwickler kennen die Syntax
- CI-Integration trivial

## Begründung

| Kriterium | SysML/Gaphor | Mermaid + ADRs |
|---|---|---|
| Zielgruppe TTZ | Maschinenbauer, Werksleiter | Softwareentwickler |
| Toolchain | GUI-App (GTK), eigenes Format | Text in Markdown |
| Git-Diff | XML-Diff (schwer lesbar) | Plain-text Diff |
| Automatisierung | LLM kann SysML-XML generieren | LLM kann Mermaid generieren |
| Aufwand pro Diagramm | ~30 Min (mit LLM-Assist) | ~10 Min |
| Kundenanforderung | Ja (TTZ explizit) | Nein |

**Entscheidend:** D-1 (Kundenanforderung) überwiegt für dieses Projekt. D-3 (Platform-Konsistenz) verhindert die Übernahme als Standard.

## Konsequenzen

### Positiv
- TTZ erhält Dokumentation in ihrem Zielformat
- `.gaphor`-Dateien sind versionierbar (XML)
- Gaphor ist Open Source (Apache 2.0) — keine Lizenzkosten

### Negativ
- Zusätzlicher Pflegeaufwand bei Architekturänderungen (Mermaid UND Gaphor aktualisieren)
- Gaphor-Installation nur auf Desktop mit GUI möglich (nicht headless)

### Regeln
- `docs/sysml/*.gaphor` — Gaphor-Modelldateien NUR in ttz-hub
- Bei Architekturänderungen: Mermaid in `technische_dokumentation.md` ist führend, `.gaphor` wird nachgezogen
- **SVG-Export Pflicht:** Jede `.gaphor`-Datei muss eine gleichnamige `.svg`-Datei daneben haben (z.B. `ttz_hub_architecture.gaphor` + `ttz_hub_architecture.svg`). SVG rendert in GitHub/Browser ohne Gaphor-Installation.
- Keine Gaphor-Abhängigkeit in CI/CD — Diagramme und SVG-Exports werden manuell/LLM-assistiert gepflegt

## Offene Fragen

- [x] ~~Soll Gaphor auch SVG-Exports im Repo ablegen?~~ → **Ja, Pflicht.** SVG neben jeder `.gaphor`-Datei.
- [ ] GitHub Action für automatischen `.gaphor` → SVG-Export (nice-to-have, braucht `xvfb-run` + Gaphor CLI)
