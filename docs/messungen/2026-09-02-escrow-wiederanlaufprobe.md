# Wiederanlaufprobe mit den ausgelagerten Schlüsseln — 2026-09-02

> Auftrag: [platform#2504](https://github.com/achimdehnert/platform/issues/2504),
> Owner-Go im Kapitäns-Kanal („28 go", „64 go"). Ausführung: Claude Code.

## Die Frage, die hier beantwortet wird

Nicht „ist das Backup da?" und nicht „wie lange dauert ein Restore?", sondern:

> **Öffnet der ausgelagerte Schlüssel das Archiv — von einer Maschine, die nicht
> der gesicherte Host ist, und ausschließlich mit den Escrow-Kopien?**

Bis zu dieser Probe war belegt, dass die Kopien byte-gleich zur Quelle sind. Das ist
etwas anderes: eine Prüfsumme sagt, dass die Kopie stimmt, nicht, dass die **Menge**
vollständig ist. Genau daran war der erste Escrow-Versuch desselben Tages gescheitert
(er sicherte eine Datei, die statt des Passworts nur einen Verweis darauf enthielt).

## Aufbau

| | |
|---|---|
| Ausführende Maschine | Dev-Maschine, **nicht** der gesicherte Host |
| Werkzeug | Wegwerf-Container `restic/restic:latest`, danach verworfen |
| Eingaben | ausschließlich die drei Escrow-Dateien, **read-only** eingehängt |
| Nicht benutzt | jede Datei des gesicherten Hosts, dessen restic-Installation, dessen Umgebung |

Der Container bekam die Escrow-Kopien an genau den Pfaden eingehängt, auf die die
Umgebungsdatei zeigt. Damit lief die Probe mit der Konfiguration **unverändert** so,
wie sie im Ernstfall vorläge — kein Umschreiben, kein Anpassen.

## Stufe 1 — öffnet der Schlüssel das Archiv?

| | |
|---|---|
| Kommando | `restic snapshots --latest 3` |
| Ergebnis | **126 Snapshots** gelistet |
| Bedeutung | Schlüssel gültig, Server erreichbar, Zertifikat akzeptiert |

## Stufe 2 — kommt auch der Inhalt zurück?

| | |
|---|---|
| Quell-Snapshot | `3b9e2d1e`, Tag `config`, erzeugt 2026-09-02 03:30:17 UTC von `root@prod-b` |
| Zurückgeholt | `/etc/fstab` in ein Wegwerf-Verzeichnis im Container |
| sha256 zurückgeholt | `cb89cacebc19e003…` |
| sha256 live auf `prod-b` | `cb89cacebc19e003…` |
| Urteil | ✅ **bestanden** — byte-gleich |

Dauer: Sekunden. Das ist **keine** RTO-Messung; zurückgeholt wurde eine einzelne
kleine Datei, nicht eine Anwendung. Wer eine RTO braucht, findet sie in den
Feuerübungen unter `docs/runbooks/restore-drills/`.

## Auffälligkeiten

1. **Der erste Auswahlversuch traf daneben.** `--include /etc/hostname` lieferte
   „Restored 0 files" — der `config`-Snapshot sichert eine feste Pfadliste, und
   `/etc/hostname` steht nicht darin. Ein Restore, der 0 Dateien zurückholt, ist
   **kein** bestandener Test; erst die zweite Wahl (`/etc/fstab`, nachweislich im
   Snapshot) trug.
2. **Der jüngste `config`-Snapshot stammt von `prod-b`**, nicht von `prod`. Der
   Vergleich lief deshalb gegen `prod-b` — sonst hätte die Gegenprobe zwei
   verschiedene Hosts verglichen und wäre wertlos gewesen.
3. **Das Protokoll liegt bewusst nicht unter `docs/runbooks/restore-drills/`.** Der
   `backup-meter` bewertet dort das jüngste Protokoll unabhängig von der Anwendung;
   dieses hier hätte die Uhr der quartalsweisen risk-hub-Übung um bis zu 100 Tage
   zurückgesetzt, obwohl es eine andere Frage beantwortet. Siehe
   [#2682](https://github.com/achimdehnert/platform/issues/2682).

## Was damit **nicht** bewiesen ist

- **Der Ernstfall.** Die Probe lief über dieselbe Netzverbindung wie der tägliche
  Sicherungslauf. Sie belegt den Schlüssel, nicht die Lage, in der der gesicherte
  Host fehlt.
- **Die Zweitkopie.** Ob die Werte im Passwortspeicher des Owners vollständig und
  lesbar abgelegt sind, ist eine Selbstauskunft und hier nicht prüfbar — bewusst,
  denn ein Agent hat dort keinen Zugang.
- **Andere Archive.** Geprüft wurde das Offsite-Repo. Für Sicherungen anderer Knoten
  gilt der Befund nicht.
