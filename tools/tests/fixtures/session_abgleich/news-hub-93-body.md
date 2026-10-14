## Was

Neuer Abschnitt **„Paper“** unter „Recherche“, Ersatz für thelatestinai.com (vom Server aus 403, Cloudflare).

- Bis zu **3** Arbeiten aus der Hugging-Face-Tagesliste (`api/daily_papers`), Reihenfolge = Upvotes, Relevanz-Filter siebt nur
- Dann bis zu **2** arXiv-Neueingänge (API, cs.AI/CL/RO, neueste 100), Rang wie bei der Recherche
- Dieselbe Arbeit zählt einmal (arXiv-Kennung ohne Version); unter **2** Arbeiten entfällt der Abschnitt
- Schalter `--paper feed` an `digest_bauen` und `digest_taeglich`; Quellen per `NEWS_HUB_PAPER_KURATIERT` / `NEWS_HUB_PAPER_ARXIV`
- `Fundstueck` trägt jetzt `abschnitt` (Migration 0012, Bestand → `recherche`), Platz je Abschnitt eindeutig
- `deployment/scripts/tageslauf.sh` schaltet `--paper feed` ein

## Warum eigener Abschnitt

Gemessen 2026-10-14: arXiv als weiterer Recherche-Feed verdrängte tldr.tech vollständig (5 von 5), weil Abstracts mehr Relevanzbegriffe treffen als Schlagzeilen. Der arXiv-RSS ist mit 2,9 MB über `MAX_FEED_BYTES`; die API-Abfrage liefert 100 Einträge mit ~250 KB in 0,5 s.

## Belege

- `make check`: 372 passed, 13 davon neu in `tests/test_paper.py` (Fixtures = gekürzte echte Antworten vom 2026-10-14)
- `makemigrations --check`: No changes detected
- Live-Lauf gegen beide Quellen (ohne Speichern): 5 Arbeiten, 3 Hugging Face + 2 arXiv

## Aktivierung in Prod — Reihenfolge zählt

Ein Merge deployt nichts.

1. Deploy per `workflow_dispatch` (migriert 0012 beim Start)
2. **Danach** `tageslauf.sh` auf dem Host neu installieren (`deployment/README.md`)

Umgekehrt kennt der alte Container `--paper` nicht und der Lauf um 06:15 UTC bricht ab.

Closes #92

🤖 Generated with [Claude Code](https://claude.com/claude-code)
