---
status: accepted
date: 2026-03-07
decision-makers: Achim Dehnert
consulted: Cascade (Senior Architect), Claude (Principal IT Architect — Review v1+v2)
informed: billing-hub, mcp-hub, platform-team
---

<!-- Drift-Detector: staleness_months=6, drift_check_paths=["apps/", "pyproject.toml"] -->

# ADR-103: ausschreibungs-hub — KI-gestützte Ausschreibungs- und Angebotsplattform

## Metadaten

| Attribut          | Wert                                                                              |
|-------------------|-----------------------------------------------------------------------------------|
| **Status**        | Accepted                                                                          |
| **Scope**         | platform                                                                          |
| **Version**       | v3 (2026-03-07) — alle Review-Befunde adressiert                                 |
| **Autor**         | Achim Dehnert, Cascade                                                            |
| **Reviewer**      | Claude (Principal IT Architect) v1+v2; Cascade (Senior Architect) v3              |
| **Relates to**    | ADR-007, ADR-021, ADR-027, ADR-028, ADR-049, ADR-062, ADR-072, ADR-077, ADR-095/096/097, ADR-102 |

## Repo-Zugehörigkeit

| Repo                 | Rolle    | Betroffene Pfade                              |
|----------------------|----------|-----------------------------------------------|
| `ausschreibungs-hub` | Primär   | Gesamtes Repo (neu)                           |
| `platform`           | Referenz | `docs/adr/ADR-103`, Port-Registry ADR-021 §2.9 |
| `billing-hub`        | Sekundär | BillingHubClient-Integration (httpx)          |
| `mcp-hub`            | Sekundär | `ausschreibungs-mcp` Tool-Integration Phase 8 |

---

## Decision Drivers

- **Marktlücke**: Kein bezahlbares SaaS verbindet Ausschreibungssuche + KI-Angebotserstellung + Fördermodul für KMU
- **Branchenbreite**: IT/Beratung, Baufirmen (VOB/GAEB), Ingenieurbüros (HOAI/VgV) als Kernzielgruppen
- **Platform-Synergie**: aifw, billing-hub, platform-context, Cloudflare sind produktionsreif
- **Monetarisierung**: Tier-Modell mit KI-Nutzung als natürlichem Skalierungshebel
- **Fördermodul**: BayVFP/BMBF-Skizzen-Generator (QL 9) als USP gegenüber DTAD, cosinex

---

## 1. Context and Problem Statement

KMU, Baufirmen und Ingenieurbüros suchen Ausschreibungen manuell auf 5+ Portalen.
Angebote entstehen in Word/Excel ohne KI-Unterstützung. Branchenspezifische Pflichtinhalte
(GAEB-LV, HOAI-Honorartafel, VgV-Bewertungsmatrix) werden manuell befüllt.

Bestehende Lösungen (DTAD >500 EUR/Monat) sind zu teuer für KMU oder nicht KI-gestützt.

| Branche            | Portale                    | Besonderheiten                                              |
|--------------------|----------------------------|-------------------------------------------------------------|
| **IT / Beratung**  | DTVP, TED, service.bund.de | EVB-IT-Verträge, Eignungskriterien, Referenznachweise       |
| **Baufirmen**      | Vergabe24, subreport, DTVP | VOB/A, GAEB-LV normalisiert, Nachunternehmer, Bürgschaften  |
| **Ingenieurbüros** | evergabe.de, TED           | HOAI 2021-Honorartafel, VgV-Verfahren, LP 1–9               |
| **Forschung**      | BayVFP, BMBF, EU Horizon   | Förderskizzen, Konsortien, Arbeitspakete                    |

---

## 2. Considered Options

### Option A: Eigenes Repo `ausschreibungs-hub` (Django 5.x + DRF + aifw) ✅
**Pros:** Volle iil-Stack-Integration, Multi-Tenant RLS, eigenständiger Deploy  
**Cons:** ~16 Wochen MVP, Branchenexpertise (VOB/HOAI/GAEB) erforderlich

### Option B: Erweiterung von coach-hub
**Abgelehnt** — Domänenkonfusion, Single-Responsibility-Verletzung

### Option C: Low-Code/No-Code
**Abgelehnt** — keine aifw-Integration, kein Multi-Tenant, Dead-End für Enterprise

---

## 3. Pros and Cons of the Options

### Option A (gewählt)
- ✅ Vollständige iil-Stack-Nutzung (platform-context, aifw, billing-hub)
- ✅ Branchenmodule sauber als Django-Apps isoliert
- ✅ pgvector HNSW-Index nativ in PostgreSQL
- ✅ Enterprise-REST-API (DRF) und MCP-Integration nativ möglich
- ⚠️ Größter initialer Invest (~16 Wochen MVP)

### Option B — coach-hub-Erweiterung
- ❌ Domänenkonfusion, keine branchenspezifische Modellierung

### Option C — Low-Code
- ✅ Schnellster Prototyp (2–3 Wochen)
- ❌ Keine aifw-Integration, Dead-End für Enterprise

---

## 4. Decision Outcome

**Gewählt: Option A** — Eigenständiges Django 5.x-Projekt (<6.0) mit branchenspezifischen Apps,
KI-gestützter Angebotsgenerierung via aifw, Fördermodul.
Multi-Tenancy via `tenant_id = BigIntegerField` (ADR-007/072). Billing via billing-hub (ADR-062).

---

## 5. Implementation Details

### 5.1 Infrastruktur-Parameter (ADR-021 konform)

| Parameter        | Wert                                          |
|------------------|-----------------------------------------------|
| **Repo**         | `achimdehnert/ausschreibungs-hub` (private)   |
| **Port**         | 8095 (in ADR-021 §2.9 registriert)            |
| **Domain**       | `ausschreibungen.iil.pet` (Cloudflare Proxy)  |
| **Deploy-Path**  | `/opt/ausschreibungs-hub`                     |
| **Container**    | `ausschreibungs_hub_web`, `_worker`, `_beat`  |
| **Network**      | `bf_platform_prod`                            |
| **Python**       | 3.12                                          |
| **Django**       | **5.x (<6.0)** (Platform-Standard)            |
| **DB**           | PostgreSQL 16 + pgvector Extension            |
| **Cache**        | Redis 7                                       |

