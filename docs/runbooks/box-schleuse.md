# Schleuse Dev-Host ↔ GPU-Box

> Dateien in beide Richtungen zwischen dem Dev-Host und der Windows-Box mit der RTX 4090.
> Werkzeug: `platform/tools/box-schleuse.sh`. Gehört zu platform#1888 (Kriterium 4).

## Warum es das braucht

**Der Dev-Host erreicht die Box nicht.** Gemessen am 2026-08-10: `10.99.0.2:8000` antwortet
nicht, während dieselbe Prüfmethode `88.198.191.108:22` als offen meldet — die Methode taugt
also, die Route fehlt. `ip route get 10.99.0.2` läuft ins Standard-Gateway; auf dem Dev-Host
gibt es kein WireGuard.

**Die Box erreicht Prod sehr wohl.** `net use` auf der Box zeigt bestehende SMB-Verbindungen
nach `\\10.99.0.1` — das ist die WireGuard-Adresse des Prod-Servers. Genau die wird hier zum
Transportweg:

```
Box  --SMB-->  Prod:/opt/paperless-consume/schleuse/  <--ssh--  Dev-Host
```

Prod ist die Relais-Station. Beide Seiten legen dort ab und holen dort.

## Vom Dev-Host

```bash
platform/tools/box-schleuse.sh hol            # von-box/ → ~/shared/von-box/
platform/tools/box-schleuse.sh bring <datei>… # → zur-box/
platform/tools/box-schleuse.sh liste          # was liegt wo
platform/tools/box-schleuse.sh leere von-box  # nach dem Abholen aufräumen
```

`bring` zieht anschließend Gruppe und Rechte gerade (`scanner`, `g+rw`). Ohne das kann die
Box — sie meldet sich als `scansnap` — eine abgelegte Datei nicht lesen, und der Fehler
fällt erst drüben auf, wo er schwer zu deuten ist.

## Von der Box (PowerShell)

