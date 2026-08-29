---
concept_id: KONZ-platform-053
title: "ASUS Ascent GX10 in der Flotte — Rolle, Perimeter, Ausbaustufen"
pipeline_status: pilot   # 2026-08-29: Owner-Entscheid — Rolle A, Phase 1, Ausbau B (§3)
tier: T2
owner: "Achim Dehnert"
spec_refs: [platform:ADR-296, platform:ADR-257, platform:KONZ-platform-042, platform:KONZ-platform-021]
adr_threshold: >
  Heute kein ADR. ADR-296 führt "Multi-GPU / zweite Box" als Nicht-Ziel — das bleibt
  unberührt, solange die beiden Geräte unabhängige Lanes sind und kein Konsument
  zwischen ihnen wählen muss. Die Amendment-Auslöser stehen in §7; tritt einer ein,
  ist es ein Amendment zu ADR-296, kein neuer Org-ADR.
review_by: 2026-10-10
kill_criteria: >
  K1: Läuft bis 2026-10-10 keine Last dauerhaft auf dem Knoten, die vorher nicht lief.
  K2: Die arm64-Bestandsaufnahme scheitert an mehr als der Hälfte der Kandidaten aus §5.
  Bei K1 ODER K2 fällt der Knoten auf die Rolle "Trainingsgerät für robo-lab" zurück —
  kein zweiter Knoten, kein Runner, Cloud bleibt Default für alles Übrige.
created: 2026-08-29
---

# KONZ-platform-053 — GX10: Rolle, Perimeter, Ausbaustufen

## 1. Fakt

Ab KW 36/2026 steht ein ASUS Ascent GX10 zur Verfügung: NVIDIA GB10, rund 126 GB
gemeinsam adressierter Speicher, **aarch64**. Die Flotte hat bis dahin genau eine GPU —
die RTX 4090 mit 24 GB auf dem Owner-Desktop hinter `wg0`. Sie trägt Bild (ComfyUI),
Text (Ollama), Robotik-Training und seit 2026-08-28 den CI-Runner `ci-gpu` für
writing-hub. ADR-296 bewirtschaftet diese eine Karte über einen Lease-Arbiter.

Belegte Ausgangslage (in dieser Sitzung geöffnet):

