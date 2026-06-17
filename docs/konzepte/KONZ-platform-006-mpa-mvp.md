---
concept_id: KONZ-platform-006
title: mPA-MVP — myPersonalAssistant als erster MVP des Telefon-/Sprachagent-Produkts
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []   # kein SoR-Spec: Greenfield-Produkt vor Spec-Stufe; Anker = platform:ADR-249
adr_threshold: kein neuer ADR — Architektur bereits in platform:ADR-249; dies ist MVP-Execution darunter
review_by: 2026-08-15
kill_criteria: "Ein zweiter LLM-Adapter (lokal, OpenAI-kompatibel) lässt sich NICHT ohne Änderung am Agent-Core einsetzen (>0 Core-Zeilen) → Swappable-Ports-These falsifiziert, Stopp VOR strict-Pilot-Invest."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: docs/adr/ADR-249-telefonagent-produkt-swappable-ports.md, commit_or_pr: "#588", opened_in_session: true}
created: 2026-06-17
---

# KONZ-platform-006 — mPA-MVP

> **Off-Ramp:** Dieses Konzept inkubiert in `platform` neben dem Anker `ADR-249`. Beim
> Onboarding des iilgmbh-Produkt-Repos zieht es dorthin um (`pipeline_status` weiterziehen,
> dieses Doc als Quelle markieren). Schreibadresse heute = platform, weil das Ziel-Repo
> noch nicht existiert.

## Kernthese
Der mPA-MVP beweist die ADR-249-Engine **billig im `open`-Profil**, indem er den **schmalsten
End-to-End-Textpfad** baut (Agent-Core + 1 LLM-Port + 1 Knowledge-Port über *eine*
live-mutable Quelle) — und dabei die Port-Nähte **und** das Souveränitäts-**Policy**-Profil
ab Commit 1 einzieht, sodass der spätere strict-Pilot ein **Config-Swap statt Rewrite** bleibt.

## Assumption-/Decision-/Risk-Ledger
| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| D1 | Heimat = neues iilgmbh-Repo; Konzept inkubiert bis dahin in platform | Entscheidung | E1 (ADR-249 §2.1, C1) | offen |
| D2 | Tier T2 — T3-Architektur schon in ADR-249, hier nur MVP-Slice | Entscheidung | D (SSoT-Regel: nicht neu aufrollen) | gesetzt |
| D3 | MVP = **Text-Core zuerst**; Voice nur als Adapter-**Naht** + 1 turn-based STT/TTS-Durchstich (kein Telefon) | Entscheidung | E1 (ADR-249 §2.3, G-4) | gesetzt |
| D4 | 1 LLM-Port-Adapter (Cloud, OpenAI-kompatibel) im `open`-Profil | Entscheidung | E1 (ADR-249 §2.2, G-5) | gesetzt |
| D5 | 1 Knowledge-Quelle = OneDrive-Ordner (live-mutable), v0 = nächtlicher Voll-Resync | Entscheidung | E1 (ADR-249 §2.4 Right-Sizing) | gesetzt |
| D6 | `tenant_profile` ab Commit 1 als **Policy** (Datenfluss/Logging/Retention-Felder), nicht nur Adapter-Allowlist | Entscheidung | E1 (ADR-249 §2.2 REC-6) | gesetzt |
| A1 | MS-Graph-Zugriff auf OneDrive mit eigenem M365-Tenant-Account möglich | Annahme | Falsifikation: keine App-Registrierung im eigenen M365 → Fallback ALT-2 (lokaler Ordner) | **zu prüfen** |
| A2 | Cloud-LLM im MVP zulässig (eigene Betreiberdaten, kein Bürger) | Annahme | E1 (ADR-249 G-5) | gesetzt |
| R1 | Cloud-only-MVP **beweist die Swappability nicht** — „austauschbar" bleibt Behauptung ohne zweiten Adapter | Risiko | → Kill-Gate macht 2. Adapter zum Akzeptanzkriterium | mitigiert |
| R2 | OAuth/PII zieht Komplexität in den „einfachen" MVP | Risiko | → nur kuratierter OneDrive-Ordner; E-Mail erst v1 | mitigiert |
| R3 | `tenant_profile` nur als Allowlist → Souveränität später = Rewrite | Risiko | → D6 + Smoke-Test (strict-Dummy lehnt Cloud-Adapter ab) | mitigiert |

