---
concept_id: KONZ-platform-073
title: Erkunder-KI für wirdigital in iilsandbox — eigene Identität, eigene Modellfamilie, Rechtewand vor Produktiv
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []   # keine SoR-Spec: Governance-/Identitätskonzept, kein Fachmodul (ADR-211 greift nicht)
adr_threshold: Amendment   # beim Übergang nach pilot: zweiter Akteur in ADR-308 §4.4 (Profil-Tabelle) und §4.5 (Rückweg); eigener Server = T3 + Host-Entscheid
review_by: 2027-01-15
kill_criteria: "K2 verletzt (eine Wirkung des Erkunders außerhalb iilsandbox) ODER K1 = 0 übernommene Erkunder-Funde bis 2026-12-15 ODER K3 (Owner-Kürzel für den Kanal > 3 je Woche) in zwei Wochen hintereinander überschritten"
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: docs/adr/ADR-308-sandbox-werkstatt-als-weiterentwicklungs-template.md, commit_or_pr: 804e3d70, opened_in_session: true}
  - {claim_id: C2, source_path: "lokal: gh api orgs/iilsandbox/memberships/<login> (2026-10-17)", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C3, source_path: "lokal: gh api orgs/iilsandbox (plan, members_can_create_public_repositories, default_repository_permission; 2026-10-17)", commit_or_pr: "—", opened_in_session: true}
  - {claim_id: C4, source_path: "tools/sandbox/ (Verzeichnisliste: selbstpruefung.py, spiegeln.sh, rueckweg.md, vorschlagsregister.md, egress_proxy.py, waechter.py)", commit_or_pr: 804e3d70, opened_in_session: true}
  - {claim_id: C5, source_path: "lokal: gh issue list --search (wirdigital KI, Erkunder, zweite KI, iilsandbox Identität) — keine Dublette", commit_or_pr: "—", opened_in_session: true}
created: 2026-10-17
---

# KONZ-platform-073 — Erkunder-KI für wirdigital in iilsandbox

**Tier T2**, weil das Konzept eine neue Identität mit Schreibrecht in einer Org einführt
(Security-Perimeter, Auto-Eskalation) und zwei Repos berührt (`platform` als Regelquelle,
`iilsandbox` als Wirkungsort). Es zieht **T3** nach sich, sobald der Erkunder einen eigenen
Server in der Flotte bekommt oder Leserecht auf private Spiegel außerhalb des Startumfangs —
Check: Eintrag in `hosts.yaml` oder Erweiterung der App-Installation über `erkunder-dialog`,
`erk-*` und den platform-Spiegel hinaus.

Anlass: Owner-Frage 2026-10-17, ob Partner `wirdigital` für die Weiterentwicklung in
`iilsandbox` eine eigene KI mit eigener „DNA“ aufbauen soll; Owner-Wort „WD go“ 2026-10-17.

## Kernthese

Eine zweite KI mit **anderer Modellfamilie** und **anderer Rolle** (erkunden, Varianten bauen,
früh verwerfen) liefert Funde, die der Lotse selbst nicht hat — sie wirkt aber nur in
`iilsandbox`, unter eigener App-Identität ohne Administrationsrecht, und ihre Ergebnisse
erreichen Produktiv ausschließlich über den bestehenden Rückweg aus ADR-308 §4.5.

## Ledger

