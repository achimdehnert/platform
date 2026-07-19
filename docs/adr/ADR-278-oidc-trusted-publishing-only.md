---
id: ADR-278
title: "OIDC Trusted Publishing als einziger PyPI-Publish-Pfad für iil-Pakete; API-Token-Publishing verboten + CI-Enforcement-Gate"
status: proposed
decision_date: 2026-07-19
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
supersedes: []
related: [ADR-266, ADR-209, ADR-255]
tags: [pypi, oidc, trusted-publishing, ci, enforcement, gate, prevention, supply-chain, governance]
drift_check_paths:
  - "tools/check_publish_oidc_auth.py"
  - ".github/workflows/publish-iil-codeguard.yml"
  - ".github/workflows/publish-iil-ingest.yml"
---

# ADR-278: OIDC Trusted Publishing als einziger PyPI-Publish-Pfad für iil-Pakete

> **Kurz:** Alle `iil-*`-Pakete publizieren nach PyPI **ausschließlich** über
> **OIDC Trusted Publishing** (`pypa/gh-action-pypi-publish` **ohne** `password:`-Input).
> API-Token-basiertes Publishing (`password: ${{ secrets.*_API_TOKEN }}` im PyPI-Upload-Step)
> ist **verboten** und wird von einem **CI-Gate** abgelehnt. Prävention vor Detektion (ADR-209).

## Kontext / Problem

Der Publish-Pfad der `iil-*`-Pakete war **uneinheitlich und fragil**. Belege aus einer
einzigen Session (2026-07-19):

- **promptfw**: alle `publish.yml`-Runs seit 2026-03 rot — `403 Forbidden` (ungültiges/fehlendes
  API-Token). Zusätzlich hebelte der `password:`-Input Trusted Publishing **aktiv** aus
  („disabling Trusted Publishing", pypa-Action-Warnung) und ignorierte Attestations.
- **weltenfw**: identisches `password:`-Muster.
- **outlinefw**: schon token-frei, aber **ohne** Trusted-Publisher-Bindung → `invalid-publisher`.

Wurzelprobleme, die Token-Publishing strukturell mitbringt:

1. **Geheimnis-Rotation & -Streuung**: jedes Repo braucht ein PyPI-API-Token als Secret;
   Ablauf/Fehlkonfiguration → 403, oft erst beim Release bemerkt.
2. **Keine Provenance**: `password:`-Input deaktiviert `attestations` → keine PEP-740-Provenance.
3. **Inkonsistenz**: Repo-Name vs. Dist-Name vs. zentraler Publish-Ort (platform) sind je Paket
   verschieden verdrahtet — jede Abweichung ist eine eigene Fehlerquelle (Realfall: Bindungen auf
   nicht existierende Dist-Namen `iil-aifw`/`iil-learnfw` statt auf die Repos `aifw`/`learnfw`).

ADR-266 hatte OIDC-Readiness als Programm gestartet, aber **keinen erzwingenden Endzustand**
definiert — Repos konnten still auf Token zurückfallen.

## Entscheidung

1. **OIDC-only**: `iil-*`-Pakete publizieren nach PyPI ausschließlich via OIDC Trusted Publishing.
   Der PyPI-Upload-Step nutzt `pypa/gh-action-pypi-publish` **ohne** `password:`-Input, mit
   `permissions: id-token: write` und einer `environment:` (Konvention: `pypi`).
2. **Token verboten**: Ein `password: ${{ secrets.*_API_TOKEN }}` (oder `user: __token__` +
   Passwort) im **PyPI**-Upload-Step ist nicht mehr zulässig. (TestPyPI bleibt unberührt.)
3. **Bindung gehört auf das publizierende Repo**: Die Trusted-Publisher-Bindung wird auf das
   GitHub-Repo gesetzt, dessen Workflow den OIDC-Token ausstellt — den **Repo-Namen**, nicht den
   PyPI-Dist-Namen. Für **zentral aus `platform`** publizierte Pakete (codeguard, ingest) zeigt die
   Bindung auf `repo=achimdehnert/platform` + den konkreten Workflow-Dateinamen (siehe #1265), nicht
   auf das Paket-Repo.
4. **Enforcement-Gate (Prävention)**: Ein CI-Check lehnt jede `*publish*.yml` ab, deren
   PyPI-Upload-Step einen `password:`-Input trägt. Referenz-Implementierung: `tools/check_publish_oidc_auth.py`
   (in diesem PR). Rollout in die Fleet über die shared-CI (als non-blocking `warn` startend,
   dann `block` — analog ADR-209 „warn-first"), sodass jedes Repo den Check bei jedem CI-Lauf
   ausführt. Der Token-Secret im Repo darf erst **nach** bewiesener Bindung entfernt werden
   (🌀 ADR-266: nie Token ohne Binding-Beweis raus) — das Gate prüft den **Workflow-Input**, nicht
   die Existenz des Secrets.

## Konsequenzen

**Positiv**
- Einheitlicher, byte-gleicher Publish-Pfad in allen Repos → „stringent + konsistent".
- Kein PyPI-API-Token mehr als Repo-Secret → nichts zu rotieren, keine 403-durch-Ablauf-Klasse.
- Attestations/PEP-740-Provenance automatisch aktiv.
- Publish bleibt ein **bewusster menschlicher Akt** (Tag-Push / `workflow_dispatch`) — kein
  stehendes Publish-Recht bei Automaten/Agenten nötig (deckt sich mit Lotsen-Charta Art. 8).

**Negativ / Kosten**
- Je PyPI-Projekt ist **einmalig** eine Trusted-Publisher-Bindung im PyPI-UI anzulegen
  (Owner-Schritt, headless nicht automatisierbar — ADR-266-Grenze).
- Zentral publizierte Pakete (codeguard/ingest) brauchen den Umbau der platform-Workflows auf OIDC
  (Token/twine → `id-token: write`), getrackt in #1265.

## Umsetzungsstand (2026-07-19)

- **Live via OIDC**: iil-promptfw 0.8.1, iil-outlinefw 0.3.2, iil-weltenfw 0.4.1.
- **PRs offen (password-Removal)**: iil-django-commons, aifw (→ iil-aifw), learnfw (→ iil-learnfw).
- **Klasse B (zentral aus platform)**: iil-codeguard, iil-ingest → #1265.
- **Enforcement-Gate**: Referenz-Skript in diesem PR; shared-CI-Verdrahtung als Folge-Schritt
  (warn → block), sobald ADR accepted.

## Kill-Gate / Review

Review-Termin **2026-10-19** (T+90): Ist das Gate in der shared-CI aktiv (block) und sind alle 7
Repos token-frei? Wenn nach 90 Tagen noch Token-Publishing existiert, das das Gate nicht fängt,
ist die Enforcement-Verdrahtung zu überarbeiten (nicht das Prinzip).