### 5.2 App-Struktur

```
ausschreibungs-hub/
├── catalog-info.yaml
├── config/settings/{base,development,production}.py
├── apps/
│   ├── core/           # TenantUser, TenantSettings, TenantBranding
│   ├── ausschreibungen/ # Portal-Adapter, Classifier, Matching
│   ├── angebote/       # Angebot, AngebotAbschnitt, Generator
│   ├── referenzen/     # Referenzprojekt (pgvector VectorField + HNSW)
│   ├── foerderung/     # Foerderprojekt, Konsortialpartner
│   ├── compliance/     # ComplianceCheck, Eignungsprüfung
│   ├── branchen/
│   │   ├── bau/        # LVPosition (GAEB norm.), Nachunternehmer, Bürgschaft
│   │   ├── ingenieur/  # HOAIHonorarBerechnung, VgVKriterium, Projektmitglied
│   │   └── it_beratung/ # EVB-IT, Referenznachweis
│   ├── api/            # REST API v1 (DRF + drf-spectacular)
│   ├── notifications/  # Webhooks via Outbox (ADR-028)
│   └── reporting/      # Dashboard, Win/Loss-Analytics
├── locale/de/ locale/en/
└── pyproject.toml
```


### 5.3 Datenmodell — Core (ADR-007/072: kein lokales Tenant-Modell)

**Fundamentales Platform-Prinzip:** Alle User-Data-Modelle tragen
`tenant_id = BigIntegerField(db_index=True)` direkt — kein FK auf ein lokales Tenant-Objekt.

```python
# apps/core/models.py
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class BranchenTyp(models.TextChoices):
    IT_BERATUNG = 'it_beratung', _('IT & Beratung')
    BAU         = 'bau',         _('Baufirma')
    INGENIEUR   = 'ingenieur',   _('Ingenieurbüro')
    FORSCHUNG   = 'forschung',   _('Forschung & Transfer')
    SONSTIGE    = 'sonstige',    _('Sonstige')


class PlanTyp(models.TextChoices):
    STARTER      = 'starter',      _('Starter')
    PROFESSIONAL = 'professional', _('Professional')
    ENTERPRISE   = 'enterprise',   _('Enterprise')


class TenantRole(models.TextChoices):
    OWNER   = 'owner',   _('Inhaber')
    MANAGER = 'manager', _('Projektleiter')
    EDITOR  = 'editor',  _('Bearbeiter')
    VIEWER  = 'viewer',  _('Leser')


class TenantUser(models.Model):
    id         = models.BigAutoField(primary_key=True)
    tenant_id  = models.BigIntegerField(db_index=True)   # <- kein FK, ADR-072
    user       = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    role       = models.CharField(max_length=20, choices=TenantRole.choices)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant_id', 'user'],
                name='tenantuser_unique_per_tenant',
            )
        ]


class TenantSettings(models.Model):
    tenant_id          = models.BigIntegerField(primary_key=True)
    branche            = models.CharField(max_length=30, choices=BranchenTyp.choices)
    plan               = models.CharField(max_length=20, choices=PlanTyp.choices,
                                          default=PlanTyp.STARTER)
    preferred_language = models.CharField(max_length=10, default='de')
    currency           = models.CharField(max_length=3, default='EUR')
    updated_at         = models.DateTimeField(auto_now=True)


class TenantBranding(models.Model):
    """White-Label-Konfiguration fuer Enterprise-Tenants (ADR-049)."""
    tenant_id     = models.BigIntegerField(unique=True)
    logo_url      = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, default='#1E3A5F')
    company_name  = models.CharField(max_length=200, blank=True)
    custom_domain = models.CharField(max_length=253, blank=True, db_index=True)
    support_email = models.EmailField(blank=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['custom_domain'],
                condition=models.Q(custom_domain__gt=''),
                name='tenantbranding_custom_domain_unique_nonempty',
            )
        ]
```

### 5.4 Datenmodell — Ausschreibungen

```python
# apps/ausschreibungen/models.py
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Portal(models.Model):
    name                 = models.CharField(max_length=200)
    adapter_class        = models.CharField(max_length=200)
    scraping_legal_basis = models.CharField(max_length=30, choices=[
        ('api',                  _('Offizielle API')),
        ('rss',                  _('RSS-Feed (oeffentlich)')),
        ('scraping_tos_checked', _('Scraping -- ToS geprueft')),
        ('scraping_legal_grey',  _('Scraping -- rechtlich unklar')),
    ])
    robots_txt_compliant = models.BooleanField(default=True)
    branchen             = models.JSONField(default=list)
    is_active            = models.BooleanField(default=True, db_index=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.is_active and not self.robots_txt_compliant:
            raise ValidationError(_('Aktive Portale muessen robots_txt_compliant=True sein.'))

    def __str__(self) -> str:
        return self.name


class Ausschreibung(models.Model):
    id               = models.BigAutoField(primary_key=True)
    public_id        = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    tenant_id        = models.BigIntegerField(db_index=True)
    portal           = models.ForeignKey(Portal, on_delete=models.PROTECT, null=True, blank=True)

    titel            = models.CharField(max_length=500)
    titel_en         = models.CharField(max_length=500, blank=True)
    zusammenfassung  = models.TextField(blank=True)
    vergabestelle    = models.CharField(max_length=300, blank=True)
    deadline         = models.DateTimeField(null=True, blank=True, db_index=True)
    original_url     = models.URLField(max_length=2000, blank=True)
    external_id      = models.CharField(max_length=300, blank=True, db_index=True)
    sprache_original = models.CharField(max_length=10, default='de')

    relevanz_score   = models.FloatField(default=0.0, db_index=True)
    cpv_codes        = models.JSONField(default=list)
    branche          = models.CharField(max_length=30, choices=BranchenTyp.choices,
                                        blank=True, db_index=True)
    vergabeart       = models.CharField(max_length=50, blank=True, choices=[
        ('offen',       _('Offenes Verfahren')),
        ('nicht_offen', _('Nicht offenes Verfahren')),
        ('verhandlung', _('Verhandlungsverfahren')),
        ('vgv',         _('VgV')),
        ('uvgo',        _('UVgO')),
        ('sektvo',      _('SektVO')),
    ])
    vergabeordnung   = models.CharField(max_length=20, blank=True,
                       choices=[('vob','VOB'),('vol','VOL'),('vgv','VgV'),
                                ('uvgo','UVgO'),('sektvo','SektVO')])
    schaetzwert      = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    waehrung         = models.CharField(max_length=3, default='EUR')
    lose             = models.JSONField(default=list)

    # BinaryField als Platzhalter bis Migration 0002_pgvector:
    # AlterField -> VectorField(dimensions=1536, null=True) + HNSW-Index
    embedding        = models.BinaryField(null=True, blank=True)

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)
    deleted_at       = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id', 'relevanz_score']),
            models.Index(fields=['tenant_id', 'deadline']),
            models.Index(fields=['tenant_id', 'branche']),
            models.Index(fields=['tenant_id', 'deleted_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant_id', 'portal', 'external_id'],
                name='ausschreibung_unique_per_tenant_portal',
                condition=models.Q(deleted_at__isnull=True),
            )
        ]
```