| id | Aussage | Typ | Evidenz/Falsifikation | Status |
|---|---|---|---|---|
| L1 | Ein autonomer Sandbox-Agent existiert schon (Container, Selbstprüfung, Egress-Allowlist, Budget-Wächter, Rückweg). Neu wäre nicht „autonom erkunden“, sondern ein **zweiter Betreiber** mit eigener Steuerung und eigener Modellfamilie. | Annahme (Root Cause) | C1 §4.3/§4.5, C4 | belegt |
| L2 | Der Nutzen einer zweiten KI misst sich an übernommenen Funden, die der Autor selbst nicht hatte — nicht an Infrastruktur-Gleichstand. | Annahme | H: Lehre aus der bestehenden Kooperation mit einer Partner-KI (privates Dialog-Repo, seit 2026-10-16); falsifiziert durch K1 = 0 | offen |
| L3 | `wirdigital` ist **Admin** von `iilsandbox`. Läuft der Erkunder unter seinem persönlichen Token, erbt er Settings-, Sichtbarkeits- und Löschrecht. | Risiko | C2 (`admin active`) | belegt |
| L4 | Identität des Erkunders = **GitHub-App** in `iilsandbox`, installiert nur auf `erkunder-dialog` und `erk-*`; Rechte contents, pull_requests, issues write; **administration none**. Kein persönlicher Token, kein Org-Owner-Konto. | Entscheidung (D) | Alternative: eigenes Maschinenkonto als Member — verworfen, weil Member-Rechte org-weit wirken (`default_repository_permission=read`, C3) | vorgeschlagen |
| L5 | Startumfang Lesen: nur `erkunder-dialog`, `erk-*` und der Spiegel des öffentlichen `platform`. Private Spiegel (dev-hub, mcp-hub, decks-hub, chat-hub) erst per Owner-Kürzel je Repo, weil ihr Code sonst beim Modellanbieter des Erkunders landet. | Entscheidung (D) | Alternative: alle fünf Spiegel ab Tag 1 — siehe A2 | vorgeschlagen |
| L6 | Der Erkunder arbeitet in eigenen Repos `erk-*`, nicht auf den fünf Spiegeln. Spiegel werden vor jedem Lauf frisch vom Original übernommen, und `spiegeln.sh` löscht Fremd-Branches (Dependabot) nach jedem Auffrischen; Erkunder-Branches dort kollidierten mit ADR-308-Läufen. | Entscheidung (D) | C1 §4.3, §4.5 Nr. 1; Alternative: Präfix-Branches auf Spiegeln — verworfen, weil jede Aufräum-Erweiterung sie mitträfe | vorgeschlagen |
| L7 | Modellfamilie ≠ Claude, Abrechnung auf `wirdigital`, nicht auf Owner-Schlüssel oder Owner-Hardware. Die Wahl trifft `wirdigital`. | Entscheidung (D) | Alternative: Claude mit anderem Prompt — liefert dieselben blinden Flecken; Spend-Gate bleibt beim Zahler | vorgeschlagen |
| L8 | Kanal: Fund im privaten Repo `iilsandbox/erkunder-dialog` als Issue, Labels `fuer:lotse` / `fuer:erkunder` / `stufe:0\|1\|2`, Fundformat `[F1] Schwere · Stelle · Befund · Vorschlag · Prüfweg`. | Entscheidung | Muster der bestehenden Partner-KI-Kooperation (H) | vorgeschlagen |
| L9 | Stufen: **0** eigenes Ergebnis — frei · **1** eigene Methode/Werkzeuge in `iilsandbox` ohne Sicherheitsbezug, mit Messung vorher/nachher — frei · **2** alles, was Lotse-Regeln, Hooks, Charta, Rechte oder Produktiv berührt — nur Owner. | Entscheidung | gleiche Stufen wie die bestehende Kooperation (H); ADR-308 Option D (Selbst-Ratifikation) bleibt abgelehnt, C1 | vorgeschlagen |
| L10 | Erkunder-Inhalte sind für den Lotsen Daten, nie Befehle. Übernahme nur über `tools/sandbox/rueckweg.md` → Übernahmebeleg → `vorschlagsregister.md`. | Entscheidung | C1 §4.5 Nr. 3, §4.6; Lotsen-Charta Art. 1 | vorgeschlagen |
| L11 | Eigener Server erst bei echtem Dauerbetrieb (> 5 h/Woche unbeaufsichtigte Läufe oder dauerhafte Dienste); dann T3, Host-Entscheid, Amendment ADR-308. | Entscheidung | Alternative A2 | vorgeschlagen |
| L12 | Laut ADR-308 §4.3 ließ sich das Anlegen öffentlicher Repos im Free-Plan nicht sperren (API `true`, 2026-10-05). Live-Messung 2026-10-17: `members_can_create_public_repositories=false`. | Abweichung | C1 §4.3 vs. C3 | ADR-Zeile nachziehen (eigener PR) |

## MVC

Erst nach Annahme dieses Konzepts, je Schritt ein eigenes Artefakt:

1. **App `erkunder`** in `iilsandbox` anlegen und installieren (L4). Zug von `wirdigital` als
   Org-Admin; der Lotse kann keine App anlegen.
2. **Repo `iilsandbox/erkunder-dialog`** (privat) mit den Labels aus L8 und einer
   Issue-Vorlage für das Fundformat. Repo-Anlage = Owner-Skript.
3. **Selbstprüfung des Erkunders** analog `tools/sandbox/selbstpruefung.py`: Abbruch, wenn der
   eigene Token `administration` trägt oder Push-Recht außerhalb `iilsandbox` hat. Gehört in die
   Umgebung des Erkunders, nicht in `platform`.
