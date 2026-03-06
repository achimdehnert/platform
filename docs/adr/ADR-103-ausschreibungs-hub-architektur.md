---
status: proposed
date: 2026-03-06
decision-makers: Achim Dehnert
consulted: Cascade
informed: –
---

# ADR-103: Adopt ausschreibungs-hub as KI-gestuetzte Ausschreibungs- und Angebotsplattform

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-03-06                                                           |
| **Autor**       | Achim Dehnert, Cascade                                               |
| **Reviewer**    | –                                                                    |
| **Relates to**  | ADR-021 (Deployment), ADR-062 (Billing), ADR-095/096/097 (aifw)      |

## Repo-Zugehoerigkeit

| Repo                | Rolle      | Betroffene Pfade / Komponenten              |
|---------------------|------------|---------------------------------------------|
| `ausschreibungs-hub`| Primaer    | Gesamtes Repo (neu)                         |
| `platform`          | Referenz   | `docs/adr/ADR-103`, Port-Registry ADR-021   |
| `billing-hub`       | Sekundaer  | Billing-Integration (Stripe, Subscriptions) |
| `mcp-hub`           | Sekundaer  | `ausschreibungs-mcp` Tool-Integration       |

---

## Decision Drivers

- **Marktluecke**: KI-gestuetzte Angebotserstellung fuer oeffentliche und private Ausschreibungen existiert nicht als bezahlbares SaaS fuer KMU
- **Branchenbreite**: Neben IT/Beratung sind **Baufirmen und Ingenieurbueros** eine Kernzielgruppe mit hohem Volumen (VOB, HOAI, GAEB)
- **Platform-Synergie**: aifw (ADR-095/096/097), billing-hub (ADR-062), Cloudflare-Tunnel (ADR-102) sind bereit
- **Monetarisierung**: Klares Tier-Modell (Starter/Professional/Enterprise) mit KI-Nutzung als Skalierungshebel
- **Foerdermodul**: BayVFP/BMBF-Foerderskizzen als Alleinstellungsmerkmal

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand

KMU, Baufirmen und Ingenieurbueros suchen Ausschreibungen manuell auf 5+ Portalen
(DTVP, TED, service.bund.de, evergabe.de, Vergabe24, subreport). Angebote werden in
Word/Excel erstellt, ohne KI-Unterstuetzung. Foerderantraege (BayVFP, BMBF, EU)
erfordern wochenlange Recherche.

Bestehende Loesungen (DTAD, cosinex, Vergabemanager) sind entweder teuer (>500 EUR/Monat),
nicht KI-gestuetzt, oder auf eine Branche beschraenkt.

### 1.2 Branchenspezifische Anforderungen

| Branche | Portale | Besonderheiten |
|---------|---------|----------------|
| **IT / Beratung** | DTVP, TED, service.bund.de | EVB-IT-Vertraege, Eignungskriterien, Referenznachweise |
| **Baufirmen** | Vergabe24, subreport, DTVP | **VOB/A**, Leistungsverzeichnisse (GAEB-Format), Nachunternehmer, Buergschaften |
| **Ingenieurbueros** | evergabe.de, TED, laenderspezifisch | **HOAI**-Leistungsphasen, VgV-Verfahren, Planungsleistungen, Bietergemeinschaften |
| **Forschung/Transfer** | BayVFP, BMBF, EU Horizon | Foerderskizzen, Konsortien, Arbeitspakete, Meilensteine |

### 1.3 Warum jetzt

- aifw Quality-Routing (ADR-096) ermoeglicht kosteneffiziente KI-Generierung auf allen Tier-Stufen
- billing-hub (ADR-062) ist live — Subscription-Management steht bereit
- Cloudflare-Tunnel (ADR-102) bietet sichere Infrastruktur fuer Enterprise-Kunden
- Wettbewerbsfenster: Noch kein Anbieter verbindet Ausschreibungssuche + KI-Angebotserstellung + Foerdermodul branchenuebergreifend

---

## 2. Considered Options

### Option A: Eigenes Repo `ausschreibungs-hub` mit Django + DRF + aifw ✅

**Pros:**
- Volle Kontrolle ueber Datenmodell und Branchenlogik
- Maximale iil-Stack-Integration (aifw, billing-hub, platform-context)
- Multi-Tenant SaaS von Anfang an
- Branchenspezifische Module (VOB, HOAI, GAEB) als Apps