### 5.5 Datenmodell — Angebote

```python
# apps/angebote/models.py
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class AngebotStatus(models.TextChoices):
    ENTWURF        = 'entwurf',        _('Entwurf')
    IN_REVIEW      = 'in_review',      _('In Pruefung')
    FREIGEGEBEN    = 'freigegeben',    _('Freigegeben')
    EINGEREICHT    = 'eingereicht',    _('Eingereicht')
    ZURUECKGEZOGEN = 'zurueckgezogen', _('Zurueckgezogen')


class AngebotErgebnis(models.TextChoices):
    AUSSTEHEND  = 'ausstehend',  _('Ausstehend')
    GEWONNEN    = 'gewonnen',    _('Gewonnen')
    VERLOREN    = 'verloren',    _('Verloren')
    ABGEBROCHEN = 'abgebrochen', _('Abgebrochen')


class Angebot(models.Model):
    id                = models.BigAutoField(primary_key=True)
    public_id         = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    tenant_id         = models.BigIntegerField(db_index=True)
    ausschreibung     = models.ForeignKey('ausschreibungen.Ausschreibung',
                                          on_delete=models.PROTECT, related_name='angebote')
    erstellt_von      = models.ForeignKey('core.TenantUser',
                                          on_delete=models.SET_NULL, null=True, blank=True)
    version           = models.PositiveIntegerField(default=1)
    status            = models.CharField(max_length=20, choices=AngebotStatus.choices,
                                         default=AngebotStatus.ENTWURF, db_index=True)
    ergebnis          = models.CharField(max_length=20, choices=AngebotErgebnis.choices,
                                         default=AngebotErgebnis.AUSSTEHEND)
    gesamtpreis_netto = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)
    deleted_at        = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['ausschreibung', 'version'],
                                    name='angebot_version_unique')
        ]
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'deleted_at']),
        ]

    def __str__(self) -> str:
        return f"Angebot #{self.id} v{self.version} ({self.status})"


class AngebotAbschnitt(models.Model):
    """Versionierter Abschnitt mit Multi-User-Edit-Tracking."""
    angebot      = models.ForeignKey(Angebot, on_delete=models.CASCADE,
                                     related_name='abschnitte')
    tenant_id    = models.BigIntegerField(db_index=True)
    typ          = models.CharField(max_length=50, choices=[
        ('leistungsbeschreibung', _('Leistungsbeschreibung')),
        ('preis',                 _('Preisblatt')),
        ('referenzen',            _('Referenzen')),
        ('eignungsnachweis',      _('Eignungsnachweis')),
        ('teamvorstellung',       _('Teamvorstellung')),
    ], db_index=True)
    titel        = models.CharField(max_length=300)
    inhalt       = models.TextField(blank=True)
    ki_generiert = models.BooleanField(default=False)
    modified_by  = models.ForeignKey('core.TenantUser', on_delete=models.SET_NULL,
                                      null=True, blank=True)
    modified_at  = models.DateTimeField(auto_now=True)
    deleted_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['tenant_id', 'angebot', 'typ'])]
```

### 5.6 Datenmodell — Branchenmodelle (normalisiert)