Einzeilig, ohne Anführungszeichen — mehrzeilige Befehle überleben das Einfügen nicht
zuverlässig (drei belegte Fehlschläge am 2026-08-10, siehe platform#1888):

```
copy D:\pfad\zur\datei \\10.99.0.1\scans\schleuse\von-box\
```

```
copy \\10.99.0.1\scans\schleuse\zur-box\datei.py D:\ziel\
```

Ein Laufwerksbuchstabe ist nicht nötig; der UNC-Pfad funktioniert direkt. **Nicht** `Z:`
oder `Q:` benutzen — die zeigen auf `paperless-consume`, wo Dateien eingelesen werden und
verschwinden.

## Warum dieser Ordner

Die Schleuse liegt als Unterordner in der bestehenden Freigabe `scans`
(`/opt/paperless-consume`). Damit braucht sie **keine** Samba-Änderung und keinen
Dienst-Neustart — das wäre Gate 2.

Geprüft am 2026-08-10, beides mit Gegenprobe:

| Frage | Befund | Gegenprobe |
|---|---|---|
| Von einem Container gemountet? | nein | dasselbe Muster findet den echten Paperless-Mount |
| In einem Cron-Eintrag? | nein | die crontab hat 18 Zeilen, ist also lesbar |

Der Ordnername `paperless-consume` ist trotzdem irreführend; ein `LIESMICH.txt` in der
Schleuse sagt deshalb, was dort gilt.

**Sauberer wäre eine eigene Freigabe `[schleuse]`** mit eigenem Pfad. Das ändert `smb.conf`
und verlangt einen Samba-Reload — Gate 2, deshalb nur als Vorschlag notiert.

## Grenzen

- **Keine Secrets.** Die Schleuse ist ein Durchgang, kein Lager: für den `scansnap`-Nutzer
  lesbar und nicht überwacht. Zeiger auf den Fundort ja, Werte nein.
- **Kein Ausführen.** Der Weg transportiert Dateien. Ein Kommando auf der Box auszulösen
  ist etwas anderes — dafür ist Kriterium 5 aus platform#1888 offen; das arbeitende Vorbild
  ist der read-only HTTP-Endpunkt `illustration-hub/tools/gpu-melder/`.
- **Kein Aufräumen von selbst.** Nach dem Abholen `leere von-box`, sonst sammelt sich dort
  der Stand vergangener Läufe und man holt beim nächsten Mal Altes mit.

## Typischer Ablauf: LoRA-Training begutachten

1. Box: `copy D:\ai-toolkit\output\<lauf>\samples\*.jpg \\10.99.0.1\scans\schleuse\von-box\`
2. Dev-Host: `platform/tools/box-schleuse.sh hol`
3. Bilder ansehen, besten Zwischenstand wählen — **am Bild**, nicht am Verlust-Wert
4. Dev-Host: `platform/tools/box-schleuse.sh leere von-box`

Die Beispielbilder von Schritt 0 gehören dazu: ohne sie ist „sieht gut aus" ein Eindruck
und kein Vergleich.

## Ohne Zuruf: der Abgleich auf der Box

`tools/box-schleuse-sync.ps1` macht aus dem Handbetrieb einen Job. Die Box legt dann
selbstständig ab und holt selbstständig; ein Agent auf dem Dev-Host arbeitet ohne, dass
jemand kopiert.

```
D:\schleuse\raus\   --->  \\10.99.0.1\scans\schleuse\von-box\    immer an
\\...\zur-box\      --->  D:\schleuse\rein\                       nur mit -Rein
```

Einrichten auf der Box, PowerShell als Administrator, einzeilig:

```
powershell -ExecutionPolicy Bypass -File .\box-schleuse-sync.ps1 -Einrichten
```

Alle 5 Minuten, als geplante Aufgabe. Ohne `-Einrichten` gleicht das Skript einmal sofort
ab — gut zum Ausprobieren.

### Die beiden Richtungen sind nicht gleichwertig

**`raus` (Box → Dev-Host) ist harmlos.** Die Box bietet an, der Dev-Host liest. Niemandes
Reichweite wächst; der Agent sieht nur, was die Box hinlegt.

**`rein` (Dev-Host → Box) erweitert die Reichweite des Agenten** auf das Dateisystem der
Box. Deshalb ist es ausgeschaltet, bis es jemand ausdrücklich einschaltet. Was dabei gilt:

- Der Abgleich **führt nichts aus**. Eine Datei in `rein\` ist abgelegt, nicht gestartet.
- Diese Grenze ist der eigentliche Schutz. Ein Transportweg, den man zum Ausführen
  überreden kann, ist keiner mehr.
- Wer eine abgelegte Datei ausführt, tut das bewusst und von Hand.

### Warum `/MIR` nicht benutzt wird

`robocopy /MIR` würde auf der Gegenseite löschen, was auf dieser Seite fehlt. Die Schleuse
ist ein Durchgang, kein Spiegel: gelöscht wird nur bewusst, vom Dev-Host aus mit
`box-schleuse.sh leere <richtung>`. Ein Abgleich, der von selbst löscht, verliert früher
oder später etwas, das noch niemand geholt hatte.

### robocopy-Exit-Codes sind keine Fehler

`0` = nichts zu tun, `1` = kopiert, `2`/`3` = zusätzliche Dateien am Ziel. Erst ab `8`
liegt ein echter Fehler vor. Deshalb steht im Skript **kein**
`$ErrorActionPreference = 'Stop'` — damit würde jeder gewöhnliche Lauf abbrechen. Genau
diese Falle hat am 2026-08-10 ein Übergabeskript zerlegt (platform#1888).

### Eine `.ps1` muss reines ASCII sein und einen BOM tragen

Windows PowerShell 5.1 liest eine `.ps1` **ohne BOM** in der ANSI-Codepage. Aus einem
UTF-8-Em-Dash (`—`, drei Bytes) werden dabei drei Zeichen, und eines davon beendet die
Zeichenfolge, in der es steht. Der Parser meldet das dann irgendwo weiter unten:

```
Die Zeichenfolge hat kein Abschlusszeichen: ".
Die schließende "}" fehlt im Anweisungsblock oder der Typdefinition.
```

Gemessen am 2026-08-10 mit Positivkontrolle:

| Datei | Nicht-ASCII | Ergebnis |
|---|---|---|
| `gpu-melder-autostart.ps1` | 0 | lief |
| `box-schleuse-sync.ps1` (erste Fassung) | 7 Em-Dashes | Parser-Fehler |
| `gpu_melder.py` | 8 | lief — Python liest UTF-8 von sich aus |

Die dritte Zeile ist der Grund, warum das lange nicht auffiel: bei `.py` ist es harmlos,
nur bei `.ps1` nicht. Regel deshalb: `.ps1` ohne Nicht-ASCII schreiben **und** einen
UTF-8-BOM voranstellen, damit ein später ergänztes Sonderzeichen nicht dieselbe Falle
aufstellt.

### Der Abgleich läuft als Benutzer, nicht als SYSTEM

Das Relais ist eine SMB-Freigabe, deren Anmeldung an der **Benutzersitzung** hängt —
`net use` auf der Box zeigt sie dort als `Z:`/`Q:`. `SYSTEM` hat diese Anmeldung nicht und
erreicht `\\10.99.0.1\scans` nicht.

Gemessen am 2026-08-10, und die Zahlen sind der ganze Beleg:

| Lauf | Konto | Ergebnis |
|---|---|---|
| 20:18 interaktiv | achim | 24 Dateien durchgeschoben |
| ab 20:20 geplant | SYSTEM | **null**, obwohl die Quelldatei seit 20:25 bereitlag |

Das Tückische ist wieder die Stille: die Aufgabe steht auf `Bereit`, meldet keinen Fehler,
und kopiert nichts. Aufgefallen ist es nur, weil ein erwartetes Protokoll ausblieb.

Deshalb `/RU <benutzer> /IT`. Preis: der Abgleich läuft nur bei angemeldeter Sitzung.
Bildschirm sperren ist in Ordnung, abmelden nicht — dieselbe Bedingung wie beim
LoRA-Nachtlauf, und aus verwandtem Grund.
