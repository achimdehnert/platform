# Policy: Data Sovereignty & LLM-Egress

**Status:** 🟡 DRAFT — pending ratification by Achim Dehnert (iil.gmbh). Bis zur Ratifizierung
ist NICHTS aktiv: das `/adr-handoff-extern`-Hard-Gate bleibt unverändert kategorisch.

**Trigger words:** souverän, sovereign, egress, extern llm, externes modell, gpt, gemini,
openai, pseudonymisieren, anonymisieren, adr-handoff-extern, daten raus, datenschutz extern,
data sovereignty, mandantendaten

## Rule (Default — kategorisch, fail-closed)

Inhalte aus den Orgs **`ttz-lif`** und **`meiki-lra`** sowie **jeglicher Inhalt mit realen
Mandanten-/Personendaten** DÜRFEN NICHT an externe SaaS-LLM (OpenAI, Google, Anthropic-API
außerhalb der laufenden Session, …) gesendet werden. Die Org-Quelle ist **`git remote get-url
origin`** (autoritativ), nicht `project-facts.md`. Lässt sich die Org nicht eindeutig bestimmen
→ **ABORT** (fail-closed). Für adversariale Zweitmeinungen ohne Egress: `/adr-challenger`
(Ollama-local).

> Das Gate schützt den **Perimeter**, nicht nur Personendaten. „Kein PII" allein hebt die
> Schranke NICHT auf.

## Exception — PII-freie Architektur-/Technik-ADRs (eng, opt-in, fail-closed)

Ein **PII-freies Architektur-/Technik-ADR** DARF extern reviewt werden — **nur**, wenn **ALLE**
folgenden Bedingungen erfüllt und dokumentiert sind. Ist auch nur eine unklar → **ABORT**
(Default gewinnt).

| # | Bedingung |
|---|---|
| **E1 — PII-frei** | Keine personenbezogenen Daten: keine Bürger:innen, **keine namentlichen Sachbearbeiter:innen**, keine realen Fall-/Mandantendaten, keine Credentials/Secrets. |
| **E2 — Klasse** | Reines **Architektur-/Technik-/Entscheidungs**-Dokument (Design, Schnittstellen, Muster) — **kein** Daten-/Prozessdokument mit Echtsätzen. |
| **E3 — Pseudonymisierung** | Org-identifizierende Marker vor Egress ersetzen: Landkreis-Namen (Günzburg/Traunstein → `LK-A`/`LK-B`), Produktnamen (`d.velop`/`enaio` → `DMS-1`/`DMS-2`), Projektname (`MEiKI` → `Projekt-X`), OE-/Team-Namen → generisch. **Ehrlich:** Re-Identifikation über den **Kontext** (Domäne, Tech-Kombination) ist damit **nicht** vollständig ausgeschlossen → siehe E4. |
| **E4 — Vertrags-/Förder-Check** | **Ausdrückliche Bestätigung**, dass Auftraggeber-Vertrag UND Förderbedingungen die externe LLM-Verarbeitung (pseudonymisierter) Projektartefakte erlauben. Unbekannt/unbestätigt → **ABORT**. **Dies ist das eigentliche Gate.** |
| **E5 — Per-ADR-Freigabe** | Explizite Einzelfreigabe durch den **Owner** (Projektleiter) je ADR. **Nie** blanket/automatisch. |
| **E6 — Audit** | Protokollieren: pseudonymisierter Text(-Hash), Zeitpunkt, Provider+Modell, E1–E5-Prüfergebnis, Freigeber. Ablage nach `~/shared/` bzw. Audit-Log. |
| **E7 — Provider-Allowlist** | Nur ausdrücklich freigegebene externe Provider/Modelle. |

**Bevorzugt bleibt** der souveräne Weg (Ollama-local Spezialisten-Panel): er liefert die
gewünschte **Familien-Diversität** ohne Egress. Der externe Pfad ist die **Ausnahme, nicht die
Norm** — sinkender Grenznutzen vs. Souveränitäts-/Re-Identifikationsrisiko.

## Wirkung auf das `/adr-handoff-extern`-Gate (Implementierung, separat)

Das Hard-Gate (Step 4b.1) bleibt **ABORT by default**. Erst nach Ratifizierung dieser Policy
wird es so erweitert, dass es bei einem `meiki-lra`/`ttz-lif`-ADR **nur dann** durchlässt, wenn
E1–E7 maschinell/checklisten-geprüft **und** per-ADR signiert sind — sonst weiterhin ABORT.
Diese Änderung ist ein **eigener PR im `platform`-Repo** (Skill-Quelle:
`platform/.windsurf/workflows/adr-handoff-extern.md`).

## Anti-Patterns

- ❌ „Kein PII → also unbedenklich extern" — der Perimeter-Schutz ist breiter (E4!).
- ❌ Pseudonymisierung als stillen Bypass bauen, ohne E4/E5/Owner-Freigabe.
- ❌ Blanket-Freigabe „alle Arch-ADRs dürfen raus" — die Ausnahme ist **per ADR**.
- ❌ Bei Unklarheit senden — Default gewinnt (fail-closed).

## Changelog

- 2026-06-23: Initial **DRAFT**. Anlass: Wunsch nach externer Architektur-Zweitmeinung zu
  `meiki:ADR-041`, die das kategorische `meiki-lra`-Gate blockt. Entwurf einer engen,
  fail-closed Ausnahme für PII-freie Architektur-ADRs (E1–E7). **Nicht aktiv bis Ratifizierung.**