```python
# apps/branchen/bau/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _


class GAEBEbene(models.TextChoices):
    LOS       = 'los',       _('Los')
    ABSCHNITT = 'abschnitt', _('Abschnitt')
    TITEL     = 'titel',     _('Titel')
    POSITION  = 'position',  _('Position')


class LVPosition(models.Model):
    """Normalisiertes GAEB-LV (DA83/DA84). Hierarchie via parent."""
    angebot      = models.ForeignKey('angebote.Angebot', on_delete=models.CASCADE,
                                     related_name='lv_positionen')
    tenant_id    = models.BigIntegerField(db_index=True)
    gaeb_oa_nr   = models.CharField(max_length=20)
    kurztext     = models.CharField(max_length=500)
    langtext     = models.TextField(blank=True)
    einheit      = models.CharField(max_length=20)
    menge        = models.DecimalField(max_digits=14, decimal_places=3)
    einzelpreis  = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    ebene        = models.CharField(max_length=10, choices=GAEBEbene.choices, db_index=True)
    parent       = models.ForeignKey('self', null=True, blank=True,
                                     on_delete=models.CASCADE, related_name='kinder')
    ki_generiert = models.BooleanField(default=False)

    @property
    def gesamtpreis(self):
        if self.einzelpreis is not None:
            return self.menge * self.einzelpreis
        return None

    class Meta:
        ordering = ['gaeb_oa_nr']
        indexes  = [models.Index(fields=['tenant_id', 'angebot', 'gaeb_oa_nr'])]

    def __str__(self) -> str:
        return f"{self.gaeb_oa_nr}: {self.kurztext[:60]}"


class Nachunternehmer(models.Model):
    angebot        = models.ForeignKey('angebote.Angebot', on_delete=models.CASCADE,
                                       related_name='nachunternehmer')
    tenant_id      = models.BigIntegerField(db_index=True)
    firma          = models.CharField(max_length=300)
    gewerk         = models.CharField(max_length=200)
    anteil_prozent = models.DecimalField(max_digits=5, decimal_places=2)
    bestaetigt     = models.BooleanField(default=False)


class Buergschaft(models.Model):
    angebot    = models.ForeignKey('angebote.Angebot', on_delete=models.CASCADE,
                                   related_name='buergschaften')
    tenant_id  = models.BigIntegerField(db_index=True)
    typ        = models.CharField(max_length=30, choices=[
        ('vertragserfuellung', _('Vertragserfuellung')),
        ('gewaehrleistung',    _('Gewaehrleistung')),
        ('anzahlung',          _('Anzahlung')),
    ])
    hoehe      = models.DecimalField(max_digits=14, decimal_places=2)
    faellig_am = models.DateField(null=True, blank=True)


# apps/branchen/ingenieur/models.py
from django.contrib.postgres.fields import ArrayField


class HOAIHonorarBerechnung(models.Model):
    """Rechtsverbindliche HOAI 2021-Kalkulation."""
    angebot              = models.OneToOneField('angebote.Angebot', on_delete=models.CASCADE,
                                                related_name='hoai_berechnung')
    tenant_id            = models.BigIntegerField(db_index=True)
    anrechenbare_kosten  = models.DecimalField(max_digits=14, decimal_places=2)
    honorarzone          = models.CharField(max_length=5, choices=[
        ('I','Zone I'), ('II','Zone II'), ('III','Zone III'), ('IV','Zone IV'), ('V','Zone V'),
    ])
    leistungsphasen      = ArrayField(
        models.IntegerField(choices=[(i, f'LP {i}') for i in range(1, 10)]),
        blank=True, default=list,
    )
    honorar_von          = models.DecimalField(max_digits=14, decimal_places=2)
    honorar_bis          = models.DecimalField(max_digits=14, decimal_places=2)
    honorar_interpoliert = models.DecimalField(max_digits=14, decimal_places=2)
    hoai_version         = models.CharField(max_length=15, default='HOAI 2021')
    disclaimer_accepted  = models.BooleanField(default=False)
    berechnet_am         = models.DateTimeField(auto_now=True)


class VgVKriterium(models.Model):
    angebot      = models.ForeignKey('angebote.Angebot', on_delete=models.CASCADE,
                                     related_name='vgv_kriterien')
    tenant_id    = models.BigIntegerField(db_index=True)
    kriterium    = models.CharField(max_length=300)
    gewichtung   = models.DecimalField(max_digits=5, decimal_places=2)
    antwort      = models.TextField(blank=True)
    ki_generiert = models.BooleanField(default=False)
    modified_at  = models.DateTimeField(auto_now=True)


class Projektmitglied(models.Model):
    angebot       = models.ForeignKey('angebote.Angebot', on_delete=models.CASCADE,
                                      related_name='projektteam')
    tenant_id     = models.BigIntegerField(db_index=True)
    name          = models.CharField(max_length=200)
    rolle         = models.CharField(max_length=100)
    qualifikation = models.TextField(blank=True)
```

### 5.7 Datenmodell — Foerderung, Compliance, Referenzen

```python
# apps/foerderung/models.py
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class FoerderStatus(models.TextChoices):
    VORBEREITUNG  = 'vorbereitung',  _('Vorbereitung')
    SKIZZE        = 'skizze',        _('Skizze eingereicht')
    ANTRAG        = 'antrag',        _('Vollantrag')
    BEWILLIGT     = 'bewilligt',     _('Bewilligt')
    ABGELEHNT     = 'abgelehnt',     _('Abgelehnt')
    ABGESCHLOSSEN = 'abgeschlossen', _('Abgeschlossen')


class Foerderprojekt(models.Model):
    id               = models.BigAutoField(primary_key=True)
    public_id        = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    tenant_id        = models.BigIntegerField(db_index=True)
    ausschreibung    = models.ForeignKey('ausschreibungen.Ausschreibung',
                                         on_delete=models.PROTECT, related_name='foerderprojekte')
    foerderprogramm  = models.CharField(max_length=20, db_index=True, choices=[
        ('bayvfp', 'BayVFP'), ('bmbf', 'BMBF'),
        ('eu_horizon', 'EU Horizon'), ('sonstig', _('Sonstig')),
    ])
    projekttitel     = models.CharField(max_length=300)
    status           = models.CharField(max_length=20, choices=FoerderStatus.choices,
                                        default=FoerderStatus.VORBEREITUNG, db_index=True)
    beantragte_summe = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bewilligte_summe = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    skizze_text      = models.TextField(blank=True)
    ki_generiert     = models.BooleanField(default=False)
    eingereicht_am   = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)
    deleted_at       = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['tenant_id', 'foerderprogramm']),
        ]

    def __str__(self) -> str:
        return f"{self.projekttitel} ({self.foerderprogramm})"


class Konsortialpartner(models.Model):
    foerderprojekt  = models.ForeignKey(Foerderprojekt, on_delete=models.CASCADE,
                                        related_name='konsortialpartner')
    tenant_id       = models.BigIntegerField(db_index=True)
    organisation    = models.CharField(max_length=300)
    bundesland      = models.CharField(max_length=100, blank=True)
    rolle           = models.CharField(max_length=20, choices=[
        ('koordinator', _('Koordinator')),
        ('partner',     _('Partner')),
        ('assoziiert',  _('Assoziierter Partner')),
    ])
    foerderquote    = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ansprechpartner = models.CharField(max_length=200, blank=True)
    bestaetigt_am   = models.DateTimeField(null=True, blank=True)


# apps/compliance/models.py
class ComplianceTyp(models.TextChoices):
    EIGNUNG    = 'eignung',    _('Eignungspruefung')
    NIS2       = 'nis2',       _('NIS-2-Compliance')
    DSGVO      = 'dsgvo',      _('DSGVO-Pruefung')
    TARIFTREUE = 'tariftreue', _('Tariftreue-Erklaerung')
    REFERENZ   = 'referenz',   _('Referenznachweis')


class ComplianceStatus(models.TextChoices):
    OFFEN    = 'offen',    _('Offen')
    ERFUELLT = 'erfuellt', _('Erfuellt')
    KRITISCH = 'kritisch', _('Kritisch')
    ABGELEHNT = 'abgelehnt', _('Abgelehnt')


class ComplianceCheck(models.Model):
    """Eignungs- und Compliance-Pruefung pro Angebot."""
    angebot      = models.ForeignKey('angebote.Angebot', on_delete=models.CASCADE,
                                     related_name='compliance_checks')
    tenant_id    = models.BigIntegerField(db_index=True)
    typ          = models.CharField(max_length=20, choices=ComplianceTyp.choices, db_index=True)
    status       = models.CharField(max_length=20, choices=ComplianceStatus.choices,
                                    default=ComplianceStatus.OFFEN, db_index=True)
    beschreibung = models.TextField(blank=True)
    ki_generiert = models.BooleanField(default=False)
    geprueft_von = models.ForeignKey('core.TenantUser', on_delete=models.SET_NULL,
                                      null=True, blank=True)
    geprueft_am  = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['tenant_id', 'angebot', 'status'])]


# apps/referenzen/models.py
import uuid
class Referenzprojekt(models.Model):
    id                  = models.BigAutoField(primary_key=True)
    public_id           = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    tenant_id           = models.BigIntegerField(db_index=True)
    auftraggeber        = models.CharField(max_length=300)
    projektbeschreibung = models.TextField()
    branche             = models.CharField(max_length=30, choices=BranchenTyp.choices, db_index=True)
    volumen             = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    themen              = models.JSONField(default=list)
    abgeschlossen_am    = models.DateField(null=True, blank=True)
    embedding           = models.BinaryField(null=True, blank=True)  # -> VectorField Migration 0002
    created_at          = models.DateTimeField(auto_now_add=True)
    deleted_at          = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=['tenant_id', 'branche'])]

    def __str__(self) -> str:
        return f"{self.auftraggeber}: {self.projektbeschreibung[:60]}"
```