**Cons:**
- Hoher initialer Entwicklungsaufwand
- Neues Repo in der Platform-Landschaft

### Option B: Erweiterung von coach-hub

**Pros:**
- Bestehende Infrastruktur nutzen

**Cons:**
- Voellig andere Domaene (KI-Governance vs. Ausschreibungen)
- Ueberlaedt coach-hub, verletzt Single-Responsibility → **Abgelehnt**

### Option C: Low-Code/No-Code (Retool, Budibase)

**Pros:**
- Schneller Prototyp

**Cons:**
- Kein aifw-Integration, kein Multi-Tenant, keine Branchenlogik → **Abgelehnt**

---

## 3. Decision Outcome

**Gewaehlt: Option A — Eigenes Repo `ausschreibungs-hub`**

Eigenstaendiges Django-Projekt mit branchenspezifischen Modulen (IT, Bau, Ingenieur),
KI-gestuetzter Angebotsgenerierung via aifw, und Foerdermodul. Multi-Tenant via
Row-Level-Security (tenant_id FK), Billing via billing-hub, Deploy via ADR-021.

---

## 4. Implementation Details

### 4.1 Infrastruktur-Parameter (ADR-021 konform)

| Parameter | Wert |
|-----------|------|
| **Repo** | `achimdehnert/ausschreibungs-hub` (private) |
| **Port** | 8095 |
| **Domain** | `ausschreibungen.iil.pet` (Tunnel) |
| **Deploy-Path** | `/opt/ausschreibungs-hub` |
| **Compose** | `docker-compose.prod.yml` |
| **Health** | `https://ausschreibungen.iil.pet/healthz/` |
| **Container** | `ausschreibungs_hub_web`, `_worker`, `_beat` |
| **Network** | `bf_platform_prod` |
| **Python** | 3.12 |
| **Django** | 5.1+ |
| **DB** | PostgreSQL 16 (eigener Stack) + pgvector |
| **Cache** | Redis 7 |
| **Settings** | `config.settings.production` / `config.settings.development` |

### 4.2 App-Struktur

```
ausschreibungs-hub/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── core/                    # Tenant, User, Branchenprofil
│   ├── ausschreibungen/         # Portal-Crawler, Klassifizierung, Matching
│   ├── angebote/                # Angebots-Editor, KI-Generierung, Versionierung
│   ├── referenzen/              # Referenzdatenbank mit pgvector-Embeddings
│   ├── foerderung/              # BayVFP, BMBF, EU Horizon
│   ├── compliance/              # Eignungspruefung, Dokumenten-Checkliste
│   ├── branchen/                # Branchenspezifische Logik
│   │   ├── it_beratung/         # EVB-IT, Eignungskriterien
│   │   ├── bau/                 # VOB/A, GAEB, Nachunternehmer, Buergschaften
│   │   └── ingenieur/           # HOAI, VgV, Leistungsphasen, Bietergemeinschaften
│   ├── api/                     # REST API v1 (DRF + drf-spectacular)
│   ├── notifications/           # E-Mail-Alerts, Deadline-Warnungen
│   └── reporting/               # Dashboard, Analytics, Win/Loss
├── templates/
├── locale/                      # i18n (DE + EN)
├── docker/app/Dockerfile
├── docker-compose.prod.yml
└── pyproject.toml
```

### 4.3 Datenmodell (Kern)

