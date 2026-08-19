---
concept_id: KONZ-platform-046
title: Wort, Bild und Ton aus einer Wurzel — den Box-Betrieb deklarieren statt finden
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []          # keine Klickdummy-Spec; System of Record ist ADR-296
adr_threshold: Amendment (ADR-296 Rev — Box-Layout und Konfig-Hoheit)
review_by: 2026-09-30
kill_criteria: >-
  Wenn die Kette erzeugen → schleusen → anwenden → prüfen für die erste Lane
  (sprache) nicht ohne einen Datei-Handgriff auf der Box durchläuft, ist die
  Annahme "Repo ist Quelle" für diese Box falsch. Dann Rückfall auf Alternative
  A1 (nur aufräumen, Konfig bleibt auf der Box). Frist: 2026-09-15.
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: music-lab/box-setup/box-6-fernbedienung.ps1, commit_or_pr: 93c0a09, opened_in_session: true}
  - {claim_id: C2, source_path: music-lab/box-setup/pfad_budget.py, commit_or_pr: 93c0a09, opened_in_session: true}
  - {claim_id: C3, source_path: music-lab/box-setup/PFAD-BUDGET.txt, commit_or_pr: 93c0a09, opened_in_session: true}
  - {claim_id: C4, source_path: music-lab/box-setup/box-6-konfig.beispiel.json, commit_or_pr: 93c0a09, opened_in_session: true}
  - {claim_id: C5, source_path: music-lab/box-setup/UMZUG-D.md, commit_or_pr: 93c0a09, opened_in_session: true}
  - {claim_id: C6, source_path: music-lab/box-setup/sprache.ps1, commit_or_pr: 93c0a09, opened_in_session: true}
  - {claim_id: C7, source_path: music-lab/scripts/box/README.md, commit_or_pr: 93c0a09, opened_in_session: true}
  - {claim_id: C8, source_path: platform/docs/runbooks/box-schleuse.md, commit_or_pr: fc80c75, opened_in_session: true}
  - {claim_id: C9, source_path: platform/docs/adr/ADR-296-gpu-box-lease-arbiter-medien-arbeitsflaeche.md, commit_or_pr: fc80c75, opened_in_session: true}
  - {claim_id: C10, source_path: illustration-hub/tools/gpu-melder/gpu_melder.py, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C11, source_path: illustration-hub/scripts/lora-nach-prod.sh, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C12, source_path: music-lab/AGENT_HANDOVER.md, commit_or_pr: 93c0a09, opened_in_session: true}
created: 2026-08-19
---

# KONZ-platform-046 — Wort, Bild und Ton aus einer Wurzel

