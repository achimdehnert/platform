# Reviews — IIL Platform

Strukturierte Code- und ADR-Reviews, versioniert und referenzierbar.

## Konvention

| Feld | Format | Beispiel |
|------|--------|----------|
| **Dateiname** | `<Typ>-<ID>-review-<YYYY-MM-DD>.md` | `ADR-118-review-2026-03-11.md` |
| **Typ** | `ADR`, `PR`, `CODE` | — |
| **ID** | ADR-Nummer, `<repo>-<PR#>`, oder frei | `ADR-118`, `risk-hub-42` |
| **Datum** | ISO-8601 | `2026-03-11` |

## Review-Format

Jeder Review folgt dem Platform-Reviewer-Format (`platform/concepts/REVIEWER_PROMPT.md`):

```
[BLOCK]    — Muss vor Akzeptanz gefixt werden
[SUGGEST]  — Empfehlung, nicht zwingend
[QUESTION] — Klärungsbedarf
[NITS]     — Kleinigkeit

Gesamturteil:
✅ APPROVED | ⚠️ APPROVED WITH COMMENTS | ❌ CHANGES REQUESTED
```

## GitHub-Integration

- Reviews mit **BLOCK-Items** → GitHub Issue mit Label `review` im betroffenen Repo
- Issue verlinkt auf die Review-Datei
- Issue wird geschlossen wenn alle BLOCKs resolved sind

## Ablauf

1. Review durchführen (Cascade, manuell, oder `/pr-review` Workflow)
2. Review als Datei hier speichern
3. Bei BLOCKs: GitHub Issue erstellen
4. Fixes implementieren → Issue schließen
5. Optional: Follow-Up-Review als neue Datei

## Index

### Aktuelle Reviews (2026)

| Datei | Gegenstand | Urteil | Issue |
|-------|-----------|--------|-------|
| [ADR-118-review-2026-03-11.md](ADR-118-review-2026-03-11.md) | billing-hub als Platform Store | ❌ → ✅ v1.2 | [platform#23](https://github.com/achimdehnert/platform/issues/23) |
| [ADR-119-review-2026-03-11.md](ADR-119-review-2026-03-11.md) | AuthoredContent Pipeline (Lore → Stil) | ❌ → ✅ v1.1 | [platform#24](https://github.com/achimdehnert/platform/issues/24) |
| [ADR-120-input-bewertung.md](ADR-120-input-bewertung.md) | Unified Deployment Pipeline (6 Input-Dateien) | ⚠️ Fixes eingearbeitet | — |
| [ADR-120-review-2026-03-11.md](ADR-120-review-2026-03-11.md) | Unified Deployment Pipeline (inkl. Input-Report) | ❌ → ✅ v1.1 Fixes applied | — |
| [ADR-114-review-2026-03-11.md](ADR-114-review-2026-03-11.md) | Discord als verlängertes Cascade IDE | ❌ → v2.0 Rewrite | — |

### Ältere Reviews (migriert aus docs/adr/reviews/)

| Datei | Gegenstand |
|-------|-----------|
| [ADR-101-ERGAENZUNG-BEWERTUNG.md](ADR-101-ERGAENZUNG-BEWERTUNG.md) | ADR-101 Ergänzung + Bewertung |
| [ADR-101-ERGAENZUNG-hetzner-cloudflare-mcp.md](ADR-101-ERGAENZUNG-hetzner-cloudflare-mcp.md) | ADR-101 Hetzner + Cloudflare MCP |
| [ADR-112-review-implementation.md](ADR-112-review-implementation.md) | ADR-112 Implementierungs-Review |
| [ADR-113-review-implementation.md](ADR-113-review-implementation.md) | ADR-113 Implementierungs-Review |
| [ADR-114-discord-ide-like-communication-gateway.md](ADR-114-discord-ide-like-communication-gateway.md) | ADR-114 Discord Gateway Review |
| [ADR-114-implementierungsplan.md](ADR-114-implementierungsplan.md) | ADR-114 Implementierungsplan |
| [ADR-115-review.md](ADR-115-review.md) | ADR-115 Grafana Dashboard Review |
| [ADR-116-input-bewertung.md](ADR-116-input-bewertung.md) | ADR-116 Input-Bewertung |
| [ADR-116-review.md](ADR-116-review.md) | ADR-116 Dynamic Model Router Review |
| [REVIEW-ADR-087-hybrid-search-architecture.md](REVIEW-ADR-087-hybrid-search-architecture.md) | ADR-087 Hybrid Search |
| [REVIEW-ADR-087-hybrid-search-architecture-v2.md](REVIEW-ADR-087-hybrid-search-architecture-v2.md) | ADR-087 Hybrid Search v2 |
| [REVIEW-ADR-088-notification-registry.md](REVIEW-ADR-088-notification-registry.md) | ADR-088 Notification Registry |
| [REVIEW-ADR-088-notification-registry-v2.md](REVIEW-ADR-088-notification-registry-v2.md) | ADR-088 Notification Registry v2 |
| [REVIEW-ADR-107-extended-agent-team.md](REVIEW-ADR-107-extended-agent-team.md) | ADR-107 Extended Agent Team |
| [REVIEW-ADR-109-110.md](REVIEW-ADR-109-110.md) | ADR-109 + ADR-110 Review |