```python
# apps/core/models.py
class Tenant(models.Model):
    id          = models.BigAutoField(primary_key=True)
    public_id   = models.UUIDField(default=uuid.uuid4, unique=True)
    name        = models.CharField(max_length=300)
    branche     = models.CharField(max_length=30, choices=BranchenTyp.choices)
    plan        = models.CharField(max_length=20, choices=PlanTyp.choices, default='starter')
    settings    = models.JSONField(default=dict)  # Sprache, Waehrung, Region, GAEB-Version
    created_at  = models.DateTimeField(auto_now_add=True)

class BranchenTyp(models.TextChoices):
    IT_BERATUNG  = 'it_beratung',  'IT & Beratung'
    BAU          = 'bau',          'Baufirma'
    INGENIEUR    = 'ingenieur',    'Ingenieurbuero'
    FORSCHUNG    = 'forschung',    'Forschung & Transfer'
    SONSTIGE     = 'sonstige',     'Sonstige Dienstleistungen'


# apps/ausschreibungen/models.py
class Portal(models.Model):
    id                   = models.BigAutoField(primary_key=True)
    name                 = models.CharField(max_length=200)
    adapter_class        = models.CharField(max_length=200)  # 'apps.ausschreibungen.adapters.DtvpAdapter'
    scraping_legal_basis = models.CharField(max_length=30)   # 'api', 'rss', 'scraping_tos_checked'
    robots_txt_compliant = models.BooleanField(default=True)
    branchen             = models.JSONField(default=list)     # ['it_beratung', 'bau', 'ingenieur']
    is_active            = models.BooleanField(default=True)

class Ausschreibung(models.Model):
    id              = models.BigAutoField(primary_key=True)
    public_id       = models.UUIDField(default=uuid.uuid4, unique=True)
    tenant          = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    portal          = models.ForeignKey(Portal, on_delete=models.SET_NULL, null=True)

    # Stammdaten
    titel           = models.CharField(max_length=500)
    titel_en        = models.CharField(max_length=500, blank=True)
    zusammenfassung = models.TextField(blank=True)
    vergabestelle   = models.CharField(max_length=300, blank=True)
    deadline        = models.DateTimeField(null=True)
    original_url    = models.URLField(max_length=2000, blank=True)
    sprache_original = models.CharField(max_length=10, default='de')

    # Klassifizierung (KI, QL 4)
    relevanz_score  = models.FloatField(default=0.0)  # 0.0-1.0
    cpv_codes       = models.JSONField(default=list)
    branche         = models.CharField(max_length=30, choices=BranchenTyp.choices, blank=True)

    # Branchenspezifisch
    vergabeart      = models.CharField(max_length=50, blank=True)  # 'offen', 'nicht_offen', 'verhandlung', 'vgv'
    vergabeordnung  = models.CharField(max_length=20, blank=True)  # 'VOB', 'VOL', 'VgV', 'UVgO', 'SektVO'
    schaetzwert     = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    waehrung        = models.CharField(max_length=3, default='EUR')
    lose            = models.JSONField(default=list)  # Lose-Struktur fuer Bau-Ausschreibungen

    # Meta
    embedding       = models.BinaryField(null=True)  # pgvector via VectorField
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'relevanz_score']),
            models.Index(fields=['tenant', 'deadline']),
            models.Index(fields=['tenant', 'branche']),
        ]


# apps/angebote/models.py
class Angebot(models.Model):
    id              = models.BigAutoField(primary_key=True)
    public_id       = models.UUIDField(default=uuid.uuid4, unique=True)
    tenant          = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    ausschreibung   = models.ForeignKey(Ausschreibung, on_delete=models.CASCADE)
    erstellt_von    = models.ForeignKey('core.TenantUser', on_delete=models.SET_NULL, null=True)

    version         = models.PositiveIntegerField(default=1)
    status          = models.CharField(max_length=20, choices=AngebotStatus.choices, default='entwurf')
    ergebnis        = models.CharField(max_length=20, choices=AngebotErgebnis.choices, blank=True)

    class Meta:
        unique_together = [('ausschreibung', 'version')]


class AngebotAbschnitt(models.Model):
    """Versionierte Abschnitte fuer Multi-User-Editing und KI-Generierung."""
    id              = models.BigAutoField(primary_key=True)
    angebot         = models.ForeignKey(Angebot, on_delete=models.CASCADE, related_name='abschnitte')
    typ             = models.CharField(max_length=50)  # 'leistungsbeschreibung', 'preis', 'referenzen', ...
    titel           = models.CharField(max_length=300)
    inhalt          = models.TextField(blank=True)
    ki_generiert    = models.BooleanField(default=False)
    modified_by     = models.ForeignKey('core.TenantUser', on_delete=models.SET_NULL, null=True)
    modified_at     = models.DateTimeField(auto_now=True)


# apps/branchen/bau/models.py
class BauAngebotDetails(models.Model):
    """Bau-spezifische Angebotsdetails (VOB/A)."""
    angebot             = models.OneToOneField(Angebot, on_delete=models.CASCADE, related_name='bau_details')
    leistungsverzeichnis = models.JSONField(default=list)  # GAEB-Struktur
    gaeb_version        = models.CharField(max_length=10, default='GAEB-XML 3.3')
    nachunternehmer     = models.JSONField(default=list)   # [{name, gewerk, anteil_prozent}]
    buergschaft_typ     = models.CharField(max_length=30, blank=True)  # 'vertragserfuellung', 'gewaehrleistung'
    buergschaft_hoehe   = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    bauzeit_beginn      = models.DateField(null=True)
    bauzeit_ende        = models.DateField(null=True)
    lose_zuordnung      = models.JSONField(default=list)  # Welche Lose werden bedient


# apps/branchen/ingenieur/models.py
class IngenieurAngebotDetails(models.Model):
    """Ingenieur-spezifische Angebotsdetails (HOAI/VgV)."""
    angebot             = models.OneToOneField(Angebot, on_delete=models.CASCADE, related_name='ingenieur_details')
    hoai_leistungsphasen = models.JSONField(default=list)  # [1,2,3,4,5] = LP 1-5
    hoai_zone           = models.CharField(max_length=10, blank=True)  # Honorarzone I-V
    anrechenbare_kosten = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    honorar_berechnung  = models.JSONField(default=dict)   # Strukturierte HOAI-Berechnung
    bietergemeinschaft  = models.JSONField(default=list)    # [{firma, rolle, anteil_prozent}]
    vgv_kriterien       = models.JSONField(default=list)    # [{kriterium, gewichtung, antwort}]
    projektteam         = models.JSONField(default=list)    # [{name, rolle, qualifikation, referenzen}]
```