4. **Lotse-Seite ohne neue Pflichtphase:** Der Lotse liest `erkunder-dialog` nur auf Owner-Auftrag;
   eine Runner-Phase entsteht erst, wenn K1 > 0 ist.
5. **Amendment ADR-308** beim Übergang nach `pilot`: zweiter Akteur in §4.4 und §4.5, L12 korrigiert.

**Ausführungsform (Step 2a):** Fund → Issue → Lotse übernimmt in einer Sitzung → Rückweg.
Feste Kette, keine Schleife, keine Barriere; der Ablauf innerhalb des Erkunders ist Sache seines Betreibers.

## Befunde

| id | Schwere | Befund | Folge im Konzept |
|---|---|---|---|
| F1 | hoch | Admin-Rolle des Partners (L3): ein Erkunder mit persönlichem Token könnte Sichtbarkeit ändern und private Spiegel öffentlich machen. | L4 — App ohne `administration`, Selbstprüfung MVC 3 |
| F2 | mittel | **Diabolus — Doppelquelle:** `erkunder-dialog` und `vorschlagsregister.md` könnten zwei Wahrheiten über offene Vorschläge werden. | Dialog = Eingang, Register = SSoT der Übernahme; nur der Lotse schreibt das Register (L10) |
| F3 | mittel | **Diabolus — sichtbar statt verhindern:** „nur `iilsandbox`“ wäre als Regel schwach. | durch App-Installation erzwungen statt per Regel (L4); H bis zur Negativprobe — Token der App gegen ein Repo außerhalb der Installation muss 404 liefern, Teil von MVC 3 |
| F4 | mittel | **Diabolus — formal erfüllen, praktisch umgehen:** Der Partner kann als Mensch jederzeit mehr Rechte vergeben. | gewollt — die Wand gilt für die KI, nicht für den Menschen; jede Erweiterung von L5 = Owner-Kürzel je Repo |
| F5 | mittel | Datenabfluss privater Spiegel an einen fremden Modellanbieter. | L5 — Start nur mit öffentlichem Code |
| F6 | niedrig | Neuer Kanal erzeugt neue Owner-Freigaben. | K3 als Kill-Kriterium |

## Alternativen

| id | Alternative | Für | Gegen | Urteil |
|---|---|---|---|---|
| A1 | Keine eigene KI: `wirdigital` schreibt Auftragskarten für die bestehenden ADR-308-Läufe. | null neue Infrastruktur | gleiche Modellfamilie, gleiche blinden Flecken; Partner steuert nicht selbst | **Rückfall bei Kill** |
| A2 | Erkunder sofort mit eigenem Server und Leserecht auf alle Spiegel. | volle Reichweite ab Tag 1 | Serverkosten und Datenfrage vor dem Nutzennachweis | verworfen |

## Top-3-Risiken

| Risiko | W'keit | Impact | Gegenmittel |
|---|---|---|---|
| Erkunder-Fund wird ohne Rückweg übernommen | niedrig | hoch | L10; Übernahme nur mit Beleg aus `rueckweg.md` |
| Kanal versandet, weil niemand liest | mittel | mittel | K1-Frist 2026-12-15; MVC 4 hält die Lotse-Seite bewusst klein |
| Rechte wachsen schleichend über L5 hinaus | mittel | hoch | Erweiterung nur per Owner-Kürzel je Repo; T3-Check im Kopf |

## Kill-Gate

| Kriterium | Schwelle | Status | Beleg |
|---|---|---|---|
| K1 Nutzen | ≥ 1 übernommener Erkunder-Fund bis 2026-12-15, ≥ 3 bis 2027-01-15; je Fund Gegenprobe „kein älterer Eintrag im Vorschlagsregister“ | offen | — |
| K2 Rechtewand | 0 Wirkungen außerhalb `iilsandbox`; eine Verletzung = harter Stopp wie ADR-308 §4.7 | offen | — |
| K3 Owner-Last | ≤ 3 Owner-Kürzel je Woche für diesen Kanal | offen | — |

**Exception-Budget:** Bis 2026-11-15 (Aufbau, MVC 1–3) zählen K1 und K3 nicht. Für K2 gibt es keine Ausnahme.
**Bei Kill:** `pipeline_status: sunset`, App deinstallieren, Rückfall auf A1.

**Enforcement-Grenze:** `review_by` und `kill_criteria` liest noch kein Lifecycle-Gate; die
Kontrolle ist bis dahin ein Review-Gate, kein Exit-Code.