## MVC (Minimal Viable Cut — konkret, keine Anforderungsprosa)
Komponenten im neuen iilgmbh-Repo (Python):
- `core/agent.py` — **modalitäts-agnostischer** Loop: Text-Eingabe → Tool-Calls/RAG → Text-Ausgabe. Kennt **keine** Adapter-Konkreta.
- `ports/llm.py` — Port-Interface (Capability-Contract: Tool-Calls, Streaming, Fehlerklassen, Timeout/Retry) + **1** Cloud-Adapter (`adapters/llm_openai_compatible.py`).
- `ports/knowledge.py` — Retriever-Interface (`ingest()`/`query()→chunks`) + **1** Adapter `adapters/knowledge_onedrive.py` (Graph-Pull → pgvector); v0-Frische = nächtlicher Voll-Resync-Job.
- `ports/voice.py` — Interface (STT davor / TTS dahinter) + **1** dünner turn-based Adapter (Datei-Audio rein/raus, **kein** SIP/Barge-in).
- `profile.py` — `tenant_profile` mit Feldern `{sovereignty, allowed_adapters, logging, retention, data_flow}`; MVP lädt `open.yaml`.
- `tests/test_profile_strict_rejects_cloud.py` — lädt ein **strict-Dummy-Profil** und prüft, dass ein Cloud-Adapter abgelehnt wird (Policy-Mechanik, **ohne** lokale Inferenz).
- `tests/test_llm_swap.py` — Akzeptanztest Kill-Gate: zweiter (Dummy-lokaler) LLM-Adapter läuft **ohne** Core-Edit.

Bewusst **NICHT** im MVP: Telefonie/SIP, full-duplex/<400 ms, on-prem-Runtime, Temporal-RAG (Rechts-Corpus), OCOS, Lösch-Tombstones/Delta-Sync, E-Mail-Quelle.

## Kill-Gate + Threshold
- **Mess-Schwelle:** `test_llm_swap.py` rot, d. h. ein 2. OpenAI-kompatibler Adapter erzwingt **>0 Zeilen** Agent-Core-Änderung → **Stopp**, Architektur-Naht (ADR-249 G-1) ist nicht real, **kein** strict-Pilot-Invest.
- **Zeit-Schwelle:** kein grüner End-to-End-Textpfad (Frage → OneDrive-RAG → belegte Antwort) bis **`review_by` 2026-08-15** → Konzept `stale`, Re-Scope.
- **Exception-Budget:** 1× Verlängerung um max. 4 Wochen, datiert begründet; danach `sunset`.

## Befunde (inkl. Adversariat, inline)
| ID | Rolle | Befund | Schwere | Konsequenz |
|---|---|---|---|---|
| STEEL-1 | Steelman | Der Slice ist korrekt schmal: 1 LLM- + 1 Knowledge-Port über *eine* live-mutable Quelle prüft genau die zwei riskantesten Nähte (Runtime-Swap + Frische) ohne Telefonie-Last | — | Slice halten |
| AD-1 | Diabolus | Cloud-only beweist Swappability **nicht** — ohne real laufenden 2. Adapter ist „austauschbar" Prosa | hoch | Kill-Gate `test_llm_swap.py` = Pflicht-Akzeptanzkriterium (nicht optional) |
| AD-2 | Diabolus | „nightly resync" maskiert das **Lösch-Problem** (Tombstones) → Frische-Naht nur halb bewiesen | mittel | ehrlich im MVC benannt; live-mutable-Löschung explizit v1 |
| AD-3 | Diabolus | `open`-Profil testet die **strict-Policy nie** → der Schalter ist unvalidiert | hoch | `test_profile_strict_rejects_cloud.py` validiert die Policy-Mechanik im MVP |
| M28-1 | Maintainer 2028 | Bleibt Voice ein reiner Interface-Stub, trifft die Telefonie-Realität (G-4) erst im Pilot auf den Core | mittel | 1 turn-based STT/TTS-Durchstich ist MVP-Soll (D3) — Core sieht einmal echten Audio-Roundtrip |

**Konflikt/Dissens:** keine echte Divergenz zwischen den Rollen — Diabolus verschärft Akzeptanzkriterien, kippt die Kernthese nicht.

## Alternativen
| ID | Idee | Vorteil | Nachteil | verworfen? |
|---|---|---|---|---|
| ALT-1 | Voice-first MVP statt text-first | testet Produkt-USP früh | zieht ASR/TTS+Latenz in den MVP, verzögert Engine-Beweis | ja — ADR-249 §2.3 (Text-Core zuerst) |
| ALT-2 | Knowledge-Quelle = lokaler Datei-Ordner statt OneDrive/Graph | kein OAuth/Graph-Overhead, schnellster Engine-Beweis | testet live-mutable-Sync-Naht (Change-Detection) schwächer | bedingt — **als Fallback zu A1** behalten |

## Entscheidung
**Bauen als T2-MVP nach MVC**, Heimat neues iilgmbh-Repo (Off-Ramp). Erste Aktion nach
Repo-Onboarding: die zwei Akzeptanztests (`test_llm_swap`, `test_profile_strict_rejects_cloud`)
**zuerst** schreiben — sie sind das Kill-Gate, nicht Beiwerk.