### 4.4 Branchenspezifische Portal-Adapter

```python
# apps/ausschreibungen/adapters/base.py
class PortalAdapter(Protocol):
    """Einheitliche Schnittstelle fuer alle Portale."""
    name: str
    scraping_legal_basis: str          # 'api', 'rss', 'scraping_tos_checked'
    robots_txt_compliant: bool
    supported_branchen: list[str]      # ['bau', 'ingenieur', 'it_beratung']

    async def fetch_new(self, since: datetime) -> list[RawAusschreibung]: ...
    async def fetch_detail(self, url: str) -> AusschreibungDetail: ...


# Bau-spezifische Adapter
class Vergabe24Adapter(PortalAdapter):
    """Vergabe24 — primaer Bau-Ausschreibungen, GAEB-Download."""
    name = 'vergabe24'
    scraping_legal_basis = 'api'
    supported_branchen = ['bau']

class SubreportAdapter(PortalAdapter):
    """subreport — kommunale Bau- und Planungsausschreibungen."""
    name = 'subreport'
    scraping_legal_basis = 'api'
    supported_branchen = ['bau', 'ingenieur']

# Ingenieur-spezifische Adapter
class EvergabeAdapter(PortalAdapter):
    """evergabe.de — VgV-Verfahren, Planungsleistungen."""
    name = 'evergabe'
    scraping_legal_basis = 'scraping_tos_checked'
    supported_branchen = ['ingenieur', 'it_beratung']

# Branchenuebergreifend
class DtvpAdapter(PortalAdapter):
    """DTVP — alle Branchen, groesste Plattform."""
    name = 'dtvp'
    scraping_legal_basis = 'api'
    supported_branchen = ['bau', 'ingenieur', 'it_beratung', 'forschung']

class TedAdapter(PortalAdapter):
    """TED (Tenders Electronic Daily) — EU-weite Ausschreibungen ab Schwellenwert."""
    name = 'ted'
    scraping_legal_basis = 'api'  # Offizielle EU-API
    supported_branchen = ['bau', 'ingenieur', 'it_beratung', 'forschung']
```

### 4.5 KI-Integration via aifw (ADR-095/096/097)

| Use-Case | QL | Starter | Professional | Enterprise |
|----------|---:|---------|-------------|-----------|
| Relevanz-Klassifizierung | 4 | 50/Monat | 500/Monat | Unbegrenzt |
| Angebots-Zusammenfassung | 5 | – | ✅ | ✅ |
| Leistungsbeschreibung generieren | 7 | – | ✅ | ✅ |
| **GAEB-LV ausfuellen (Bau)** | 7 | – | ✅ | ✅ |
| **HOAI-Honorar berechnen (Ing.)** | 6 | – | ✅ | ✅ |
| **VgV-Kriterien beantworten (Ing.)** | 7 | – | ✅ | ✅ |
| Preiskalkulation | 7 | – | ✅ | ✅ |
| Foerderskizze BayVFP/BMBF | 9 | – | ✅ | ✅ |
| Referenz-Matching (pgvector RAG) | 5 | – | ✅ | ✅ |

