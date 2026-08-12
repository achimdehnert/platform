---
concept_id: KONZ-platform-044
title: "iil-formatsatz — ein Satz-Motor als Paket, Design bleibt in design-hub"
pipeline_status: idea
tier: T3
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: "org-weiter ADR (ab Migrationsschritt 4 — neue Dependency + Cross-Repo)"
review_by: 2026-11-12
kill_criteria: >
  Schritt 4 (create-buch in writing-hub gegen das Paket) liefert bis 2026-10-15
  kein PDF, das seitengleich mit dem lokalen Lauf ist — oder die Messreihe
  390/160/198 verschiebt sich in irgendeinem Schritt ohne benannte Ursache.
  Dann: Paketierung abbrechen, zwei Motoren bewusst nebeneinander führen,
  gemeinsames Wissen bleibt Runbook.
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "platform/tools/print_agent/print_agent.py", commit_or_pr: "main@2026-08-12", opened_in_session: true}
  - {claim_id: C2, source_path: "platform/tools/print_agent/profile_policy.py", commit_or_pr: "main@2026-08-12", opened_in_session: true}
  - {claim_id: C3, source_path: "design-hub/profiles/_SCHEMA.md", commit_or_pr: "#42", opened_in_session: true}
  - {claim_id: C4, source_path: "design-hub/profiles/iil-extern.yaml", commit_or_pr: "main@2026-08-12", opened_in_session: true}
  - {claim_id: C5, source_path: "manuskripte/tools/bookkit/pdf.py", commit_or_pr: "#4", opened_in_session: true}
  - {claim_id: C6, source_path: "manuskripte/tools/bookkit/css/buch_a5.css", commit_or_pr: "#4", opened_in_session: true}
  - {claim_id: C7, source_path: "writing-hub/apps/projects/views_export.py", commit_or_pr: "main@2026-08-12", opened_in_session: true}
  - {claim_id: C8, source_path: "writing-hub/Dockerfile", commit_or_pr: "main@2026-08-12", opened_in_session: true}
  - {claim_id: C9, source_path: "aifw/pyproject.toml", commit_or_pr: "v0.11.6", opened_in_session: true}
  - {claim_id: C10, source_path: "iil-doc-templates/pyproject.toml", commit_or_pr: "v0.3.1", opened_in_session: true}
  - {claim_id: C11, source_path: "platform/docs/adr/ADR-273-writing-hub-composition-ssot.md", commit_or_pr: "main@2026-08-12", opened_in_session: true}
  - {claim_id: C12, source_path: "platform/pulls/1923", commit_or_pr: "#1923", opened_in_session: true}
  - {claim_id: C13, source_path: "~/.claude/policies/adr-threshold.md", commit_or_pr: "n/a", opened_in_session: true}
  - {claim_id: C14, source_path: "~/.claude/commands/create-pdf.md", commit_or_pr: "n/a", opened_in_session: true}
created: 2026-08-12
---

# KONZ-platform-044: iil-formatsatz — ein Satz-Motor als Paket, Design bleibt in design-hub

**Tier: T3.** Auto-Eskalation greift mehrfach: Cross-Repo (heute 7 Konsumenten von
`print_agent`, C1/C14), neue Dependency, neue Boundary, Verschiebung einer SSoT
(Rendering), und der Lizenz-Perimeter von design-hub ist berührt (C3). Keine dieser
Eigenschaften ist wegdiskutierbar, auch wenn der erste Schritt klein ist.

**Methodenhinweis:** Der T3-Fan-out mit drei getrennten Agenten wurde **nicht**
gefahren (Session-Vorgabe: keine Subagenten ohne Auftrag). Steelman, Advocatus
Diabolus und Maintainer-2028 stehen deshalb als getrennte Abschnitte, von derselben
Instanz geschrieben — schwächer als drei unabhängige Sichten, und so zu lesen.

---

## 1 Executive Summary

In dieser Organisation setzen heute **zwei** Motoren PDFs, beide mit WeasyPrint:
`platform/tools/print_agent` für Dokumente über Vorgänge (1.711 Zeilen Python, 7
Konsumenten, C1) und `manuskripte/tools/bookkit` für Werke (795 Zeilen inkl. CSS,
C5/C6). Ein dritter, schwächerer A5-Export lebt inline in einer Django-View von
writing-hub (C7). Keiner der vier adoptions-ADR-gestützten `iil-*`-Pakete deckt
Rendering ab — `iil-doc-templates` (v0.3.1) enthält nachweislich kein WeasyPrint
(C10). Die Fähigkeit „aus Markdown plus Design wird ein PDF" hat also **keinen
Eigentümer**, obwohl sie dreimal implementiert ist.