**Tier: T3.** Nicht selbst gewählt, sondern durch drei nicht verhandelbare
Auto-Eskalations-Trigger erzwungen: **SSoT-Verschiebung** (die lebende
Konfiguration des Box-Betriebs wandert von der Box ins Repo), **Cross-Repo**
(music-lab, illustration-hub, writing-hub, platform) und **Reversal** (die
heutige Entscheidung „die Box findet ihre Dienste selbst" wird zurückgenommen).
Jeder einzelne davon hätte gereicht.

---

## 1 Executive Summary

Der Owner-Befund lautete: „die ganze Einrichtung ist chaotisch … permanent neue
Verzeichnisse, Skripte." Die naheliegende Erklärung — jemand hat unsauber
gearbeitet — ist **falsch**, und die zweitnächste — derselbe Pfad steht in
mehreren Dateien — ist nur die Wirkung.

Die belegte Ursache liegt eine Ebene tiefer: **die Box erzeugt ihre eigene
Wahrheit.** `box-6-fernbedienung.ps1` sucht beim Einrichten nach dem
Ollama-Tray, nach einer ComfyUI-Exe und nach Verknüpfungen, und schreibt das
**Gefundene** als `box-6-konfig.json` fort (C1, Z. 201–263). Ein gefundener
Zustand kann per Konstruktion nicht falsch sein — deshalb merkt niemand, wenn er
falsch ist. Genau das ist am 2026-08-18 passiert: Die Konfiguration zeigte auf
ein leeres Verzeichnis, und die einzige Rückmeldung war „kein Startbefehl für
'sprache' hinterlegt" (C5, C12).

Daraus folgt die unbequeme Hälfte dieses Konzepts: **`D:\box` allein heilt gar
nichts.** Wer heute alles in ein Verzeichnis räumt und die Findungs-Logik
stehen lässt, bekommt die nächste Lane wieder dort, wo sie zufällig landet — nur
mit aufgeräumter Vergangenheit. Die Wurzel ist die *Folge* einer Deklaration,
nicht ihr Ersatz.

Das Konzept besteht deshalb aus drei Teilen, von denen nur der erste sichtbar
ist:

1. **`lanes.json`** — je Lane ein Datensatz im Repo. Die Wurzel `D:\box` steht
   genau **einmal**.
2. **Erzeugen statt Finden** — ein Generator baut `box-6-konfig.json` aus
   `lanes.json`; die Fernbedienung verliert ihren Suchteil und liest nur noch.
3. **Die Ratsche erweitern** — `pfad_budget.py` liest heute ausschließlich
   `*.ps1` (C2). Ein in eine `.json` verschobener Pfad entkäme dem Budget
   lautlos. Ohne diesen dritten Teil baut man sich die Drift in einem neuen
   Dateiformat nach.

Der Ausrollweg muss **nicht erfunden werden** — er existiert und ist belegt:
Repo → `~/shared` → `box-schleuse.sh` → Prod-Relais → geplante Aufgabe
`Box-Schleuse-Sync` → `D:\schleuse` (C8, C5).

---

## 2 Scope & Evidenzbasis

**Im Umfang:** Verzeichnis-Layout und Betriebs-Konfiguration der 4090-Box für
alle drei Medien-Lanes (Wort/Ollama, Bild/ComfyUI, Ton/ACE-Step + MOSS-TTS),
zuzüglich Stems und Training; die Konfig-Hoheit; die daraus folgenden
Cross-Repo-Änderungen.

**Nicht im Umfang:** Hardware-Kauf (eigene Entscheidungsvorlage,
`box-setup/HARDWARE-2026-08-18.md`), Modellauswahl, Trainingsinhalte, die
Umbenennung illustration-hub → media-hub (ADR-296 Phase 7), und **alle
Fremddaten auf `D:`** — `downloads` (79,9 GB), `Program Files`, `FunFly`,
`LDPlayer`, `dhrw`, `db_backups`, `temp` werden nicht angefasst, auch nicht
versehentlich (C5).

**Evidenzklassen.** `E2` = in dieser Session geöffnete Datei, `E3` = Issue/PR/CI,
`E1` = ADR/Invariant, `H` = Hypothese. Was hier als `E2` steht, steht im
`evidence_manifest` oben.

**Nicht verifiziert, ausdrücklich benannt:**
- Der Ist-Zustand auf `D:` stammt aus **einem** Lauf von `box-inventar.ps1` am
  2026-08-18 (C5). Seitdem ist auf der Box nichts gemessen worden.
- **Wer die Dienste tatsächlich hält**, ist weiterhin ungemessen: der erste
  Inventar-Lauf war durch `$pid` (schreibgeschützte automatische Variable in
  PowerShell) verfälscht; der korrigierte Lauf steht aus (C5).
- Ob die geplante Aufgabe `Box-Schleuse-Sync` heute läuft, ist **nicht** geprüft
  — nur, dass sie eingerichtet ist (C5). Der billigste Check ist eine Datei
  durch die Schleuse zu schicken und drüben nachzusehen.

---

## 3 Infrastruktur-Fit

| Frage | Befund | Klasse |
|---|---|---|
| Governance vorhanden? | ADR-296 (Accepted 2026-08-14) regelt Lease-Arbiter + Medien-Arbeitsfläche; Box-Layout ist dort **nicht** geregelt | E1/C9 |
| Transportweg vorhanden? | ja, `box-schleuse.sh` über Prod-Relais; ausdrücklich **ohne** Ausführungsrecht | E2/C8 |
| Steuerweg vorhanden? | ja, Fernbedienung auf `:8765`, Klient `gpu-fernbedienung.sh` | E2/C7 |
| Gate vorhanden? | ja, `ps1-gate` mit Pfad-Budget als Ratsche — aber nur für `.ps1` | E2/C2 |
| Zielbild vorhanden? | ja, `UMZUG-D.md` mit Reihenfolge und Löschregel | E2/C5 |
| Fremdzugriff dateibasiert? | **nein** — alle Fremdrepos gehen über `IP:Port` | E2/C5 |

**Der wichtigste Fit-Befund ist der letzte.** writing-hub und illustration-hub
sprechen die Box über `10.99.0.2:11434`, `:8000`, `:8010`, `:8765` an. Ein
Verzeichnis-Umzug bricht davon **nichts**, solange die Dienste danach wieder auf
denselben Ports lauschen. Das macht das Vorhaben überhaupt erst tragbar — und es
macht „antwortet der Port wieder?" zum einzig richtigen Abnahmekriterium.

**Die Ausnahme von dieser Regel ist illustration-hub**, und zwar an acht
Stellen in fünf Dateien (E2/C10, C11):

| Pfad | Fundstellen | zieht mit Lane |
|---|---|---|
| `D:\ComfyUI\ComfyUI\ComfyUI\models\loras\` | `docs/runbooks/charakter-lora-trainieren.md`, `scripts/lora-nach-prod.sh` (2×) | bild |
| `D:\ComfyUI\ComfyUI\standalone-env\python.exe` | `tools/gpu-melder/gpu_melder.py`, `tools/gpu-melder/README.md`, `tests/test_gpu_melder.py` | bild |
| `D:\lora\auftrag` | `NEXT.md`, `AGENT_HANDOVER.md` | training |

Beide Gruppen hängen an Lanes, die in diesem Zug **nicht** umziehen. Das ist
kein Zufall, sondern der Grund, warum sie nicht umziehen.

---

## 4 Steelman des Ist-Zustands

Bevor kritisiert wird: **der heutige Zustand ist nicht dumm, er ist gewachsen —
und er hat funktioniert.**

- **Findung statt Deklaration war die richtige erste Entscheidung.** Wer eine
  Windows-Box mit ComfyUI, Ollama und ACE-Step in Betrieb nimmt, kennt die Pfade
  vorher nicht. Ein Skript, das den Ollama-Tray sucht, ist einem Skript
  überlegen, das einen geratenen Pfad hart einträgt — und ein geratener Pfad war
  die einzige Alternative am ersten Tag.
- **Jede Lane an ihrem eigenen Ort ist die schnellste Art, eine Lane in Betrieb
  zu nehmen**, und Inbetriebnahme war bis vor einer Woche die einzige Aufgabe.
- **Die Verschachtelung `D:\ComfyUI\ComfyUI\ComfyUI` ist ein Installer-Artefakt**,
  kein Denkfehler.
- **Der Zustand ist heute vollständig bedienbar**: vier Lanes, ein Steuerweg,
  ein Transportweg, ein Gate gegen Pfad-Dubletten. Das ist mehr Ordnung als die
  meisten gewachsenen Arbeitsplätze haben.

**Der stärkste Einwand gegen dieses ganze Konzept lautet deshalb:** Der
Leidensdruck ist gering, die Lanes laufen, und ein Umzug kostet garantiert
Ausfallzeit gegen einen Nutzen, der sich erst beim *nächsten* Dienst zeigt. Wer
den Umzug ablehnt, hat nicht Unrecht — er wettet nur darauf, dass keine neue
Lane mehr kommt.

Diese Wette ist belegbar verloren: seit dem 2026-08-13 sind **sprache**,
**stems**, **training** und der **GPU-Melder** dazugekommen (C5, C12).

---

## 5 Konzeptdefinition

### 5.1 Kernthese

> Eine Lane ist ein **deklarierter Datensatz im Repo**, kein gefundenes
> Verzeichnis auf der Box. `D:\box` ist die Folge dieser Deklaration.

### 5.2 Die Deklaration — `music-lab/box-setup/lanes.json`

Ein Datensatz je Lane. Bewusst JSON und nicht YAML: PowerShell liest JSON mit
`ConvertFrom-Json` ohne Zusatzmodul, und der bestehende Weg
(`box-6-konfig.json`) ist bereits JSON (C4).

```json
{
  "wurzel": "D:\\box",
  "lanes": {
    "sprache": {
      "port": 8002,
      "besitzer": "music-lab",
      "unterverzeichnis": "dienste\\sprache",
      "programm": "powershell.exe",
      "argumente": "-NoProfile -ExecutionPolicy Bypass -File \"{wurzel}\\skripte\\sprache.ps1\" -Aktion starten",
      "venv": true,
      "autostart": false
    },
    "bild":  { "port": 8000,  "besitzer": "illustration-hub", "...": "..." },
    "text":  { "port": 11434, "besitzer": "writing-hub",      "ausserhalb": "C:\\Users\\achim\\AppData\\Local\\Programs\\Ollama" },
    "melder":{ "port": 8010,  "besitzer": "illustration-hub", "...": "..." }
  }
}
```

Drei Eigenschaften tragen die Idee:

- **`{wurzel}` ist ein Platzhalter, kein Text.** Der Generator setzt ihn ein.
  Damit steht `D:\box` an genau einer Stelle der gesamten Plattform.
- **`besitzer` benennt das Repo**, dem die Lane fachlich gehört. Das ist kein
  Zugriffsrecht, sondern eine Zuständigkeit: wer die Lane ändert, weiß, wen die
  Änderung betrifft. Der GPU-Melder gehört illustration-hub, läuft aber auf der
  Box — heute steht das nirgends.
- **`ausserhalb`** ist der ehrliche Sonderfall: Ollama liegt unter
  `C:\Users\achim\AppData\Local` und zieht **nicht** um (C4). Eine Deklaration,
  die Ausnahmen nicht benennen kann, wird umgangen statt gepflegt.

### 5.3 Erzeugen statt Finden

`box-setup/konfig_bauen.py` (neu) erzeugt `box-6-konfig.json` aus `lanes.json`.
`box-6-fernbedienung.ps1` verliert seinen Findungs-Teil (C1, Z. 201–263) und
**liest** die Konfiguration nur noch (das tut es in Z. 58–60 ohnehin schon).

Damit kehrt sich die Richtung um:

```
heute:  Box findet  →  box-6-konfig.json  →  Fernbedienung
neu:    lanes.json  →  Generator  →  box-6-konfig.json  →  Fernbedienung
```

Der Gewinn ist nicht Ästhetik. Er ist, dass eine falsche Konfiguration künftig
**im Repo sichtbar** ist, bevor sie auf der Box wirkt — und dass sie in CI
prüfbar wird.

### 5.4 Die Ratsche erweitern (sonst trägt nichts davon)

`pfad_budget.py` durchsucht heute `wurzel.rglob("*.ps1")` (C2). Verschiebt man
die Pfade nach `lanes.json`, sinkt das `.ps1`-Budget auf null — das Gate meldet
das korrekt und verlangt, die Zahl zu senken — aber **die neue Fundstelle ist
unbewacht**. Man hätte die Drift nur ins JSON umgezogen.

Deshalb gehört zum Konzept zwingend: Das Gate liest zusätzlich `*.json`, `*.py`,
`*.sh`, `*.md`, und `PFAD-BUDGET.txt` bekommt die Zeile

```
D:\box 1        # nur lanes.json
```

Nach dem Umzug müssen `D:\ace-step`, `D:\ace-step-15`, `D:\moss-tts`,
`D:\msst`, `D:\msst-venv`, `D:\sprache` **aus der Budget-Datei verschwinden** —
das Gate erzwingt das von sich aus, weil ein Budget für einen Pfad, den es
nirgends mehr findet, ein Fehler ist (C2, letzte Schleife).

Heutiger Stand als Ausgangsmessung (C3, Lauf in dieser Session):

| Pfad | `.ps1`-Dateien | Ziel nach Umzug |
|---|---|---|
| `D:\ace-step` | 7 | 0 (Zeile entfällt) |
| `D:\ace-step-15` | 4 | 0 (Zeile entfällt) |
| `D:\box` | 1 | 1 — aber in `lanes.json`, nicht in einer `.ps1` |
| alle übrigen | je 1 | 0 bzw. entfällt |

### 5.5 Ausrollweg — vorhanden, nicht neu

```
Repo (lanes.json)
  └─ konfig_bauen.py  ──►  box-6-konfig.json
        └─ ~/shared  ──►  box-schleuse.sh bring  ──►  \\10.99.0.1\scans\schleuse\zur-box\
              └─ geplante Aufgabe „Box-Schleuse-Sync"  ──►  D:\schleuse
                    └─ konfig-anwenden.ps1 auf der Box  ──►  D:\box\konfig\
                          └─ Prüfung: gpu-fernbedienung.sh start <lane>  →  Port antwortet
```

**Die Schleuse transportiert Dateien und darf ausdrücklich nichts ausführen**
(C8, Abschnitt „Grenzen"). Das Anwenden bleibt deshalb ein Schritt auf der Box —
angestoßen über die Fernbedienung, nicht über die Schleuse. Diese Trennung ist
kein Hindernis, sie ist die Sicherheitsgrenze, und dieses Konzept verschiebt sie
**nicht**.

### 5.6 Ausführungsform (Step 2a)

| # | Frage | Antwort |
|---|---|---|
| 1 | Mehrere Schritte nötig? | ja — erzeugen, schleusen, anwenden, prüfen |
| 2 | Schrittfolge steht vorher fest? | ja → **feste Kette** |
| 3 | Teilaufgaben unabhängig? | nein → sequenziell |
| 4 | Barriere nötig? | nein |
| 5 | Verzweigung je Zwischenergebnis? | nein → **kein Graph, kein Router** |
| 6 | Schleife? | **keine** — jeder Lauf endet |

**Ergebnis: eine vierstellige, fest verdrahtete Kette.** Kein Agent, kein
Dienst, kein Zustandsautomat. Wer hier einen Orchestrator baut, hat die
Ausfallursache von morgen gebaut.

---

## 6 Adversariale Analyse

Die drei Rollen wurden **inline** durchgespielt, nicht als drei unabhängige
Agenten (Sitzungsvorgabe: keine Subagenten ohne Auftrag). Das ist eine echte
Schwächung — ein Kritiker, der den Steelman gelesen hat, zieht die Schläge
zurück. Ich benenne es, statt es zu kaschieren; die Konfliktmatrix in §6.4 ist
entsprechend selbst-erhoben.

### 6.1 Advocatus Diabolus

**AD-1 — Die zweite Wahrheit wird nur verschoben, nicht beseitigt.**
Nach dem Umbau gibt es `lanes.json` **und** `box-6-konfig.json` auf der Box. Ist
letztere per Hand geändert worden, ist sie wieder die wirksame Wahrheit — und
niemand merkt es, weil der Generator nur schreibt und nie vergleicht.
→ **Zugestanden. Führt zu REC-4** (der Generator schreibt einen `erzeugt_aus`-
Stempel; `konfig-anwenden.ps1` verweigert das Überschreiben einer Datei ohne
diesen Stempel und meldet das laut.)

**AD-2 — „Repo ist Quelle" ist behauptet, solange die Box ohne Repo bootet.**
Der Autostart der Box (`box-2-firewall-und-autostart.ps1`,
`box-5-comfyui-autostart.ps1`) startet Dienste **ohne** jede Rückfrage beim
Repo. Ein Neustart stellt also den Box-Stand her, nicht den Repo-Stand.
→ **Zugestanden, nicht lösbar und auch nicht zu lösen.** Die Box muss ohne
Netz booten können. Das Konzept beansprucht Hoheit über die *Deklaration*, nicht
über die *Laufzeit*. Wo Autostart und `lanes.json` auseinanderlaufen, ist das
ein Befund — deshalb REC-5 (Autostart aus derselben Deklaration erzeugen).

**AD-3 — Das Gate erzwingt Formalie, nicht Wahrheit.** `pfad_budget.py` zählt
Zeichenketten. Ein Skript kann `D:\box` aus zwei Teilstücken zusammensetzen und
das Gate sieht nichts.
→ **Zugestanden.** Ein Gate gegen böswillige Umgehung ist hier nicht das Ziel;
es geht um versehentliche Wiederholung, und die trifft es. Ehrlicher Vermerk
statt falscher Sicherheit.

**AD-4 — Die Reihenfolge schützt die falsche Lane.** Bild und Training bleiben
stehen, weil sie teuer sind. Genau dort sitzen aber die acht Cross-Repo-Pfade —
also bleibt der schmerzhafteste Teil ungelöst, und das Konzept feiert einen
Erfolg an den drei billigsten Lanes.
→ **Teilweise zugestanden.** Der Einwand trifft den Nutzen, nicht die Methode:
drei umgezogene Lanes belegen die Kette, und die Kette ist die Voraussetzung
dafür, die Bild-Lane *überhaupt* verlässlich umziehen zu können. Aber er ist
der Grund, warum §13 die Bild-Lane als Kill-Gate-Kriterium führt und nicht als
„später".

**AD-5 — Ein Werkzeug wird zur Boundary.** `lanes.json` in music-lab macht das
Ton-Repo faktisch zum Eigentümer der Bild- und Wort-Lane. Das ist eine
Zuständigkeitsgrenze, die niemand beschlossen hat.
→ **Zugestanden, und es ist der wichtigste Einwand.** Antwort in §8/A2 und
REC-6: der Umzug nach platform bekommt eine **benannte, zählbare** Schwelle
statt eines Bauchgefühls.

### 6.2 Maintainer 2028

Was findet jemand vor, der in achtzehn Monaten dazukommt?

- **Gut:** eine Datei beantwortet „welche Dienste gibt es, auf welchem Port,
  wem gehören sie". Heute ist diese Frage nur durch Lesen von zwölf Skripten
  plus einer Live-Messung zu beantworten.
- **Schlecht:** er findet `lanes.json` in einem Repo namens *music-lab* und
  sucht die Bild-Lane zuerst woanders. Der Name ist die Falle, nicht die
  Struktur.
- **Gefährlich:** er ändert `box-6-konfig.json` direkt auf der Box, weil das
  schneller geht — und der nächste Ausrollvorgang wirft seine Änderung weg. Der
  Stempel aus REC-4 ist genau dagegen gebaut.

### 6.3 Was dieses Konzept an bestehenden Problemen *verschlimmert*

Ehrliche Liste, statt nur Verbesserungen zu zählen:

- **Ein Ausrollschritt mehr.** Wer heute eine Lane ändert, ändert ein Skript.
  Künftig ändert er `lanes.json`, erzeugt, schleust, wendet an, prüft. Für eine
  Einmal-Änderung ist das **langsamer**. Der Gewinn liegt beim vierten Mal.
- **Die Fernbedienung wird abhängiger.** Verliert sie ihren Findungs-Teil, kann
  sie sich nach einem Totalverlust der Konfiguration nicht mehr selbst heilen.
  → Gegenmaßnahme: der Findungs-Teil wird **nicht gelöscht**, sondern zu
  `box-6-fernbedienung.ps1 -Aktion vorschlagen` — er erzeugt dann einen
  `lanes.json`-Entwurf zum Einchecken, statt die wirksame Konfiguration zu
  schreiben. Aus dem Automatismus wird ein Werkzeug.
- **Zwei Formate im Gate.** `.ps1` und `.json` mit derselben Regex zu prüfen
  erzeugt Falschtreffer (der erste Anlauf des Gates zählte bereits per
  Teilstring falsch, C2-Kommentar). Das ist Arbeit, die im MVC steckt.

### 6.4 Konfliktmatrix

| Frage | Steelman | Diabolus | Maintainer 2028 | Auflösung |
|---|---|---|---|---|
| Ist der Umzug den Aufwand wert? | nein, läuft doch | ja, aber falsche Lanes zuerst | ja | **ja**, mit Bild-Lane im Kill-Gate |
| Wo lebt `lanes.json`? | music-lab (Werkzeug ist dort) | platform (Neutralität) | platform (Name führt in die Irre) | **music-lab jetzt**, Umzugsschwelle in REC-6 |
| Findung ganz weg? | nein, sie hat die Box gerettet | ja, sie ist die Ursache | nein, Selbstheilung | **umwidmen** zu `-Aktion vorschlagen` |

Das ist echter Dissens an drei Stellen, keine Bestätigungsrunde.

---

## 7 Deep-Dive: die drei Stellen, an denen es real scheitern kann

### 7.1 Henne und Ei — der Ausrollweg zieht sich nicht selbst um

`Box-Schleuse-Sync` liegt als geplante Aufgabe auf `D:\ai-toolkit\box-schleuse-sync.ps1`
(C5). Die Fernbedienung liest ihre Konfiguration **neben sich selbst**
(`Join-Path $PSScriptRoot 'box-6-konfig.json'`, C1 Z. 31). Beide sind Teil des
Umzugs, und beide sind der Weg, über den umgezogen wird.

**Konsequenz für die Reihenfolge:** Fernbedienung und Schleusen-Sync ziehen
**zuletzt** um, an der Box, mit dem Owner davor. Nicht aus Vorsicht, sondern
weil die Box **kein IPMI** hat und der 5950X **keine iGPU** — wer den
Fernzugang kappt, braucht Monitor und Tastatur am Gerät (C12).

### 7.2 venvs überleben den Umzug nicht

`.venv\Scripts\*.exe` und `pyvenv.cfg` tragen absolute Pfade; alle drei
gemessenen venvs haben `home=C:\Users\achim` (C5). Für jede Lane heißt Umzug
also: Daten verschieben, venv **neu anlegen**, Pakete neu installieren.
Modellgewichte wandern mit, wenn die Cache-Verzeichnisse gesetzt werden — sonst
lädt die Sprach-Lane 4B-Gewichte ein zweites Mal.

`sprache.ps1` macht das bereits richtig: es legt das Gerüst
(`konfig`, `skripte`, `dienste`, `daten`, `logs`) an und nimmt eine **bereits
vorhandene** Installation, statt neu zu laden (C6, Z. 44–49 und Z. 151). Die
Sprach-Lane ist damit nicht nur die billigste, sondern die einzige, deren
Umzugslogik schon geschrieben ist.

### 7.3 Der GPU-Melder ist die Probe aufs Exempel

Port 8010 ist **zu**, obwohl `D:\ai-toolkit\gpu-melder-autostart.ps1` existiert
(C5). Der Dienst gehört illustration-hub, läuft auf der Box, steht in keiner
Lane-Liste und in keinem Gate — er ist genau der Fall, für den dieses Konzept
gebaut ist. Als Lane-Datensatz wäre „8010 antwortet nicht" ein **prüfbarer
Zustand** statt eines Befunds, den jemand zufällig findet.

Nebenwirkung mit Wert über dieses Konzept hinaus: Der Melder ist das
Messwerkzeug für die Peak-VRAM-Frage aus der Hardware-Vorlage (C12). Solange er
nicht läuft, ist die Kaufentscheidung ohne Messgrundlage.

---

## 8 Alternativen

| # | Alternative | Kosten | Warum nicht |
|---|---|---|---|
| **A1** | Nur aufräumen: alles nach `D:\box`, Konfig bleibt auf der Box | gering | **Falsifiziert am eigenen Fall:** die Sprach-Lane wurde am 2026-08-18 aufgeräumt (drei Skripte → eins), und die Konfiguration zeigte danach *trotzdem* auf ein leeres Verzeichnis, weil die Findung sie erzeugte (C5, C12). Ordnung ohne Deklaration hält genau bis zur nächsten Lane. |
| **A2** | `lanes.json` in `platform/infra/` neben `ports.yaml` | mittel | Sachlich sauberer (Neutralität, AD-5). Aber Ratsche, Gate, Inventar und alle zwölf Box-Skripte liegen in music-lab; ein Cross-Repo-Gate kostet heute mehr, als die Neutralität einbringt. **Nicht verworfen, sondern terminiert** — REC-6. |
| **A3** | Box komplett neu aufsetzen | hoch | 113 GB Betriebsdaten, laufende Bild-Lane, Trainingsdatensätze in `D:\lora`. Ein sauberer Neubau wäre das beste Ergebnis und das schlechteste Risiko. |
| **A4** | Alles auf die Hub-Seite ziehen, Box nur noch Rechenknecht | sehr hoch | Ist die Richtung von ADR-296 (C9) und langfristig richtig — aber Phase 5/6 stehen dort auf **Kill** aus Kostengründen, mit dokumentiertem Owner-Override aus Souveränitätsgründen. Dieses Konzept ist die *Vorstufe*, kein Ersatz. |

---

## 9 Out-of-the-Box

**O1 — Die Hardware-Randbedingung ist ein Architektur-Faktum, kein Nebensatz.**
Kein IPMI, keine iGPU (C12). Jede Änderung, die den Fernzugang kappen kann,
kostet eine Fahrt zum Gerät. Das ordnet die Umzugsreihenfolge zwingend — und
es ist ein Argument in der offenen Kaufentscheidung, das dort bisher fehlt.

**O2 — `lanes.json` beantwortet nebenbei eine Frage aus ADR-296.** Der
Lease-Arbiter muss wissen, welche Dienste um die Karte konkurrieren. Heute steht
diese Liste dreifach: in `box-6-fernbedienung.ps1`, in der `case`-Zeile von
`gpu-fernbedienung.sh` (C7 nennt das ausdrücklich als Wartungsfalle: „Die
Dienstliste steht an zwei Stellen") und implizit im Arbiter. Eine Deklaration
kann alle drei speisen. Das ist kein Mehraufwand — es ist der eigentliche
Hebel, und er war nicht der Anlass dieses Konzepts.

**O3 — Die Löschregel ist wertvoller als der Umzug.** `D:` trägt 227 GB, davon
113 GB Betrieb und 106 GB Fremddaten (C5). Der Umzug gewinnt kaum Platz. Was er
gewinnt, ist die Fähigkeit, überhaupt sagen zu können, was Betrieb ist und was
nicht — und *das* macht Löschen erst verantwortbar.

---

## 10 Befunde

| ID | Befund | Klasse | Beleg |
|---|---|---|---|
| B1 | Die Fernbedienung **erzeugt** die Konfiguration durch Suchen; ein gefundener Zustand kann nicht falsch sein | E2 | C1 Z. 201–263 |
| B2 | Das Pfad-Budget liest ausschließlich `*.ps1`; ein Pfad in `.json` entkommt der Ratsche | E2 | C2 `rglob("*.ps1")` |
| B3 | Die Dienstliste steht an mindestens zwei Stellen und muss von Hand synchron gehalten werden | E2 | C7 |
| B4 | illustration-hub hat 8 harte Box-Pfade in 5 Dateien; alle hängen an Lanes, die *nicht* jetzt umziehen | E2 | C10, C11 |
| B5 | Der Ausrollweg existiert, darf aber nichts ausführen — Anwenden bleibt ein Box-Schritt | E2 | C8 |
| B6 | Fernbedienung und Schleusen-Sync sind Teil des Umzugs **und** sein Werkzeug (Henne/Ei) | E2 | C1 Z. 31, C5 |
| B7 | Port 8010 ist zu, obwohl das Autostart-Skript existiert — ein Dienst ohne Zuständigkeit | E2 | C5 |
| B8 | `sprache.ps1` legt das `D:\box`-Gerüst bereits an und nimmt vorhandene Installationen | E2 | C6 Z. 44–49, 151 |
| B9 | Wer die Dienste tatsächlich hält, ist ungemessen (verfälschter erster Inventar-Lauf) | E2 | C5 |

---

## 11 Top-5-Risiken

| # | Risiko | Eintritt | Wirkung | Gegenmaßnahme |
|---|---|---|---|---|
| R1 | Fernzugang gekappt, Box ohne IPMI/iGPU nicht erreichbar | mittel | **hoch** — Fahrt zum Gerät, alle Lanes tot | Fernbedienung zuletzt, mit Owner am Gerät (§7.1) |
| R2 | venv-Neuaufbau scheitert (Netz, Version, Paketquelle) | mittel | mittel — eine Lane aus | Altort bleibt bis zur bestandenen Portprüfung stehen; Rückfall = alte Konfig |
| R3 | Handänderung auf der Box wird vom nächsten Ausrollen überschrieben | mittel | mittel — stiller Verlust | `erzeugt_aus`-Stempel, Anwenden verweigert stempellose Dateien (REC-4) |
| R4 | Modellgewichte werden versehentlich neu geladen | gering | mittel — Zeit, Bandbreite | Cache-Verzeichnisse setzen, vorhandene Installation bevorzugen (B8) |
| R5 | Konzept bleibt bei den drei billigen Lanes stehen, Bild/Training driften weiter | **hoch** | hoch — Ursache überlebt | Bild-Lane ist Kill-Gate-Kriterium K4, nicht „später" (§13) |

---

## 12 Empfehlungen

| # | Empfehlung | Datei / Artefakt |
|---|---|---|
| **REC-1** | `lanes.json` anlegen, alle sechs Lanes deklarieren (song, bild, text, sprache, stems, melder, training), `wurzel` genau einmal | `music-lab/box-setup/lanes.json` |
| **REC-2** | Generator schreiben: `lanes.json` → `box-6-konfig.json`; Selbsttest gegen `scripts/fakes/` | `music-lab/box-setup/konfig_bauen.py` |
| **REC-3** | Ratsche auf `*.json`, `*.py`, `*.sh`, `*.md` erweitern; `D:\box 1` ins Budget; Falschtreffer-Test wie beim ersten Gate-Anlauf | `music-lab/box-setup/pfad_budget.py`, `PFAD-BUDGET.txt` |
| **REC-4** | `erzeugt_aus`-Stempel in `box-6-konfig.json`; `konfig-anwenden.ps1` verweigert stempellose Dateien und meldet laut | `music-lab/box-setup/konfig-anwenden.ps1` (neu) |
| **REC-5** | Findungs-Teil der Fernbedienung **nicht löschen**, sondern zu `-Aktion vorschlagen` umwidmen (erzeugt `lanes.json`-Entwurf) | `music-lab/box-setup/box-6-fernbedienung.ps1` Z. 201–263 |
| **REC-6** | Umzugsschwelle nach platform **zählbar** festhalten: sobald ein zweites Repo `lanes.json` zum **zweiten Mal** ändern muss, zieht die Datei nach `platform/infra/` | dieses Dokument, §13 K5 |
| **REC-7** | Die 8 illustration-hub-Pfade **im selben PR** wie die Bild-/Training-Lane ändern, nicht davor und nicht danach | `illustration-hub` (5 Dateien, §3) |
| **REC-8** | `box-inventar.ps1` erneut laufen lassen — der erste Lauf war durch `$pid` verfälscht, „wer hält die Dienste" ist offen | `music-lab/box-setup/box-inventar.ps1` |

---

## 13 Entscheidung, Kill-Gate, 30/60/90

### Entscheidung

**Angenommen (Owner, 2026-08-19):** Konfig-Hoheit wandert ins Repo — „Repo ist
Quelle, Box ist Kopie". Umzug Lane für Lane, beginnend mit den drei
abschaltbaren (sprache, stems, song). `lanes.json` lebt vorerst in music-lab.

### Kill-Gate

Das Konzept wird **abgebrochen und auf A1 zurückgestuft**, wenn K1 scheitert.
K2–K5 sind Fortschrittsschwellen, keine Abbruchgründe.

| # | Kriterium | Status | Beleg |
|---|---|---|---|
| K1 | Die Kette (erzeugen → schleusen → anwenden → prüfen) läuft für **sprache** durch, ohne dass jemand auf der Box eine Datei von Hand anfasst — abgesehen vom einmaligen Erstlauf. Frist **2026-09-15** | offen | – |
| K2 | `gpu-fernbedienung.sh start sprache` → Port 8002 antwortet nach dem Umzug | offen | – |
| K3 | `pfad_budget.py` findet `D:\box` in genau **einer** Datei (`lanes.json`); die Zeilen für `D:\ace-step`, `D:\ace-step-15`, `D:\moss-tts`, `D:\msst`, `D:\msst-venv`, `D:\sprache` sind aus dem Budget verschwunden | offen | – |
| K4 | Bild-Lane umgezogen **und** die 8 illustration-hub-Pfade im selben PR nachgezogen. Ohne K4 hat das Konzept die Ursache nicht erreicht (AD-4/R5). Frist **2026-10-31** | offen | – |
| K5 | Zweites Repo ändert `lanes.json` zum zweiten Mal → Datei zieht nach `platform/infra/` (REC-6) | offen | – |

**Exception-Budget:** eine Fristverlängerung je Kriterium, datiert und hier
eingetragen. Eine zweite Verlängerung ist ein Kill.

### 30 / 60 / 90

| Frist | Inhalt |
|---|---|
| **30 Tage** (bis 2026-09-18) | REC-1 bis REC-4 gebaut, sprache + stems + song umgezogen, K1–K3 beantwortet |
| **60 Tage** (bis 2026-10-18) | REC-5 + REC-8; Fernbedienung und Schleusen-Sync am Gerät umgezogen (Owner anwesend) |
| **90 Tage** (bis 2026-11-17) | K4: Bild-Lane + illustration-hub-Pfade; Training-Lane; Löschregel auf die Altorte angewandt |

---

## Anhang: ehrliche Enforcement-Grenze

Dieses Dokument **schreibt** `review_by`, `kill_criteria` und
`superseded_by_spec`, **erzwingt** sie aber nicht. Ohne ein Lifecycle-Gate, das
überfällige Konzepte auf `stale` setzt, ist die Kontrolle hier ein
Review-Gate, kein Exit-Code. Das gilt für alle KONZ-Dokumente der Plattform und
wird hier nicht als gelöst verkauft.