```python
# apps/angebote/services/generator.py
from aifw.routing import get_quality_context, route_llm_call

class AngebotGeneratorService:
    def generate_abschnitt(self, angebot, abschnitt_typ, tenant, user):
        branche = tenant.branche

        # Branchenspezifischen Prompt waehlen
        prompt_builder = self._get_prompt_builder(branche, abschnitt_typ)
        prompt = prompt_builder.build(angebot, tenant)

        # aifw Quality-Routing
        use_case = f'{branche}_{abschnitt_typ}'
        ctx = get_quality_context(
            use_case=use_case,
            tenant_id=tenant.id,
            plan_code=tenant.plan,
        )
        result = route_llm_call(ctx, prompt)

        # Audit-Event
        emit_audit_event(
            event_type='angebot.ki_generated',
            tenant_id=tenant.id,
            user_id=user.id,
            object_type='AngebotAbschnitt',
            object_id=str(angebot.public_id),
            metadata={
                'quality_level': ctx.quality_level,
                'model_used': ctx.resolved_model,
                'branche': branche,
                'abschnitt': abschnitt_typ,
            }
        )
        return result

    def _get_prompt_builder(self, branche, abschnitt_typ):
        BUILDERS = {
            ('bau', 'leistungsverzeichnis'): BauLVPromptBuilder,
            ('bau', 'nachunternehmer'): BauNachunternehmerPromptBuilder,
            ('ingenieur', 'hoai_honorar'): IngenieurHOAIPromptBuilder,
            ('ingenieur', 'vgv_kriterien'): IngenieurVgVPromptBuilder,
            ('it_beratung', 'leistungsbeschreibung'): ITLeistungPromptBuilder,
        }
        key = (branche, abschnitt_typ)
        return BUILDERS.get(key, GenericPromptBuilder)()
```

### 4.6 RBAC (Review K-01)

```python
class TenantRole(models.TextChoices):
    OWNER   = 'owner',   'Inhaber'       # Alle Rechte + Billing
    MANAGER = 'manager', 'Projektleiter' # Angebote einreichen, KI nutzen
    EDITOR  = 'editor',  'Bearbeiter'    # Ausschreibungen/Angebote bearbeiten
    VIEWER  = 'viewer',  'Leser'         # Nur lesen

class TenantUser(models.Model):
    id         = models.BigAutoField(primary_key=True)
    tenant     = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user       = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    role       = models.CharField(max_length=20, choices=TenantRole.choices)
    is_active  = models.BooleanField(default=True)

    class Meta:
        unique_together = [('tenant', 'user')]
```

### 4.7 Plan-Limits und Monetarisierung

| Feature | Starter (49 EUR) | Professional (149 EUR) | Enterprise (ab 499 EUR) |
|---------|:-:|:-:|:-:|
| Portale | 3 | Alle | Alle + Custom |
| Nutzer | 1 | 5 | Unbegrenzt |
| KI-Klassifizierungen/Monat | 50 | 500 | Unbegrenzt |
| KI-Angebotsgenerierung | – | ✅ | ✅ |
| **GAEB-Import/Export (Bau)** | – | ✅ | ✅ |
| **HOAI-Rechner (Ingenieur)** | Basis | Voll | Voll |
| **VgV-Bewertungsmatrix** | – | ✅ | ✅ |
| Referenzdatenbank | 10 | 100 | Unbegrenzt |
| Foerderskizzen-Generator | – | ✅ | ✅ |
| REST API + Webhooks | – | – | ✅ |
| White-Label / Custom Domain | – | – | ✅ |
| SLA (Reaktionszeit) | Best-Effort | 24h | 4h |

### 4.8 REST API (Review B-03, Enterprise-Tier)