Vorschlag: ein Paket `iil-formatsatz` als **Motor**, mit `[dokument]`- und
`[buch]`-Extras; Design bleibt vollständig in design-hub und wird dem Motor als
Profil **übergeben**, nie gebündelt. Konsumenten sind `create-pdf` (bestehend) und
ein neues `create-buch` in writing-hub. Die Migration läuft in sechs Schritten,
von denen die ersten beiden bereits gebaut und gemessen sind.

**Was dieses Konzept nicht vorschlägt:** keinen PyPI-Publish (Schritt 6, eigener
Beschluss), keine Verschiebung von Inhalten zwischen Repos, keine Änderung an
ADR-274-Zuständigkeiten.

---

## 2 Scope & Evidenzbasis

**In Scope:** Zuschnitt des Pakets, Verhältnis zu design-hub, Migrationsreihenfolge,
Kill-Gate. **Out of Scope:** die Frage, wo Werke leben (das beantwortet ADR-273, C11);
Lektorat, Cover, Vertrieb; Publish-Entscheidung.

Evidenzklassen im Text: `E2` = in dieser Session geöffneter Code, `E3` = geöffneter
PR/Issue, `E1` = ADR/Policy, `H` = Hypothese. Das Manifest im Frontmatter listet jede
Datei, auf die sich eine `E2/E3`-Aussage stützt.

Nicht verifiziert: ob die 7 Repos aus der `print_agent`-Trefferliste alle **aktiv**
rendern oder ihn nur erwähnen (die Zählung war ein Dateiname-Treffer, kein Lauf) —
`H`. Billigster Check: `grep -rn "print_agent" <repo>/Makefile docs/` je Repo, oder
die `pdfs/`-Verzeichnisse auf Änderungsdatum ansehen.

---

## 3 Infrastruktur-Fit

| Baustein | Stand | Beleg |
|---|---|---|
| `print_agent` | Motor + Design-Brücke, 1.711 Z., zieht `litellm` und ruft `npx`/mmdc für Mermaid | C1 `E2` |
| `profile_policy` | bewusst importfrei, damit im CI prüfbar — Vorbild für den Kern-Zuschnitt | C2 `E2` |
| design-hub | erklärt sich zur SSoT für Design/Profile/Templates, 6 Profile, `allowed_assets`-Hard-Block | C3/C4 `E2` |
| `bookkit` | zweiter Motor, Werk-Semantik, seit #4 profilgetrieben | C5/C6 `E3` |
| writing-hub | dritter A5-Export inline in der View, ohne Impressum/Recto/Folio-Neustart | C7 `E2` |
| `iil-*`-Familie | vier Pakete, je mit Adoptions-ADR, Konsum „über dokumentierte öffentliche Oberfläche" | C11 `E1` |
| `iil-doc-templates` | Templates + Prefill, **kein** Rendering | C10 `E2` |
| platform#1923 | Buchsatz aus `print_agent` zurückgenommen, weil Buchproduktion woanders lebt | C12 `E3` |

**Fit-Urteil:** Ein `iil-formatsatz` folgt einem etablierten Muster (fünftes
`iil-*`-Paket, Konsum über öffentliche Oberfläche, Adoptions-ADR). Es füllt eine
belegte Lücke statt eine dritte Wahrheit zu schaffen — genau deshalb ist es
verteidigbar, obwohl #1923 einen oberflächlich ähnlichen Versuch zurückgenommen hat.
Der Unterschied: #1922 legte ein **Design** ins Werkzeug; hier zieht ein **Motor**
aus, und das Design bleibt, wo es hingehört.

---

## 4 Steelman — der stärkste Fall für das Paket

Dreimal dieselbe Mechanik zu pflegen ist nicht nur Duplikat, sondern **divergentes**
Duplikat: die vier gemessenen WeasyPrint-Fallen (`vh` löst nicht auf, Type1 nicht
einbettbar, `hyphens` ohne `lang` wirkungslos, Seitenzählung nicht neu startbar)
sind heute genau **einmal** gelöst, in `bookkit`. Der Export in writing-hub kennt
keine davon (C7) und liefert entsprechend ein schwächeres Ergebnis, ohne dass das
irgendwo auffällt — es gibt keinen Ort, an dem der Unterschied sichtbar würde.

