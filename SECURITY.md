# Sicherheitshinweise

<!-- Vorlage aus achimdehnert/platform docs/templates/SECURITY.md — erzeugt durch
     tools/welle_security_notices.py; Platzhalter {{...}} werden je Repo gefüllt.
     Nicht von Hand pflegen: Änderungen an der Vorlage, dann neu erzeugen. -->

## Sicherheitsproblem melden

Bitte **kein öffentliches Issue** mit technischen Details zu einem Sicherheitsproblem
(Schwachstelle, versehentlich eingechecktes Geheimnis, personenbezogene Daten im Repo).

Bitte den Repo-Owner direkt über GitHub anschreiben (Profil `achimdehnert`) oder ein Issue **nur mit dem Label `security` und ohne technische Details** anlegen — die Details werden dann vertraulich nachgefragt.

Wir bestätigen den Eingang, holen fehlende Details über einen vertraulichen Kanal ein
und melden zurück, was daraus geworden ist. Kritische Funde werden vorrangig behandelt.

## Was gilt, wenn ein Geheimnis im Repo landet

Ein eingechecktes Passwort, Token oder ein privater Schlüssel gilt ab dem Moment als
**kompromittiert** — er wird rotiert, nicht nur aus der Historie entfernt. Bitte den
Fund melden, auch wenn er schon wieder gelöscht ist.

## Welcher Stand wird gepflegt

Korrekturen gehen auf den Stand von `main` und auf die jeweils letzte veröffentlichte Version. Ältere
Stände erhalten keine Sicherheitskorrekturen.

## Regeln für Mitwirkende

- Keine Zugangsdaten, keine Verbindungszeichenfolgen mit Passwort, keine privaten
  Schlüssel im Repo — auch nicht in Tests, Beispielen oder Doku.
- Keine personenbezogenen Daten in Fixtures, Screenshots oder Beispieldaten.
- Abhängigkeiten nur mit Versionsangabe; Sicherheitsupdates werden nicht aufgeschoben.