```python
# config/settings/base.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'apps.api.auth.APIKeyAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'apps.api.permissions.TenantPermission',
    ],
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    'DEFAULT_THROTTLE_CLASSES': ['apps.api.throttling.TenantRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {
        'starter': '100/hour',
        'professional': '1000/hour',
        'enterprise': '10000/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# apps/api/v1/urls.py
urlpatterns = [
    path('v1/ausschreibungen/', AusschreibungListView.as_view()),
    path('v1/ausschreibungen/<uuid:public_id>/', AusschreibungDetailView.as_view()),
    path('v1/angebote/', AngebotListView.as_view()),
    path('v1/angebote/<uuid:public_id>/', AngebotDetailView.as_view()),
    path('v1/referenzen/', ReferenzListView.as_view()),
    path('v1/schema/', SpectacularAPIView.as_view()),
    path('v1/schema/swagger/', SpectacularSwaggerView.as_view()),
]
```

### 4.9 i18n (Review B-01)

```python
# config/settings/base.py
LANGUAGE_CODE = 'de'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGES = [
    ('de', 'Deutsch'),
    ('en', 'English'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
```

DE + EN als Pflichtsprachen. Weitere Sprachen per Tenant-Setting aktivierbar.
aifw-gestuetzte Auto-Uebersetzung von Ausschreibungstiteln (QL 3).

---

## 5. Migration Tracking — Phasenplan

| Phase | Inhalt | Status | Ziel |
|-------|--------|--------|------|
| **0 — Skeleton** | Repo, Docker, CI/CD, DB, Health, ADR-021-Registrierung | ⬜ | Woche 1 |
| **1 — Portal-Crawler** | DTVP + TED Adapter, Celery-Beat, Relevanz-Klassifizierung (QL 4) | ⬜ | Woche 2-3 |
| **2 — Angebots-Editor** | HTMX-Editor, KI-Generierung (QL 7), Versionierung | ⬜ | Woche 4-5 |
| **3 — Bau-Modul** | VOB/A-Logik, GAEB-Import/Export, Nachunternehmer, LV-Editor | ⬜ | Woche 6-7 |
| **4 — Ingenieur-Modul** | HOAI-Rechner, VgV-Bewertungsmatrix, Bietergemeinschaften | ⬜ | Woche 8-9 |
| **5 — Referenzen + RAG** | pgvector-Embeddings, semantisches Matching, Referenz-Import | ⬜ | Woche 10 |
| **6 — Billing + Plans** | Stripe-Integration via billing-hub, Plan-Enforcement | ⬜ | Woche 11 |
| **7 — Foerdermodul** | BayVFP/BMBF-Skizzen-Generator (QL 9), Konsortien | ⬜ | Woche 12-13 |
| **8 — Enterprise** | REST API, Webhooks, White-Label, RBAC, Audit-Trail | ⬜ | Woche 14-15 |
| **9 — i18n + Polish** | EN-Uebersetzung, DSGVO-Export, Staging, Docs | ⬜ | Woche 16 |

---

## 6. Consequences

### 6.1 Good

- Branchenuebergreifende Plattform: IT, Bau, Ingenieur, Forschung
- KI-gestuetzte Angebotserstellung senkt Bearbeitungszeit um 60-80%
- GAEB- und HOAI-Integration als USP gegenueber generischen Tools
- Klares Monetarisierungsmodell mit LLM-Kosten als natuerlichem Skalierungshebel
- Foerdermodul als Alleinstellungsmerkmal
- Volle Platform-Integration (aifw, billing-hub, Cloudflare, MCP)

### 6.2 Bad

- Hoher Entwicklungsaufwand (~16 Wochen fuer MVP)
- Branchenspezifische Logik (VOB, HOAI, GAEB) erfordert Domaenen-Expertise
- Portal-Scraping rechtlich heikel — API-basierte Portale priorisieren
- Zusaetzlicher Service auf dem Hetzner-Server (Ressourcen-Monitoring noetig)

### 6.3 Nicht in Scope