Ein Motor mit einer öffentlichen Oberfläche macht diese Unterschiede zu einer
Versionsfrage statt zu einer Zufallsfrage. Er gibt dem Schrift-Wächter (#4) einen
Platz, an dem er **alle** Konsumenten schützt statt nur einen. Und er erlaubt, das
Wissen einmal zu testen: `profile_policy` zeigt im selben Repo, dass ein
importfreier Kern im CI prüfbar ist (C2), während der heutige Buchsatz nur durch
manuelles Hinsehen abgesichert wird.

Der Zeitpunkt ist außerdem günstiger als je zuvor: Schritt 1 und 2 sind gebaut, ohne
ein fremdes Repo zu brechen, und die Messreihe 390/160/198 existiert als
Regressionsprobe. Wer jetzt nicht schneidet, schneidet später gegen mehr Code.

---

## 5 Konzeptdefinition

### 5.1 Drei Schichten, klare Eigentümer

| Schicht | Frage | Ort |
|---|---|---|
| Design | Wie soll es aussehen? | **design-hub** — Profile + Assets, `allowed_assets` als Sperre |
| Motor | Wie wird daraus ein PDF? | **`iil-formatsatz`** — Kern + Extras |
| Konsument | Was wird gesetzt? | `create-pdf` (7 Repos), `create-buch` (writing-hub) |

### 5.2 Paketzuschnitt

```
iil-formatsatz            Kern: Profil einlesen, CSS bauen, HTML→PDF,
                          Schrift-Wächter, die vier WeasyPrint-Fallen
iil-formatsatz[dokument]  Mermaid/Gantt/Flow-Parser, LLM-Anreicherung
                          (litellm), Meta-Tabellen, llm_gate
iil-formatsatz[buch]      Kapitelmodell, Quell-Konventionen, Titelei,
                          Verzeichnis mit Seitenzahlen, Vorspann, EPUB
```

Der Kern hängt an WeasyPrint, `markdown`, `pypdf`, `PyYAML` — nicht an `litellm`,
nicht an Node. Das ist der Unterschied zu `aifw`, wo `litellm` **Core** ist, weil es
dort der Zweck ist (C9). Von `aifw` übernommen wird dagegen das Extra als
**Absichtsmarker**: dessen `nl2sql`-Extra installiert null zusätzliche Pakete und
schaltet nur eine Fähigkeit frei (C9) — dasselbe Muster trägt `[buch]`, falls es
keine eigenen Abhängigkeiten braucht.

### 5.3 Zwei harte Invarianten

**I-1 — Profile werden übergeben, nie gebündelt.** design-hub enthält lizenzierte
DB-Assets mit Nutzungsbeschränkung (C3). Ein Paket, das Profile mitliefert, wäre
spätestens beim Publish eine Lizenzverletzung. Der Motor nimmt ein Profil-Dict oder
einen Pfad entgegen und prüft `allowed_assets`, bevor er einen Asset-Pfad auflöst —
so wie `print_agent` es heute tut (C1).

**I-2 — Kein stiller Rückfall.** Fehlt ein Profil oder eine Schrift, bricht der
Motor ab. Das ist bereits gebaut und mit Positivkontrolle belegt (#4): erfundene
Schriftfamilie → Abbruch, fehlendes Profil → Abbruch mit Handlungsanweisung. Der
Grund ist die teuerste Fehlerklasse dieser Kette — gebaut, grün, wirkungslos.

### 5.4 Ausführungsform (Step 2a)

Frage 1 der Filterkette beantwortet den Rest: Der Satz eines Buchs ist **ein
Aufruf** mit deterministischen Teilschritten, kein mehrschrittiger Agentenablauf.
Kein Graph, kein Router, keine Schleife — und damit auch kein Abbruchkriterium
nötig. Die Migration selbst ist eine **Kette** mit fest stehender Reihenfolge
(Schritte 1–6), weil jeder Schritt den vorigen als Beweis braucht.

---

## 6 Adversariale Analyse

### 6.1 Advocatus Diabolus

**AD-1 — Der gemeinsame Kern ist zu klein, um ein Paket zu rechtfertigen.** Von
1.711 Zeilen `print_agent` sind die Masse Mermaid-, Gantt- und LLM-Code; von 795
Zeilen `bookkit` die Masse Werk-Semantik. Übrig bleibt ein schmaler Streifen. Ein
Paket für ~100 Zeilen kostet Versionierung, Release-Disziplin und einen zweiten Ort
zum Nachsehen. *Antwort:* trifft für den Kern **allein** zu — aber der Nutzen liegt
nicht in geteilten Zeilen, sondern darin, dass die **Extras** den Motor gemeinsam
haben und der Schrift-Wächter alle schützt. Bleibt der Kern nach Schritt 3 unter
~150 Zeilen und hat `[dokument]` keinen Nutzer, ist Alternative B (nur Runbook) die
ehrlichere Antwort. Das steht als Kill-Kriterium in §13.

**AD-2 — „SSoT für Rendering" wird behauptet, nicht erzwungen.** Nichts hindert
writing-hub daran, seinen View-Export (C7) zu behalten; dann gibt es weiterhin zwei
Wege, nur mit einem Paket mehr. *Antwort:* stimmt. Deshalb ist Schritt 4 nicht
„Paket bereitstellen", sondern „`create-buch` liefert seitengleich" — und Schritt 4
enthält die Ablösung oder ausdrückliche Kennzeichnung des Alt-Exports als
Arbeits-Export. Ohne diesen Teil ist der Schritt nicht erledigt.

**AD-3 — Das `kind: werk`-Feld erzeugt eine zweite Profilwelt in design-hub.**
Dokument-Profile und Werk-Profile teilen ein Schema, aber kaum Felder; das lädt zu
divergierenden Pflichtfeldern und einem faktischen Schema-Fork ein. *Antwort:*
Risiko anerkannt, siehe RISK-3. Gegenmaßnahme: `kind` bleibt ein **Feld**, keine
zweite Datei-Konvention, und der Default `dokument` hält alle sechs bestehenden
Profile unverändert gültig (#42).

**AD-4 — Systemabhängigkeiten kann ein Extra nicht ausdrücken.** `[dokument]`
braucht Node und Puppeteer, der Kern braucht Pango-Bibliotheken und Schriften — nichts
davon installiert `pip`. Ein Konsument kann formal korrekt installieren und
trotzdem nicht rendern. *Antwort:* das ist der Grund für den Schrift-Wächter und für
den Kopplungstest aus writing-hub#547 (`E1`, aus dem dortigen Fehlerbild: Paket in
`requirements.txt` ⇒ Laufzeitbibliotheken im Dockerfile). Der Test gehört ins Paket,
nicht in jedes Konsumenten-Repo.

**AD-5 — #1923 hat genau das schon einmal zurückgenommen.** Wer eine Woche später
dasselbe Thema erneut aufmacht, hat entweder damals oder heute falsch entschieden.
*Antwort:* #1923 nahm ein **Design** aus dem Werkzeug (C12). Hier zieht ein Motor
aus und das Design bleibt in design-hub. Die Unterscheidung ist prüfbar: enthielte
`iil-formatsatz` eine einzige Farb- oder Schriftfestlegung, wäre AD-5 berechtigt.

### 6.2 Maintainer 2028

Ich erbe ein Paket mit zwei Extras, dessen `[buch]`-Seite genau einen Nutzer hat.
Ich sehe drei Repos, die es installieren, und eines, das noch seinen alten
View-Export fährt, weil Schritt 4 „im Prinzip fertig" war. Die Profile liegen in
einem vierten Repo, das ich nicht ohne Weiteres auschecken kann, weil dort
lizenzierte Assets liegen — und mein CI-Runner scheitert an genau der Stelle mit
einer Fehlermeldung, die ich zuerst für einen Netzwerkfehler halte.

Was mir hilft: dass der Abbruch bei fehlendem Profil den Pfad und die Umgebungsvariable
nennt (gebaut, #4). Was mir fehlt: eine Antwort auf „wie komme ich im CI an die
Profile?". Das ist **offen** und gehört in Schritt 3 entschieden, nicht in Schritt 5
entdeckt (REC-4).

---

## 7 Deep-Dive: was wirklich geteilt ist

Gemessen, nicht geschätzt (C1/C5/C6):

| Bestandteil | print_agent | bookkit | teilbar? |
|---|---|---|---|
| Profil laden + `allowed_assets` prüfen | ja | seit #4 | **ja** |
| CSS aus Werten zusammensetzen | ja | ja | **ja** |
| HTML→PDF, `lang`-Attribut, Silbentrennung | ja | ja | **ja** |
| Schrift-Wächter | nein | seit #4 | **ja** |
| Mehrdokument-Rendern + `pypdf`-Zusammenfügen | nein | ja | ja, `[buch]` |
| Seitenzahlen aus Ankern ins Verzeichnis | nein | ja | ja, `[buch]` |
| Mermaid/Gantt/Flow, LLM, Meta-Tabellen | ja | nein | nein, `[dokument]` |
| Kapitel, Titelei, EPUB | nein | ja | nein, `[buch]` |

Der **Kern** ist damit klein, aber nicht leer — und er enthält ausgerechnet die
Stellen, an denen bisher jeder Konsument eigene Fehler gemacht hat.

---

## 8 Alternativen

| # | Alternative | Wofür sie spricht | Warum nicht gewählt |
|---|---|---|---|
| A | Nichts tun, zwei Motoren bewusst führen | null Kosten, null Risiko | der dritte Export (C7) divergiert weiter unbemerkt; der Schrift-Wächter schützt nur ein Repo |
| B | Nur ein gemeinsames Runbook, kein Code | billig, sofort, kein Publish | Wissen ohne Enforcement — genau die Klasse Empfehlung, die dieser Skill verbietet |
| C | Ein flaches Paket ohne Extras | einfachste Struktur | `create-buch` erbte `litellm` + Node-Toolchain (AD-4); im schlanken App-Image untragbar |
| D | **Kern + Extras** (gewählt) | Konsumenten zahlen nur, was sie nutzen | mehr Struktur als C, Extras-Grenze muss gepflegt werden |
| E | Render-Dienst statt Bibliothek | keine Systemabhängigkeiten beim Konsumenten | neuer Betriebsgegenstand, Netzwerkpfad, Auth — unverhältnismäßig für zwei Konsumenten |

---

## 9 Out-of-the-Box

**OOTB-1 — Das Profil als Ausgabevertrag, nicht nur als Aussehen.** Wenn `satz`
Seitenformat und Ränder trägt, könnte es auch die **Prüfkriterien** tragen
(erwartete Seitenzahl-Toleranz, Pflicht-Elemente wie Impressum). Dann ist die
Regressionsprobe Teil des Designs statt Teil des Gedächtnisses.

**OOTB-2 — Typst statt WeasyPrint für den Buchpfad.** WeasyPrint kostet vier
gemessene Umwege (Seitenzählung, `vh`, Type1, `lang`). Ein Satzsystem, das
Buchsatz nativ kann, würde `[buch]` verkleinern statt vergrößern. Gegen sofort:
das wirft die gemessene Regressionsprobe weg. Als Frage für Schritt 5 vormerken.

**OOTB-3 — Der Alt-Export als Kanarienvogel.** Statt writing-hubs View-Export zu
löschen, ihn behalten und in CI **gegen** das Paket rendern: weicht die Seitenzahl
ab, ist entweder das Paket kaputt oder der Alt-Export überholt. Kostet wenig und
beantwortet AD-2 messbar.

---

## 10 Befunde

| # | Befund | Klasse | Konsequenz |
|---|---|---|---|
| B1 | Drei Implementierungen derselben Fähigkeit, keine besitzt sie | `E2` C1/C5/C7 | Lücke ist real, nicht konstruiert |
| B2 | Kein `iil-*`-Paket deckt Rendering ab | `E2` C10 | kein Overlap mit ADR-274 |
| B3 | writing-hubs Export kennt keine der vier Fallen | `E2` C7 | schwächeres Ergebnis, unbemerkt |
| B4 | Image hat nur `fonts-dejavu-core` | `E2` C8 | Schritt 4 braucht Schriftpaket |
| B5 | design-hub trägt lizenzierte Assets | `E2` C3 | Profile nie bündeln (I-1) |
| B6 | `aifw` nutzt Extras als Absichtsmarker | `E2` C9 | Muster für `[buch]` |
| B7 | 7 Repos nennen `print_agent` — aktiv? ungeprüft | `H` | vor Schritt 5 zählen |
| B8 | Messreihe 390/160/198 nach zwei Umbauten stabil | `E3` #4 | Regressionsprobe trägt |

---

## 11 Top-5-Risiken

| # | Risiko | Wirkung | Gegenmaßnahme |
|---|---|---|---|
| R1 | Schritt 4 bleibt „im Prinzip fertig", Alt-Export lebt weiter | zwei Wege plus ein Paket | Schritt 4 gilt erst mit abgelöstem oder gekennzeichnetem Alt-Export (AD-2) |
| R2 | CI der Konsumenten kommt nicht an die Profile | Build rot oder stiller Umweg | in Schritt 3 entscheiden (REC-4), nicht in Schritt 5 entdecken |
| R3 | `kind: werk` driftet zum Schema-Fork | zwei Profilwelten in einem Repo | `kind` bleibt Feld, Default `dokument`, ein Schema-Dokument |
| R4 | Systemabhängigkeiten unsichtbar | „installiert, rendert nicht" | Kopplungstest im Paket + Schrift-Wächter |
| R5 | Migration bleibt nach Schritt 3 stehen | Paket ohne Nutzen, Wartungslast | Kill-Gate §13, Datum gesetzt |

---

## 12 Empfehlungen

| # | Empfehlung | Wo | Prüfbar an |
|---|---|---|---|
| REC-1 | design-hub#42 und manuskripte#4 in dieser Reihenfolge mergen | beide Repos | Bau danach: 390/160/198 |
| REC-2 | Kern in `bookkit` als eigenes Modul mit expliziter Signatur isolieren (Markdown + Profil-Dict → PDF), noch ohne Paket | `manuskripte/tools/bookkit/` | zwei interne Aufrufer nutzen dieselbe Funktion |
| REC-3 | Kopplungstest „Paket in requirements ⇒ Laufzeitbibliothek im Dockerfile" aus writing-hub#547 in den Kern übernehmen | Paket-Tests | Test schlägt fehl, wenn `fonts-urw-base35` im Image fehlt |
| REC-4 | Profil-Zugang für CI entscheiden: Checkout, Submodule oder übergebenes Dict | Schritt 3 | ein CI-Lauf eines Konsumenten ohne lokalen design-hub-Checkout |
| REC-5 | `create-buch` in writing-hub baut Faust 2777 seitengleich (198) zum lokalen Lauf | writing-hub | Seitenzahl + Sichtprüfung eines Kapitel-Aufschlags |
| REC-6 | Erst nach REC-5: Adoptions-ADR analog ADR-169/170/274, dann Schritt 5 | platform | ADR mit Nummer, `print_agent` als `[dokument]` |

---

## 13 Entscheidung, Kill-Gate, 30/60/90

**Zur Entscheidung steht:** Schritte 3–4 freigeben (Kern isolieren, `create-buch`
gegen git-Dependency). Schritte 5–6 (`print_agent`-Migration, PyPI) sind **nicht**
Teil dieser Freigabe und brauchen den Adoptions-ADR aus REC-6.

**Kill-Gate:** Liefert `create-buch` bis **2026-10-15** kein seitengleiches PDF,
oder verschiebt sich die Messreihe 390/160/198 in irgendeinem Schritt ohne benannte
Ursache, wird die Paketierung abgebrochen. Rückbau: `bookkit` bleibt im Repo, das
Profil bleibt in design-hub (es steht für sich), das geteilte Wissen wird Runbook —
Alternative B. Exception-Budget: **eine** Verlängerung um 4 Wochen, spätestens am
2026-10-15 zu ziehen, mit benanntem Grund.

| Kriterium | Status | Beleg |
|---|---|---|
| K1 design-hub#42 + manuskripte#4 gemergt, Messreihe stabil | offen | — |
| K2 Kern isoliert, zwei interne Aufrufer | offen | — |
| K3 Profil-Zugang für CI entschieden (REC-4) | offen | — |
| K4 `create-buch` liefert 198 Seiten wie lokal | offen | — |
| K5 Alt-Export abgelöst oder als Arbeits-Export gekennzeichnet | offen | — |
| K6 Kern nach K2 über ~150 Zeilen (sonst → Alternative B) | offen | — |

**30 Tage:** REC-1, REC-2, REC-4 entschieden. **60 Tage:** REC-3, REC-5 —
`create-buch` läuft gegen git-Dependency, nicht gegen PyPI. **90 Tage:**
Entscheidung über REC-6; bei Nein endet das Konzept mit `sunset` und einem Satz
Begründung, nicht mit Stillstand.