**Migration 0002_pgvector** (Phase 6 — nach `CREATE EXTENSION pgvector` auf Server):
```python
from pgvector.django import VectorField

# AlterField: Ausschreibung.embedding -> VectorField(dimensions=1536, null=True)
# AlterField: Referenzprojekt.embedding -> VectorField(dimensions=1536, null=True)
# RunSQL: CREATE INDEX ON ausschreibungen_ausschreibung
#           USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)
# RunSQL: CREATE INDEX ON referenzen_referenzprojekt
#           USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)
```

### 5.8 KI-Integration via aifw (ADR-095/096/097)

```python
# apps/angebote/services/generator.py
import logging
from aifw.routing import get_quality_context, route_llm_call
from platform_context.audit import emit_audit_event

logger = logging.getLogger(__name__)


class AngebotGeneratorService:
    """Service-Layer -- keinerlei Geschaeftslogik in Views (ADR-007)."""

    def generate_abschnitt(
        self,
        angebot: 'Angebot',
        abschnitt_typ: str,
        tenant_id: int,
        user_id: int,
        plan_code: str,
        branche: str,
    ) -> str:
        prompt_builder = self._get_prompt_builder(branche, abschnitt_typ)
        prompt = prompt_builder.build(angebot)
        ctx = get_quality_context(
            use_case=f'{branche}_{abschnitt_typ}',
            tenant_id=tenant_id,
            plan_code=plan_code,
        )
        result = route_llm_call(ctx, prompt)
        emit_audit_event(
            event_type='angebot.ki_generated',
            tenant_id=tenant_id,
            user_id=user_id,
            object_type='AngebotAbschnitt',
            object_id=str(angebot.public_id),
            metadata={
                'quality_level': ctx.quality_level,
                'model_used':    ctx.resolved_model,
                'tokens_used':   result.tokens,
                'branche':       branche,
                'abschnitt':     abschnitt_typ,
            },
        )
        logger.info(
            "[AngebotGenerator] tenant=%d angebot=%s branche=%s ql=%d tokens=%d",
            tenant_id, angebot.public_id, branche, ctx.quality_level, result.tokens,
        )
        return result.content

    def _get_prompt_builder(self, branche: str, abschnitt_typ: str):
        BUILDERS = {
            ('bau',         'leistungsverzeichnis'):  BauLVPromptBuilder,
            ('bau',         'nachunternehmer'):        BauNachunternehmerPromptBuilder,
            ('ingenieur',   'hoai_honorar'):           IngenieurHOAIPromptBuilder,
            ('ingenieur',   'vgv_kriterien'):          IngenieurVgVPromptBuilder,
            ('it_beratung', 'leistungsbeschreibung'):  ITLeistungPromptBuilder,
            ('forschung',   'foerderskizze'):          FoerderSkizzePromptBuilder,
        }
        return BUILDERS.get((branche, abschnitt_typ), GenericPromptBuilder)()
```

**KI-Use-Cases und Quality-Level:**

| Use-Case                          |  QL | Starter    | Professional | Enterprise  |
|-----------------------------------|----:|------------|--------------|-------------|
| Relevanz-Klassifizierung          |   4 | 50/Monat   | 500/Monat    | Unbegrenzt  |
| Titel-Uebersetzung EN (Auto)      |   3 | Auto       | Auto         | Auto        |
| Angebots-Zusammenfassung          |   5 | --         | yes          | yes         |
| Leistungsbeschreibung generieren  |   7 | --         | yes          | yes         |
| GAEB-LV ausfuellen (Bau)          |   7 | --         | yes          | yes         |
| HOAI-Honorar berechnen (Ing.)     |   6 | --         | yes          | yes         |
| VgV-Kriterien beantworten (Ing.)  |   7 | --         | yes          | yes         |
| Compliance-Check (Eignung)        |   5 | --         | yes          | yes         |
| Referenz-Matching (pgvector RAG)  |   5 | --         | yes          | yes         |
| Foerderskizze BayVFP/BMBF (15 S.) |   9 | --         | yes          | yes         |