- Elektronische Vergabe (eVergabe-Submission) — nur Angebots-Erstellung, nicht Einreichung
- Bauzeitenplanung / Projektmanagement — eigenes Tool
- CAD/BIM-Integration — nur textbasierte Angebotsteile
- Eigene LLM-Modelle — aifw-Router nutzt externe Provider

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Portal-Scraping rechtlich problematisch | Mittel | Hoch | API-basierte Portale priorisieren (TED, DTVP API), robots.txt-Compliance |
| GAEB-Parser-Komplexitaet | Mittel | Mittel | Bestehende Python-Libs evaluieren (gaeb-parser), Format-Subset starten |
| HOAI-Berechnungsfehler | Niedrig | Hoch | Validierung gegen offizielle HOAI-Tabellen, Disclaimer |
| LLM-Kosten bei Enterprise-Kunden | Mittel | Mittel | aifw Semantic-Cache, Embedding-Dedup vor Klassifizierung |
| Datenschutz: Angebotsdaten bei LLM-Provider | Mittel | Hoch | AVV mit Providern, EU-Region-Option (Azure OpenAI), Tenant-Consent |
| Wettbewerber reagieren schnell | Niedrig | Mittel | Branchenbreite (Bau+Ing+IT) als Differenzierung |

---

## 8. Confirmation

1. **Health-Endpoint**: `curl -sf https://ausschreibungen.iil.pet/healthz/` → `{"status": "ok"}`
2. **CI/CD**: Repo nutzt `_ci-python.yml` + `_deploy-hetzner.yml` aus platform (ADR-021)
3. **Port-Registry**: Port 8095 in ADR-021 §2.3 registriert
4. **Billing**: billing-hub Platform-Eintrag fuer ausschreibungs-hub vorhanden
5. **Drift-Detector**: Staleness-Schwelle 6 Monate

---

## 9. More Information

- Konzept-Review: `docs/concepts/REVIEW-ausschreibungs-hub-konzept.md`
- ADR-021: Unified Deployment Pattern (Port-Registry)
- ADR-062: Central Billing Service (billing-hub)
- ADR-095/096/097: aifw Quality-Routing
- ADR-102: Cloudflare DNS/CDN/Tunnel Migration
- [DTVP API](https://www.dtvp.de)
- [TED API (EU)](https://ted.europa.eu/api)
- [GAEB-Format](https://www.gaeb.de)
- [HOAI 2021](https://www.hoai.de)
- [VOB/A](https://www.bmwsb.bund.de/SharedDocs/Gesetzgebungsverfahren/DE/vergaberecht.html)

---

## 10. Changelog

| Datum | Autor | Aenderung |
|-------|-------|----------|
| 2026-03-06 | Cascade + AD | Initial: Proposed — Grundarchitektur mit Bau/Ingenieur-Erweiterung |

---

## Anhang A: Bewertung des Konzept-Reviews

Das Review (Claude, Senior Architect) identifiziert 4 Blocker, 8 kritische und 9 hohe
Befunde. Bewertung und Einarbeitung in dieses ADR:

| Review-Befund | Bewertung | Status in ADR-103 |
|--------------|-----------|-------------------|
| **B-01 i18n** | Berechtigt, aber DE+EN reicht fuer MVP | §4.9 — Phase 9 |
| **B-02 UUID public_id** | Berechtigt, Platform-Standard | §4.3 — Alle Modelle haben public_id |
| **B-03 REST API** | Berechtigt fuer Enterprise | §4.8 — DRF + drf-spectacular, Phase 8 |
| **B-04 iil-Stack** | Berechtigt, aber Packages existieren teils noch nicht | Referenziert, realistisch priorisiert |
| **K-01 RBAC** | Berechtigt | §4.6 — 4 Rollen definiert |
| **K-02 Audit-Trail** | Berechtigt fuer Enterprise | §4.5 — emit_audit_event in Generator |
| **K-03 Outbox-Pattern** | Berechtigt, aber erst Enterprise-Phase | Phase 8 |
| **K-04 Scraping-Recht** | Berechtigt und kritisch | §4.4 — legal_basis + robots_txt Pflichtfeld |
| **K-05 SubscriptionTierConfig** | Berechtigt | §4.5 — aifw-Integration definiert |
| **K-06 DSGVO/DSFA** | Berechtigt, aber kein Code-Thema | Risiko-Tabelle §7 |
| **K-07 SLA** | Berechtigt | §4.7 — Plan-basierte SLAs definiert |
| **K-08 White-Label** | Berechtigt fuer Enterprise | Phase 8 |
| **NEU: Bau/Ingenieur** | Nicht im Original-Review | §4.3, §4.4, §4.5 — Vollstaendig integriert |
