# Schleusen-Abgleich auf der GPU-Box -- die Box-Seite von platform/tools/box-schleuse.sh.
#
# WOZU
#
# Ohne diesen Abgleich muss ein Mensch jedes Mal von Hand kopieren, bevor ein Agent auf
# dem Dev-Host etwas von der Box sehen kann. Mit ihm legt die Box selbstaendig ab und holt
# selbstaendig -- der Agent arbeitet dann ohne Zuruf.
#
#     D:\schleuse\raus\   --->  \\10.99.0.1\scans\schleuse\von-box\    (immer an)
#     \\...\zur-box\      --->  D:\schleuse\rein\                       (nur mit -Rein)
#
# WAS HIER NICHT PASSIERT
#
# Nichts wird ausgefuehrt. Der Abgleich kopiert Dateien und sonst nichts -- eine Datei, die
# in `rein\` landet, ist ein Ablage-Vorgang, kein Befehl. Wer sie ausfuehren will, tut das
# von Hand. Diese Grenze ist Absicht: ein Transportweg, den man zum Ausfuehren ueberreden
# kann, ist kein Transportweg mehr.
#
# `-Rein` ist deshalb NICHT der Standard. Es erlaubt einer Gegenstelle, Dateien auf dieser
# Maschine abzulegen -- eine Ausweitung, die eine bewusste Entscheidung verdient und nicht
# nebenbei mitlaufen sollte.
#
# EINRICHTEN (PowerShell als Administrator, einzeilig):
#
#     powershell -ExecutionPolicy Bypass -File .\box-schleuse-sync.ps1 -Einrichten
#
# Legt eine Aufgabe an, die alle 5 Minuten laeuft. Mit -Rein zusaetzlich die Gegenrichtung.
# Einmalig von Hand pruefen geht ohne -Einrichten: das Skript gleicht dann sofort ab.

param(
    [switch]$Einrichten,
    [switch]$Rein,
    [string]$Raus = 'D:\schleuse\raus',
    [string]$Herein = 'D:\schleuse\rein',
    [string]$Relais = '\\10.99.0.1\scans\schleuse',
    [int]$AlleMinuten = 5
)

# Kein $ErrorActionPreference = 'Stop': robocopy und schtasks schreiben im Normalfall nach
# stderr und liefern Exit-Codes ungleich 0, die KEINE Fehler sind. Mit 'Stop' wuerde jeder
# gewoehnliche Lauf abbrechen -- genau diese Falle hat am 2026-08-10 ein Uebergabeskript
# zerlegt (platform#1888).

$Name = 'Box-Schleuse-Sync'

function Abgleichen {
    New-Item -ItemType Directory -Force -Path $Raus, $Herein | Out-Null

    # /MIR waere falsch: es wuerde auf der Gegenseite loeschen, was hier nicht liegt.
    # Die Schleuse ist ein Durchgang, kein Spiegel -- geloescht wird nur bewusst,
    # vom Dev-Host aus mit `box-schleuse.sh leere`.
    # /Z Wiederaufnahme, /R:1 /W:2 damit ein belegtes File den Lauf nicht 30x blockiert.
    & robocopy $Raus "$Relais\von-box" /E /Z /R:1 /W:2 /NFL /NDL /NJH /NJS | Out-Null
    $raus_code = $LASTEXITCODE

    $rein_code = 'uebersprungen'
    if ($Rein) {
        & robocopy "$Relais\zur-box" $Herein /E /Z /R:1 /W:2 /NFL /NDL /NJH /NJS | Out-Null
        $rein_code = $LASTEXITCODE
    }

    # robocopy: 0 = nichts zu tun, 1 = kopiert, 2/3 = zusaetzliche Dateien am Ziel.
    # Ab 8 wird es ein echter Fehler. Alles darunter ist Normalbetrieb.
    $stand = if ($raus_code -ge 8) { "FEHLER ($raus_code)" } else { "ok ($raus_code)" }
    Write-Host ("{0}  raus: {1}  rein: {2}" -f (Get-Date -Format 'HH:mm:ss'), $stand, $rein_code)
    if ($raus_code -ge 8) { exit 1 }
}

if (-not $Einrichten) {
    Abgleichen
    exit 0
}

$skript = $MyInvocation.MyCommand.Path
$args_ = if ($Rein) { '-Rein' } else { '' }
# Eine Zeile mit Absicht: eine Backtick-Fortsetzung ueberlebt zwar in einer Datei, aber
# sie ist die Form, die beim Einfuegen in ein Terminal zerbricht. Wer den Ausdruck spaeter
# kopiert, soll ihn nicht erst reparieren muessen.
$befehl = '"{0}" -NoProfile -ExecutionPolicy Bypass -File "{1}" {2}' -f (Get-Command powershell).Source, $skript, $args_

& schtasks /Delete /TN $Name /F 2>&1 | Out-Null
& schtasks /Create /TN $Name /RU SYSTEM /RL HIGHEST /SC MINUTE /MO $AlleMinuten /F /TR $befehl 2>&1 |
    ForEach-Object { Write-Host $_ }

if ($LASTEXITCODE -ne 0) {
    Write-Host "schtasks /Create fehlgeschlagen (Exit $LASTEXITCODE) -- als Administrator gestartet?" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host ("Aufgabe '{0}' laeuft alle {1} Minuten." -f $Name, $AlleMinuten) -ForegroundColor Green
Write-Host ("  raus: {0}  ->  {1}\von-box" -f $Raus, $Relais)
if ($Rein) {
    Write-Host ("  rein: {0}\zur-box  ->  {1}" -f $Relais, $Herein) -ForegroundColor Yellow
    Write-Host "  Die Gegenrichtung ist aktiv: eine Gegenstelle kann hier Dateien ablegen." -ForegroundColor Yellow
    Write-Host "  Ausgefuehrt wird davon nichts." -ForegroundColor Yellow
} else {
    Write-Host ("  rein: aus (mit -Rein einschalten)")
}

Write-Host ""
Write-Host "Sofort einmal abgleichen:" -ForegroundColor Cyan
Abgleichen
