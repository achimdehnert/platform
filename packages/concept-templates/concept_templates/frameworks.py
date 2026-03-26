"""Vordefinierte Konzept-Frameworks (ADR-147).

Jedes Framework definiert die Standardgliederung eines Fachkonzepts.
Frameworks werden beim Import automatisch in die Registry eingetragen.
"""

from __future__ import annotations

from concept_templates.schemas import (
    ConceptScope,
    ConceptTemplate,
    FieldType,
    TemplateField,
    TemplateSection,
)

# ---------------------------------------------------------------------------
# Brandschutz nach §14 MBO
# ---------------------------------------------------------------------------

BRANDSCHUTZ_MBO = ConceptTemplate(
    name="Brandschutzkonzept §14 MBO",
    scope=ConceptScope.BRANDSCHUTZ,
    is_master=True,
    framework="brandschutz_mbo",
    framework_version="1.0",
    sections=[
        TemplateSection(
            name="standort",
            title="1. Standortbeschreibung",
            required=True,
            order=1,
            fields=[
                TemplateField(
                    name="address",
                    label="Adresse",
                    field_type=FieldType.TEXT,
                    required=True,
                ),
                TemplateField(
                    name="building_class",
                    label="Gebäudeklasse",
                    field_type=FieldType.CHOICE,
                    choices=["GK1", "GK2", "GK3", "GK4", "GK5"],
                ),
                TemplateField(
                    name="usage_type",
                    label="Nutzungsart",
                    field_type=FieldType.TEXT,
                ),
                TemplateField(
                    name="building_height_m",
                    label="Gebäudehöhe (m)",
                    field_type=FieldType.NUMBER,
                ),
                TemplateField(
                    name="floors",
                    label="Anzahl Geschosse",
                    field_type=FieldType.NUMBER,
                ),
            ],
        ),
        TemplateSection(
            name="brandabschnitte",
            title="2. Brandabschnitte",
            required=True,
            order=2,
            description="Einteilung in Brandabschnitte gem. MBO §28",
        ),
        TemplateSection(
            name="fluchtwege",
            title="3. Flucht- und Rettungswege",
            required=True,
            order=3,
            description="Gem. MBO §33-§36, ASR A2.3",
        ),
        TemplateSection(
            name="massnahmen",
            title="4. Brandschutzmaßnahmen",
            required=True,
            order=4,
            subsections=[
                TemplateSection(
                    name="baulich",
                    title="4.1 Bauliche Maßnahmen",
                    order=1,
                ),
                TemplateSection(
                    name="technisch",
                    title="4.2 Anlagentechnische Maßnahmen",
                    order=2,
                ),
                TemplateSection(
                    name="organisatorisch",
                    title="4.3 Organisatorische Maßnahmen",
                    order=3,
                ),
            ],
        ),
        TemplateSection(
            name="loescheinrichtungen",
            title="5. Löscheinrichtungen",
            required=False,
            order=5,
        ),
        TemplateSection(
            name="prueffristen",
            title="6. Prüffristen und Wartung",
            required=False,
            order=6,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Explosionsschutz nach TRGS 720ff / ATEX
# ---------------------------------------------------------------------------

EXSCHUTZ_TRGS720 = ConceptTemplate(
    name="Explosionsschutzkonzept TRGS 720ff",
    scope=ConceptScope.EXPLOSIONSSCHUTZ,
    is_master=True,
    framework="exschutz_trgs720",
    framework_version="1.0",
    sections=[
        TemplateSection(
            name="stoffdaten",
            title="1. Stoffdaten und Eigenschaften",
            required=True,
            order=1,
            fields=[
                TemplateField(
                    name="substance_name",
                    label="Stoffbezeichnung",
                    field_type=FieldType.TEXT,
                    required=True,
                ),
                TemplateField(
                    name="flash_point_c",
                    label="Flammpunkt (°C)",
                    field_type=FieldType.NUMBER,
                ),
                TemplateField(
                    name="explosion_limits",
                    label="Explosionsgrenzen (UEG/OEG)",
                    field_type=FieldType.TEXT,
                ),
                TemplateField(
                    name="dust_explosion_class",
                    label="Staubexplosionsklasse",
                    field_type=FieldType.CHOICE,
                    choices=["St 1", "St 2", "St 3"],
                ),
            ],
        ),
        TemplateSection(
            name="zoneneinteilung",
            title="2. Zoneneinteilung",
            required=True,
            order=2,
            description="Zone 0/1/2 (Gas) bzw. Zone 20/21/22 (Staub)",
        ),
        TemplateSection(
            name="zuendquellen",
            title="3. Zündquellenanalyse",
            required=True,
            order=3,
            description="Bewertung nach EN 1127-1",
        ),
        TemplateSection(
            name="primaer",
            title="4. Primärer Explosionsschutz",
            required=True,
            order=4,
            description="Vermeidung explosionsfähiger Atmosphäre",
        ),
        TemplateSection(
            name="sekundaer",
            title="5. Sekundärer Explosionsschutz",
            required=True,
            order=5,
            description="Vermeidung wirksamer Zündquellen",
        ),
        TemplateSection(
            name="konstruktiv",
            title="6. Konstruktiver Explosionsschutz",
            required=False,
            order=6,
            description="Begrenzung der Auswirkungen",
        ),
        TemplateSection(
            name="betriebsanweisungen",
            title="7. Betriebsanweisungen",
            required=False,
            order=7,
        ),
    ],
)

# ---------------------------------------------------------------------------
# Ausschreibung nach VOB/A
# ---------------------------------------------------------------------------

AUSSCHREIBUNG_VOB = ConceptTemplate(
    name="Ausschreibung nach VOB/A",
    scope=ConceptScope.AUSSCHREIBUNG,
    is_master=True,
    framework="ausschreibung_vob",
    framework_version="1.0",
    sections=[
        TemplateSection(
            name="auftraggeber",
            title="1. Auftraggeber",
            required=True,
            order=1,
            fields=[
                TemplateField(
                    name="client_name",
                    label="Name des Auftraggebers",
                    field_type=FieldType.TEXT,
                    required=True,
                ),
                TemplateField(
                    name="client_address",
                    label="Adresse",
                    field_type=FieldType.TEXT,
                ),
                TemplateField(
                    name="contact_person",
                    label="Ansprechpartner",
                    field_type=FieldType.TEXT,
                ),
            ],
        ),
        TemplateSection(
            name="leistungsbeschreibung",
            title="2. Leistungsbeschreibung",
            required=True,
            order=2,
            description="Beschreibung der ausgeschriebenen Leistung",
        ),
        TemplateSection(
            name="mengen",
            title="3. Mengen und Massen",
            required=True,
            order=3,
        ),
        TemplateSection(
            name="vertragsbedingungen",
            title="4. Vertragsbedingungen",
            required=True,
            order=4,
        ),
        TemplateSection(
            name="eignungskriterien",
            title="5. Eignungskriterien",
            required=False,
            order=5,
        ),
        TemplateSection(
            name="zuschlagskriterien",
            title="6. Zuschlagskriterien",
            required=False,
            order=6,
        ),
        TemplateSection(
            name="fristen",
            title="7. Fristen und Termine",
            required=False,
            order=7,
            fields=[
                TemplateField(
                    name="submission_deadline",
                    label="Abgabefrist",
                    field_type=FieldType.DATE,
                    required=True,
                ),
                TemplateField(
                    name="execution_start",
                    label="Ausführungsbeginn",
                    field_type=FieldType.DATE,
                ),
                TemplateField(
                    name="execution_end",
                    label="Ausführungsende",
                    field_type=FieldType.DATE,
                ),
            ],
        ),
        TemplateSection(
            name="anlagen",
            title="8. Anlagen und Nachweise",
            required=False,
            order=8,
        ),
    ],
)

# All built-in frameworks for auto-registration
BUILTIN_FRAMEWORKS: dict[str, ConceptTemplate] = {
    "brandschutz_mbo": BRANDSCHUTZ_MBO,
    "exschutz_trgs720": EXSCHUTZ_TRGS720,
    "ausschreibung_vob": AUSSCHREIBUNG_VOB,
}
