# Benutzertrennung in Paperless (doc-hub, 2026-08-02)

Ausgeführte Umstellung, hier als Beleg und Wiederholbarkeit. Alle Skripte laufen **im**
Paperless-Container und sind trockenlauffähig — sie ändern erst mit `SCHARF=1` etwas.

```
ssh root@<host> "docker exec -i [-e SCHARF=1] iil_dochub_web python3 manage.py shell" < <skript>
```

## Ausgangslage

`docs.iil.pet` steht hinter Cloudflare Access; Paperless übernimmt die Identität aus der
Kopfzeile `Cf-Access-Authenticated-User-Email` (`PAPERLESS_ENABLE_HTTP_REMOTE_USER`). Der
Anmeldename **ist** also die E-Mail-Adresse. Die vorhandenen Konten hießen aber `mara`,
`bine`, `achim` — beim ersten Zutritt hätte Paperless daneben neue, leere Konten angelegt
und die alten mitsamt ihren Dokumenten unerreichbar zurückgelassen.

## Reihenfolge (nicht vertauschbar)

| Skript | Was | Ergebnis am 2026-08-02 |
|---|---|---|
| `paperless_benutzer.py` | liest nur — Konten, Gruppen, Besitz | Bestandsaufnahme |
| `paperless_stufe1.py` | Doppelgänger zusammenführen | `mara`→`md@dehnert.team`, `bine`→`sd@dehnert.team`, `achim`→`achim.dehnert@iil.gmbh` |
| `paperless_stufe4.py` | Besitz übertragen | 711 Dokumente ans Arbeitskonto, 0 ohne Besitzer |
| `paperless_stufe3.py` | Superuser entziehen | 4 entzogen, 2 behalten |
| `paperless_rechte.py` | Rechte angleichen | Mara 24 → 40 |

**Stufe 4 muss vor Stufe 3 laufen.** Ein Superuser sieht in Paperless jedes Dokument;
entzieht man die Rechte zuerst, verschwinden die noch nicht übertragenen Dokumente aus
dem Blick, bevor sie einen Besitzer haben.

## Zwei Eigenheiten von Paperless, die den Zuschnitt bestimmen

- **Kein Besitzer heißt für alle sichtbar.** Die zwei besitzerlosen Dokumente mussten
  deshalb mit übertragen werden — sonst hätten Mara und Bine sie gesehen.
- **Umbenennen ist harmlos, Zusammenführen nicht.** Bei einer Umbenennung bleibt die
  Benutzerkennung, also bleiben Dokumente, Einzelrechte und die guardian-Einträge gültig.
  Existieren beide Konten (`achim` und `achim.dehnert@iil.gmbh`), muss jeder Besitzverweis
  einzeln umgehängt werden — `paperless_stufe1.py` tut das in einer Transaktion und
  deaktiviert das Quellkonto, statt es zu löschen.

## Endstand

| Konto | Superuser | Dokumente |
|---|---|---|
| `achim.dehnert@iil.gmbh` | ja | 776 |
| `md@dehnert.team` | nein | 27 |
| `sd@dehnert.team` | nein | 11 |
| `admin` | ja (Notzugang) | 0 |
| `akadmin`, `ad@dehnert.team`, `pg@dehnert.team`, `admin@wir-digital.de` | nein | 0 |

`admin` behält die Superuser-Eigenschaft bewusst: bricht die Kopfzeilen-Anmeldung über
Cloudflare, ist das lokale Konto der einzige Weg zurück ins System.

Rücknahme für ein einzelnes Konto:

```python
User.objects.filter(username="<name>").update(is_superuser=True, is_staff=True)
```