**SubscriptionTierConfig (Migration `0003_aifw_tier_configs.py`):**

```python
TIER_CONFIGS = [
    ('relevanz_klassifizierung',     4, 'starter'),
    ('relevanz_klassifizierung',     4, 'professional'),
    ('relevanz_klassifizierung',     4, 'enterprise'),
    ('bau_leistungsverzeichnis',     7, 'professional'),
    ('bau_leistungsverzeichnis',     7, 'enterprise'),
    ('ingenieur_hoai_honorar',       6, 'professional'),
    ('ingenieur_hoai_honorar',       6, 'enterprise'),
    ('ingenieur_vgv_kriterien',      7, 'professional'),
    ('ingenieur_vgv_kriterien',      7, 'enterprise'),
    ('compliance_eignungspruefung',  5, 'professional'),
    ('compliance_eignungspruefung',  5, 'enterprise'),
    ('foerderskizze_bayvfp',         9, 'professional'),
    ('foerderskizze_bayvfp',         9, 'enterprise'),
]
```

### 5.9 Portal-Adapter (Protocol-Pattern)

```python
# apps/ausschreibungen/adapters/base.py
from typing import Protocol
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class RawAusschreibung:
    external_id:   str
    titel:         str
    vergabestelle: str
    deadline:      datetime | None
    original_url:  str
    branche_hint:  str
    raw_data:      dict = field(default_factory=dict)


class PortalAdapter(Protocol):
    name:                 str
    scraping_legal_basis: str
    robots_txt_compliant: bool
    supported_branchen:   list[str]

    async def fetch_new(self, since: datetime) -> list[RawAusschreibung]: ...
    async def fetch_detail(self, external_id: str) -> dict: ...
    async def health_check(self) -> bool: ...
```

| Adapter              | `legal_basis`         | Branchen                               |
|----------------------|-----------------------|----------------------------------------|
| `DtvpAdapter`        | `api`                 | bau, ingenieur, it_beratung, forschung |
| `TedAdapter`         | `api`                 | bau, ingenieur, it_beratung, forschung |
| `ServiceBundAdapter` | `rss`                 | alle                                   |
| `Vergabe24Adapter`   | `api`                 | bau                                    |
| `SubreportAdapter`   | `api`                 | bau, ingenieur                         |
| `EvergabeAdapter`    | `scraping_tos_checked`| ingenieur, it_beratung                 |
| `IukBayernAdapter`   | `rss`                 | forschung                              |
| `BmbfAdapter`        | `rss`                 | forschung                              |
| `DtadAdapter`        | `api` (Premium)       | alle -- Enterprise only                |

### 5.10 BillingHubClient (httpx -- kein separates Package)

> **Architektur-Entscheidung:** `billing-hub` stellt kein installiertes Python-Package bereit.
> Consumer implementieren `BillingHubClient` direkt via `httpx` mit `X-Internal-Secret` Header (ADR-062).

```python
# apps/core/billing.py
import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class BillingHubClient:
    """Thin HTTP-Client gegen billing-hub REST API (ADR-062)."""

    def __init__(self) -> None:
        self._base = settings.BILLING_HUB_URL.rstrip('/')
        self._headers = {'X-Internal-Secret': settings.BILLING_INTERNAL_SECRET}

    def check_access(self, tenant_email: str, module_id: str) -> bool:
        try:
            r = httpx.get(
                f'{self._base}/api/access/ausschreibungs-hub/{tenant_email}/{module_id}/',
                headers=self._headers,
                timeout=3.0,
            )
            return r.status_code == 200 and r.json().get('has_access', False)
        except httpx.RequestError:
            logger.warning("[BillingHubClient] billing-hub nicht erreichbar -- Fallback: deny")
            return False

    def get_plan(self, tenant_email: str) -> str:
        try:
            r = httpx.get(
                f'{self._base}/api/customer/{tenant_email}/subscriptions/',
                headers=self._headers,
                timeout=3.0,
            )
            if r.status_code == 200:
                subs = r.json().get('subscriptions', [])
                return subs[0].get('tier', 'starter') if subs else 'starter'
        except httpx.RequestError:
            logger.warning("[BillingHubClient] billing-hub nicht erreichbar -- Fallback: starter")
        return 'starter'
```

### 5.11 REST API + i18n + Webhook (Ueberblick)

**REST API** (DRF + drf-spectacular, Enterprise-Tier):
```python
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'DEFAULT_THROTTLE_RATES': {
        'starter': '100/hour', 'professional': '1000/hour', 'enterprise': '10000/hour',
    },
}
# Endpunkte: /api/v1/{ausschreibungen,angebote,referenzen,foerderung}/
# OpenAPI: /api/v1/schema/swagger/
```

**i18n ab Phase 0** -- jeder String markiert, keine Nacharbeit in Phase 9:
```python
# config/settings/base.py
LANGUAGE_CODE = 'de'
USE_I18N = True
LANGUAGES = [('de', 'Deutsch'), ('en', 'English')]
LOCALE_PATHS = [BASE_DIR / 'locale']
MIDDLEWARE = [..., 'django.middleware.locale.LocaleMiddleware', ...]
```

**Webhook-Delivery** via Transactional Outbox (ADR-028):
```python
from platform_context.outbox import emit_outbox_event

emit_outbox_event(
    event_type='ausschreibung.new_match',
    tenant_id=ausschreibung.tenant_id,
    payload={'id': str(ausschreibung.public_id), 'relevanz_score': ausschreibung.relevanz_score},
)
```

### 5.12 pyproject.toml (Auszug)