| #  | Beleg | Fundort |
|----|-------|---------|
| B1 | ADR-296 führt "Multi-GPU / zweite Box" ausdrücklich als **Nicht-Ziel** | `docs/adr/ADR-296-…md` Z. 560 |
| B2 | shared-ci baut amd64: `_deploy-unified.yml` Z. 218 hart verdrahtet, **kein** `arm64` im ganzen Repo | `shared-ci/.github/workflows/` |
| B3 | Alle drei registrierten Runner tragen das Label `X64` | `infra/hosts.yaml` §runners |
| B4 | MEiKI-Kette: LRA verantwortlich → HNU Auftragsverarbeiter → Hetzner Unterauftragnehmer; **IIL kommt nicht vor** | Owner-Auskunft 2026-07-22 |
| B5 | Pilot liegt auf deutschem Server mit BSI-C5-Typ-2-Testat | ebd. |
| B6 | KONZ-042 Kernempfehlung: `ubuntu-latest` ist **Default** für Build/Test der Flotte | `KONZ-platform-042` §1 |
| B7 | strict ist auf `qwen2.5:7b` validiert (guenzburg-80-Gate); T1a ist `gpt-oss-120b` | `~/.claude/policies/llm-routing.md` |
| B8 | `ollama.iil.pet` ist für strict-Bürgerdaten gesperrt (Tunnel auf privaten LAN-Host) | Perimeter-Regel, Memory |
| B9 | Actions-Minuten 2.700/3.000; writing-hub = 70 % der hosted Minuten; Treiber ist Job-Rundung (13 Jobs, 6 davon < 15 s), nicht Rechenleistung | [platform#2392](https://github.com/achimdehnert/platform/issues/2392) |
| B10 | writing-hub referenziert im Code weiterhin `groq/llama-3.3-70b-versatile` — ein Modell, das laut Policy-Reality-Check vom 2026-08-25 **nicht mehr existiert** | `apps/authoring/defaults.py`, `services/laenge.py`, `pruefe_lesbarkeit.py` |
| B11 | robo-lab trainiert auf W11 + RTX 4090 **unter WSL2**, torch 2.13.0+cu130, Python 3.11 (conda) | `robo-lab/docs/mjlab-workstation.md` |

## 2. Analyse

Der GX10 hat die fünffache Speicherkapazität der 4090, aber laut Hersteller-Spec nur
rund ein Viertel ihrer Speicherbandbreite. Er ist damit kein schnelleres Gerät, sondern
ein anderes: er hält Modelle, die die 4090 nicht laden kann (120B-Klasse resident,
Finetuning jenseits von 24 GB), ist aber bei bandbreitengebundenen Lasten — Bild,
Einzelstrom-Token kleiner Modelle — nicht die bessere Wahl.

Zwei Bruchkanten treffen die Flotte quer. Architektonisch steht aarch64 gegen eine
amd64-only-Build-Kette (B2/B3): ein Bild, das der GX10 baut, läuft auf keinem unserer
Hetzner-Hosts. Rechtlich bringt ein Gerät in Owner- oder IIL-Räumen für Bürgerdaten
**kein** besseres Schutzniveau, sondern nur ein zusätzliches Unterauftragsverhältnis
mit Anzeigepflicht nach § 80 Abs. 2 SGB X — der Pilot liegt bereits C5-testiert (B4/B5).

Der echte Gewinn liegt woanders: bei Daten, für die **IIL selbst Verantwortlicher** ist.
Dort braucht es keine AV-Kette, und dort geht heute jeder LLM-Call an Groq, Cerebras
oder Anthropic.

## 3. Entscheidung (Owner, 2026-08-29)

| #  | Frage | Entscheid |
|----|-------|-----------|
| E1 | Rolle in der Verarbeitungskette | **A: IIL-interner Inferenz- und Trainingsknoten**, ausdrücklich außerhalb des Bürgerdaten-Perimeters |
| E2 | CI-Runner? | **Phase 1: nein.** Reiner Rechenknoten; Runner frühestens nach §6 |
| E3 | Zweiter Knoten / Kopplung | **B: später, unabhängiger Knoten** statt ConnectX-Kopplung — Auslösebedingung in §6 |

Nicht entschieden und weiterhin offen: der physische Standort (Owner-Räume oder
IIL-Geschäftsräume). Er ändert an E1 nichts, wird aber für den `hosts.yaml`-Eintrag
gebraucht und ist dort als `TBD` geführt.

## 4. Perimeter

Der Knoten wird wie `ollama.iil.pet` behandelt (B8), nicht strenger und nicht laxer:

- **Erlaubt:** Daten, für die IIL Verantwortlicher ist — eigenes Postfach, Paperless,
  sevdesk-Belege, Manuskripte, Ausschreibungsunterlagen, Repo-Inhalte, Benchmarks.
- **Nicht erlaubt:** Sozial- und Bürgerdaten aus der MEiKI-Kette, gleich in welcher
  Form und gleich wie kurz. Diese Kette läuft ohne IIL und bleibt es.
- **Zugang:** `wg0`-Peer wie die 4090. **Kein** öffentlicher Tunnel — das war der Fehler,
  der `ollama.iil.pet` für strict-Lasten unbrauchbar macht.
- Ein Modellwechsel für ein strict-Profil bleibt an das guenzburg-80-Gate gebunden;
  Kapazität ist kein Freibrief für ein ungeprüftes Modell.

## 5. Was sich cross-repo ändert

| #  | Repo | Neu möglich | Voraussetzung |
|----|------|-------------|---------------|
| C1 | writing-hub | Batch-Lane ohne Verdrängung durch Bild/Ton | eigene Lane, kein Arbiter nötig |
| C2 | writing-hub | Finetune/LoRA jenseits 24 GB | Speicher reicht erstmals |
| C3 | illustration-hub, music-lab | 4090 wird entlastet, weniger Verdrängung | Textlasten wandern ab |
| C4 | aifw, mcp-hub | lokaler T1a-Zwilling (`gpt-oss-120b`) | Eintrag im ADR-208-Resolver |
| C5 | ttz-hub | lokaler Pfad mit großem statt kleinem Modell | Ollama auf aarch64 (H2) |
| C6 | robo-lab | zweite Trainings-Karte, keine Konkurrenz mit Medien | mjlab auf aarch64 (H3) |
| C7 | doc-hub, sevdesk-Strecke | Belegextraktion lokal | **offen**, siehe §5b |
| C8 | shared-ci | Multi-Arch-Bilder | `platforms`-Input existiert, Deploy hart (B2) |

C4 und C8 sind die einzigen Zeilen, die überhaupt eine Änderung in einem fremden Repo
verlangen. Alles Übrige läuft über den Knoten selbst.

## 5b. Anwendungsfälle ab Werk — und was davon bei uns andockt

Der Knoten bringt den NVIDIA-AI-Stack mit. Die folgende Liste ist **Herstellerebene,
von uns nicht gemessen**, und steht unter demselben aarch64-Vorbehalt wie §8.

| #  | Anwendungsfall | Andockstelle | Vorbehalt |
|----|----------------|--------------|-----------|
| A1 | Spracherkennung | iil-voice-agent, Besprechungsmitschriften | Modell auf aarch64 |
| A2 | Sprachsynthese | iil-voice-agent | Lizenz je Stimme |
| A3 | Dokumentenverstehen, OCR + Layout | doc-hub, Rechnungsstrecke, ausschreibungs-hub | **kein belegter Bedarf**, s.u. |
| A4 | Embeddings in großen Mengen | pgvector-Neuaufbau, klickdummy-search | reiner Durchsatz |
| A5 | Bild- und Videoerzeugung | illustration-hub | 4090 bleibt für Latenz besser |
| A6 | Robotik-Simulation, Policy-Training | robo-lab | H3/H6 ungeprüft |
| A7 | Reranking, lokale Suche | alle Hubs mit Recherche | klein, ständig gebraucht |
| A8 | Code-Modelle lokal | Review ohne Abfluss | Qualität unter Frontier |

**Reihenfolge nach Nutzen je Aufwand: A4, dann A1.** A4 ist reiner Durchsatz ohne
Qualitätsrisiko. A1 hat in `iil-voice-agent` bereits beide Wege verdrahtet — Cloud
**und** lokal —, der Knoten ersetzt dort also einen bestehenden Pfad statt einen neuen
zu erfinden.

**A3 bleibt ausdrücklich offen.** Die Annahme, Belege und Ausschreibungen liefen heute
über Cloud-Modelle, hat sich bei der Gegenprobe **nicht** bestätigt: in `doc-hub` findet
die Suche nach Cloud-Anbietern null Treffer, in `ausschreibungs-hub` genau einen, und der
liegt in einer Testdatei. Positivkontrolle des Suchmusters an `iil-voice-agent` bestanden
(dort werden Cloud-Anbieter **und** der Ollama-Pfad gefunden), die Null ist also echt.
Damit wäre A3 keine Verlagerung eines Abflusses, sondern eine **neue** Fähigkeit — und
die braucht eine eigene Begründung, bevor sie auf diese Liste rutscht.

## 5a. writing-hub im Einzelnen — Kosten und Qualität

Getrennt beantwortet, weil beides oft in einen Topf fällt (Anschaffung ausgeklammert).

**Kosten: kein Vorteil, eher ein Nachteil.** writing-hub fährt heute die T1a-Klasse bei
Groq (`openai/gpt-oss-120b`, `qwen/qwen3.6-27b`) — Tokenpreise dieser Klasse liegen ein
bis zwei Größenordnungen unter Frontier-Modellen. Ein Kapitel von 1.200 Wörtern kostet
Bruchteile eines Cents; selbst intensiver Buchbetrieb bleibt im niedrigen zweistelligen
Eurobereich pro Jahr. Der Dauerstrom eines Knotens unter Last liegt darüber. Die
Größenordnung ist dieselbe wie in der bereits belegten Rechnung zur EU-Inferenz: dort
war der **Strom allein** rund fünfmal so teuer wie die gesamte Cloud-Rechnung.

**Qualität: ja, an vier Stellen — und die erste ist die wichtigste.**

| #  | Vorteil | Warum das nur lokal geht |
|----|---------|--------------------------|
| Q1 | **Stabile Gewichte** | Groq hat die T1a-Sprosse binnen Monaten zweimal abgeräumt; writing-hub trägt deshalb tote Modell-IDs im Code (B10). Lokale Gewichte verschwinden nicht. |
| Q2 | **Stil-Finetune** | LoRA auf Achims Korpus jenseits von 24 GB — bei keinem Anbieter der T1a-Klasse als gehostetes Custom-Modell zu haben. |
| Q3 | **Breite statt Sparsamkeit** | Ohne Token-Zähler und Rate-Limit sind fünf Kandidatenfassungen je Kapitel und eine Auswahl daraus normal statt teuer. |
| Q4 | **Ganzes Manuskript im Kontext** | 126 GB erlauben großes Modell **plus** großen KV-Cache — Kohärenz über Kapitelgrenzen statt kapitelweiser Blindheit. Unbelegt, siehe H1/H5. |

Q1 richtet heute schon Schaden an: der Code beschreibt Messwerte gegen ein Modell, das es
nicht mehr gibt. Das ist unabhängig vom GX10 ein Aufräumauftrag.

**Wo verdrahtet:** `AIActionType.default_model` je Action-Code, Router in
`apps/authoring/services/llm_router.py`, Provider-Auflösung in `apps/core/modellwahl.py`.
Der `ollama/`-Pfad existiert dort bereits — inklusive der dokumentierten Falle, dass
litellm im Prod-Container auf `localhost:11434` zeigt statt auf den Knoten. Genau diese
Zeile ist die Arbeit, kein Umbau.

## 6. Ausbaustufen

**Phase 1 (ab KW 36, kein Enddatum):** reiner Inferenz- und Trainingsknoten. Kein
GitHub-Runner. Konsumenten sprechen das Gerät direkt an; der ADR-296-Arbiter bleibt
unberührt, weil zwei unabhängige Geräte keine gemeinsame Ressource haben.

**Phase 2 — Runner (frühestens +30 Tage):** ein *repo-scoped* Runner mit eigenem Label
`ci-gpu-arm`, ausschließlich für Jobs, die die große Speicherklasse wirklich brauchen
(Modell-Benchmark gegen das guenzburg-80-Gate, LoRA-Läufe, robo-lab-Training). **Niemals**
als allgemeiner Build-Runner: die Flotte deployt x86 (B2), und KONZ-042 hat `ubuntu-latest`
gerade erst zum Default gemacht (B6). Auslöser: zwei dokumentierte Fälle, die auf
`ubuntu-latest` nicht laufen können.

**Warum der Knoten kein Mittel gegen die Actions-Rechnung ist:** Der Hebel ist bereits
gezogen. writing-hub — 70 % der Minuten — läuft seit 2026-08-28 auf dem `ci-gpu`-Runner
der 4090-Box, und die eigentliche Ursache war strukturell: 13 Jobs je Lauf, sechs davon
unter 15 Sekunden, jeder auf eine volle Minute aufgerundet (B9). Behoben hat das
`shared-ci` v1.1.12 samt Branch-Protection-Umbau, nicht Rechenleistung. Ein self-hosted
Runner spart Minuten unabhängig davon, *welche* Maschine er ist; dafür genügt jede
x86-Kiste, und mit `staging-ci` steht bereits eine. Für diesen Zweck ist der GX10 der
**schlechteste** Kandidat der Flotte, weil er als einziger aarch64 ist (B2/B3).

**Phase 3 — zweiter Knoten (offen):** Auslösebedingung ist **UND**-verknüpft. Es braucht
einen dokumentierten Workload, der **(a)** auf 126 GB nachweislich scheitert oder dauerhaft
zwei Lanes gleichzeitig belegt, **und (b)** aus einem benannten Grund nicht in die Cloud darf.
Beides zusammen, nicht einzeln — sonst kauft das Argument "wäre schön" die Kiste. Gekauft
wird dann ein **unabhängiger** Knoten, keine ConnectX-Kopplung: zwei gekoppelte Geräte sind
ein großer Rechner mit **einer** Warteschlange, zwei unabhängige sind zwei Lanes — und der
belegte Schmerz aus ADR-296 ist Verdrängung, nicht Modellgröße. Die Kopplung setzt zudem
beide Geräte an denselben Ort voraus.

## 7. Amendment-Auslöser für ADR-296

ADR-296 bleibt gültig, solange die Geräte unabhängig sind. Ein Amendment wird fällig,
sobald einer dieser Fälle eintritt:

1. Ein Konsument muss zwischen 4090 und GX10 **wählen** (Routing-Entscheidung statt
   fester Zuordnung).
2. Eine Lane wandert so, dass der Arbiter eine Zuordnung führt, die nicht mehr stimmt.
3. Phase 3 tritt ein — ab dem zweiten Knoten ist "Ressource" eine Dimension, kein Singular.

Bis dahin genügt dieses Konzept; ein ADR jetzt wäre überschießend.

## 8. Hypothesen — ausdrücklich unbelegt

| #  | Hypothese | Billigster Check |
|----|-----------|------------------|
| H1 | Ein 120B-Modell zu laden dauert auf dem Knoten Minuten, nicht Sekunden | erster Ladelauf am Gerät, Zeit mitschreiben |
| H2 | Ollama läuft auf aarch64 mit CUDA-Beschleunigung | Ollama-Release-Matrix lesen, dann ein Lauf |
| H3 | mjlab/MuJoCo-Warp läuft auf aarch64 | Anforderungsseite der mjlab-Doku |
| H4 | Zwei Geräte lassen sich per ConnectX-7 zur 405B-Klasse koppeln | Hersteller-Spec, für Phase 3 irrelevant |
| H5 | Die Bandbreite liegt bei rund einem Viertel der 4090 | Hersteller-Spec, durch eigenen Lauf zu ersetzen |
| H6 | `torch` in der von robo-lab genutzten Version gibt es als aarch64+CUDA-Rad | PyTorch-/NVIDIA-Index für `sbsa` prüfen |

Gemessen ist bislang nur das Prompt-Processing der GB10-Klasse (1.723 tok/s gegen
340 tok/s Strix Halo, Fremdmessung) — nichts davon auf unserem Gerät.

## 8a. Was der Knoten NICHT erbt

Die 4090-Box ist Windows 11 mit WSL2 (B11) — daher die dokumentierten Fallen: Quoting
durch cmd→wsl→bash, der Docker-Desktop-Stub ohne Daemon, `vmIdleTimeout=-1` als
Keepalive. Der GX10 läuft nativ unter Linux; **all das entfällt**. An seine Stelle tritt
die Architektur: aarch64 statt x86, also andere Räder (H6) und andere Container-Images.

## 9. Offene Punkte

| #  | Punkt | Wer |
|----|-------|-----|
| O1 | Physischer Standort für den `hosts.yaml`-Eintrag | Owner |
| O2 | arm64-Bestandsaufnahme über die Kandidaten aus §5 | Lotse |
| O3 | Ladelauf-Messung, hebt H1 von Hypothese auf Beleg | Lotse, am Gerät |
| O4 | Kandidatenliste IIL-interner Lasten für C7 verfeinern | Lotse |

Tracking für O2/O3: siehe Auftrags-Issue in §10.

## 10. Nachträge

- 2026-08-29: Konzept angelegt, Owner-Entscheid E1–E3 aufgenommen.
- 2026-08-29: §5b ergänzt (Anwendungsfälle ab Werk, A1–A8). C7 von „ohne Cloud-Abfluss"
  auf „offen" korrigiert — die zugrunde liegende Annahme war ungeprüft und hielt der
  Gegenprobe nicht stand.