```toml
[tool.poetry.dependencies]
python                         = "^3.12"
Django                         = ">=5.2,<6.0"
gunicorn                       = ">=23.0"
whitenoise                     = ">=6.8"
psycopg                        = {version = ">=3.2", extras = ["binary"]}
pgvector                       = ">=0.3.0"
celery                         = {version = ">=5.4", extras = ["redis"]}
redis                          = ">=5.2"
django-redis                   = ">=5.4"
djangorestt framework          = ">=3.15"
drf-spectacular                = ">=0.27"
djangorestt framework-simplejwt = ">=5.3"
django-htmx                    = ">=1.17"
django-tailwind-cli            = ">=2.0"
httpx                          = ">=0.28"
django-rosetta                 = ">=0.9.9"
prometheus-client              = ">=0.19"
platform-context = {git = "https://github.com/achimdehnert/platform.git", subdirectory = "packages/platform-context"}
django-logging   = {git = "https://github.com/achimdehnert/platform.git", subdirectory = "packages/django-logging"}
django-health    = {git = "https://github.com/achimdehnert/platform.git", subdirectory = "packages/django-health"}
iil-aifw         = ">=1.0.0"

[tool.poetry.dev-dependencies]
pytest         = ">=8.0"
pytest-django  = ">=4.9"
pytest-asyncio = ">=0.23"
pytest-cov     = ">=5.0"
ruff           = ">=0.4"
pip-audit      = ">=2.7"
```

### 5.13 Plan-Limits und Monetarisierung

| Feature                      | Starter (49 EUR/M) | Professional (149 EUR/M) | Enterprise (ab 499 EUR/M) |
|------------------------------|:-:|:-:|:-:|
| Portale                      | 3 | Alle | Alle + DTAD |
| Nutzer                       | 1 | 5 | Unbegrenzt |
| KI-Klassifizierungen/Monat  | 50 | 500 | Unbegrenzt |
| KI-Angebotsgenerierung       | -- | yes | yes |
| GAEB-Import/Export (Bau)     | -- | yes | yes |
| HOAI-Rechner (Ingenieur)     | Basis | Vollstaendig | Vollstaendig |
| VgV-Bewertungsmatrix         | -- | yes | yes |
| Referenzdatenbank            | 10 | 100 | Unbegrenzt |
| Compliance-Checks            | -- | yes | yes |
| Foerderskizzen-Generator     | -- | yes | yes |
| REST API + Webhooks          | -- | -- | yes |
| White-Label / Custom Domain  | -- | -- | yes |
| SLA (Reaktionszeit)          | Best-Effort | 24 h | 4 h |

---

## 6. Phasenplan

| Phase | Inhalt | Status | Woche |
|-------|--------|--------|-------|
| **0 -- Skeleton** | Repo, Docker, CI/CD, Health `/livez/`+`/healthz/`, i18n-Grundkonfiguration, `catalog-info.yaml`, Port 8095 | open | 1 |
| **1 -- Portal-Crawler** | DTVP + TED Adapter, Celery-Beat, Relevanz-Klassifizierung (QL 4) | open | 2-3 |
| **2 -- Billing + Plan-Gates** | BillingHubClient (httpx), Plan-Enforcement, Quota-Counter, Feature-Flags | open | 4 |
| **3 -- Angebots-Editor** | HTMX-Editor, AngebotAbschnitt, KI-Generierung (QL 7), Versionierung | open | 5-6 |
| **4 -- Bau-Modul** | VOB/A, LVPosition (GAEB DA83/DA84), Nachunternehmer, Buergschaft, GAEB-XML-Import | open | 7-8 |
| **5 -- Ingenieur-Modul** | HOAIHonorarBerechnung, VgVKriterium, Projektmitglied, ComplianceCheck | open | 9-10 |
| **6 -- Referenzen + RAG** | Referenzprojekt, Migration 0002_pgvector (VectorField + HNSW-Index) | open | 11 |
| **7 -- Foerdermodul** | Foerderprojekt, Konsortialpartner, BayVFP/BMBF-Skizzen-Generator (QL 9) | open | 12-13 |
| **8 -- Enterprise** | REST API (DRF), Webhooks (Outbox), TenantBranding, Audit-Trail, DTAD-Adapter | open | 14-15 |
| **9 -- i18n + Polish** | EN-Uebersetzungen, DSGVO-Data-Export `/api/v1/gdpr/export/`, Staging, Docs | open | 16 |

---

## 7. Consequences

### 7.1 Good
- Einziger Anbieter der IT, Bau, Ingenieur und Forschung + Foerdermodul verbindet
- KI-gestuetzte Angebotserstellung senkt Bearbeitungszeit um 60-80 %
- GAEB und HOAI normalisiert -- Analytics, Audit, Vergabe-Rechtskonformitaet moeglich
- pgvector HNSW in PostgreSQL -- kein externer Vektorspeicher noetig
- Vollstaendige Platform-Integration: aifw, billing-hub, platform-context, Cloudflare

### 7.2 Bad
- Hoher initialer Invest (~16 Wochen MVP)
- VOB/HOAI/GAEB Domaenwissen erforderlich
- Portal-Scraping rechtlich heikel -- API-Portale priorisieren

### 7.3 Nicht in Scope
- Elektronische Vergabe / eVergabe-Submission
- Bauzeitenplanung / Projektmanagement
- CAD/BIM-Integration (-> cad-hub)
- Eigene LLM-Modelle (aifw-Router nutzt externe Provider)

---

## 8. Risks

| Risiko                                 | W'keit | Impact | Mitigation                                                      |
|----------------------------------------|--------|--------|-----------------------------------------------------------------|
| Portal-Scraping rechtlich problematisch| Mittel | Hoch   | API-Portale priorisieren; `robots_txt_compliant` DB-Constraint  |
| GAEB-Parser-Komplexitaet              | Mittel | Mittel | Python-Libs evaluieren (gaeb, lxml); DA83 + DA84 zunaechst      |
| HOAI-Berechnungsfehler -> Vergabestreit | Niedrig| Hoch   | `disclaimer_accepted`-Pflichtfeld; Rechtshinweis im UI          |
| LLM-Kosten bei Enterprise-Scale        | Mittel | Mittel | Semantic-Cache via pgvector; aifw Semantic-Cache                |
| Angebotsdaten bei LLM-Provider (DSGVO) | Mittel | Hoch   | AVV mit Anthropic/OpenAI; EU-Region (Azure OpenAI)              |
| DSGVO Art. 35 DSFA                     | Mittel | Hoch   | Datenschutz-Folgenabschaetzung vor Go-Live in `docs/dsgvo/`     |
| pgvector-Migration Downtime            | Niedrig| Mittel | Migration 0002 vorab testen; pgvector-Extension vorab aktivieren|
| Ressourcen Hetzner-Server              | Niedrig| Mittel | Container-Limits; RAM-Monitoring; CX32-Upgrade bei Bedarf       |

---

## 9. Confirmation

1. **Health-Endpoints**: `curl -sf https://ausschreibungen.iil.pet/livez/` -> `{"status":"ok"}` und `/healthz/` -> `{"status":"ok","db":"ok","redis":"ok","celery":"ok"}`
2. **CI/CD-Standard**: `_ci-python.yml` + `_deploy-hetzner.yml` aus platform (ADR-021); Coverage >= 80 %
3. **Port-Registry**: Port 8095 in ADR-021 §2.9 vor Phase-0-Deploy registriert
4. **Kein lokales Tenant-FK**: `grep -rn "ForeignKey(Tenant" apps/` -> 0 Treffer
5. **tenant_id auf allen User-Data-Modellen**: `grep -rn "tenant_id" apps/` deckt alle Modelle
6. **public_id auf Hauptmodellen**: Ausschreibung, Angebot, Foerderprojekt, Referenzprojekt
7. **Scraping-Compliance**: `Portal.objects.filter(is_active=True, robots_txt_compliant=False).count()` -> 0
8. **i18n ab Phase 0**: `USE_I18N=True` in `base.py`; `locale/de/` und `locale/en/` im Phase-0-Commit
9. **SubscriptionTierConfig**: Migration `0003_aifw_tier_configs.py` mit 13 Eintraegen aus SS 5.8
10. **catalog-info.yaml**: Im Repo-Root mit `metadata.name`, `spec.type`, `spec.lifecycle`, `spec.owner`
11. **pgvector-Migration**: Migration 0002 mit `VectorField(1536)` + HNSW-Index fuer beide Embedding-Felder
12. **Drift-Detector**: Staleness 6 Monate; ADR-059 ueberwacht `apps/` + `pyproject.toml`

---

## 10. More Information

- `docs/adr/reviews/REVIEW-ADR-103.md` -- Review v1+v2 (Claude, Principal IT Architect)
- ADR-007: Tenant- & RBAC-Architektur | ADR-021: Deployment/Port-Registry
- ADR-027/028: platform-context (Audit, Outbox) | ADR-049: Design-Tokens
- ADR-062: billing-hub (`https://billing.iil.pet`) | ADR-072: Multi-Tenancy RLS
- ADR-077: Backstage Catalog | ADR-095/096/097: aifw Quality-Routing
- ADR-102: Cloudflare DNS/Proxy
- [DTVP API](https://www.dtvp.de/api-dokumentation) | [TED REST API v3](https://ted.europa.eu/api/v3.0)
- [GAEB DA83/DA84](https://www.gaeb.de) | [HOAI 2021](https://www.hoai.de) | [VOB/A 2019](https://www.bmwsb.bund.de)
- [pgvector Django](https://github.com/pgvector/pgvector-python)

---

## 11. Changelog

| Datum      | Autor                           | Aenderung                                                                                     |
|------------|---------------------------------|-----------------------------------------------------------------------------------------------|
| 2026-03-06 | Cascade + AD                    | v1: Initial Proposed                                                                          |
| 2026-03-06 | Claude (Principal IT Architect) | v2: 3 Blocker + 7 kritische + 6 hohe Befunde eingearbeitet                                   |
| 2026-03-07 | Cascade (Senior Architect)      | v3: Status Accepted; VectorField-Migration explizit; BillingHubClient via httpx; ComplianceCheck vollstaendig; FoerderSkizze-PromptBuilder; pgvector Confirmation-Check; pyproject.toml vollstaendig; UniqueConstraints konditionell |
| 2026-03-07 | Achim Dehnert                   | v3.1: Django >=5.2,<6.0 (Platform-Standard) -- Django 6.0 war irrtümlich eingetragen |

---

## Anhang A: Review-Befunde Behandlung (v1 -> v2 -> v3)

| Befund | Schwere | v2 | v3 |
|--------|---------|----|----||
| B-01: Django 5.1 statt 6.0 -- Zielversion 5.x (<6.0) | BLOCKER | korrigiert | yes -- >=5.2,<6.0 |
| B-02: BinaryField statt VectorField | BLOCKER | Kommentar | Migration 0002 explizit + Confirmation |
| B-03: Lokales Tenant-Modell | BLOCKER | tenant_id ueberall | yes |
| K-01: GAEB als JSONField | KRITISCH | LVPosition normalisiert | yes |
| K-02: JSONField Nachunternehmer/VgV/Team | KRITISCH | Separate Modelle | yes |
| K-03: HOAI als JSONField | KRITISCH | HOAIHonorarBerechnung | yes |
| K-04: Portal FK SET_NULL | KRITISCH | on_delete=PROTECT | yes |
| K-05: HOAI LP ohne Validation | KRITISCH | ArrayField(choices=...) | yes |
| K-06: Billing in Phase 6 | KRITISCH | Phase 2 | yes |
| K-07: i18n in Phase 9 | KRITISCH | ab Phase 0 | yes |
| H-01: Foerderprojekt fehlend | HOCH | definiert | yes |
| H-02: ComplianceCheck fehlend | HOCH | App-Referenz | vollstaendiges Modell |
| H-03: TenantBranding fehlend | HOCH | definiert | konditioneller UniqueConstraint |
| H-04: Soft-Delete fehlend | HOCH | deleted_at ueberall | yes |
| H-05: unique_together deprecated | HOCH | UniqueConstraint | yes |
| H-06: catalog-info.yaml fehlend | HOCH | in Struktur + Confirmation | yes |
| M-01: Pros/Cons-Abschnitt | MEDIUM | Abschnitt 3 | yes |
| M-02: informed leer | MEDIUM | YAML-Header | yes |
| M-03: Confirmation unvollstaendig | MEDIUM | 10 Checks | 12 Checks |
| NEU v3: billing-client unklar | -- | -- | BillingHubClient via httpx dokumentiert |
| NEU v3: pgvector Migration-Scope | -- | -- | beide Felder + beide Indizes explizit |
