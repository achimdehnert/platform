"""
Usage Example
=============

Beispiel für die Verwendung der Handler mit Repositories.
"""
import asyncio

from repositories import (
    DatabaseConfig,
    init_database,
    close_database,
    FireProtectionUnitOfWork,
)

from handlers import (
    ConceptAnalyzerHandler,
    ConceptAnalysisInput,
    CADAnalyzerHandler,
    CADAnalysisInput,
)


async def analyze_concept_example():
    """Beispiel: Brandschutzkonzept analysieren."""
    
    # 1. Datenbank initialisieren
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="fire_protection",
        user="postgres",
        password="your_password"
    )
    await init_database(config)
    
    try:
        # 2. Unit of Work erstellen
        async with FireProtectionUnitOfWork() as uow:
            
            # 3. Handler initialisieren
            handler = ConceptAnalyzerHandler(uow)
            
            # 4. Analyse durchführen
            result = await handler.process(ConceptAnalysisInput(
                file_path="path/to/brandschutzkonzept.pdf",
                building_class="GK4",
                usage_types=["büro", "arbeitsstätte"],
                use_llm=False  # Ohne LLM für schnellere Analyse
            ))
            
            # 5. Ergebnis verarbeiten
            if result.success:
                data = result.data
                
                print(f"✅ Analyse erfolgreich!")
                print(f"   Vollständigkeit: {data['completeness_score']:.1f}%")
                print(f"   Risiko-Score: {data['risk_score']:.1f}")
                print(f"   Gebäudeklasse: {data['building_data'].get('building_class')}")
                print(f"   Findings: {len(data['findings'])}")
                
                # Kritische Findings ausgeben
                critical = [f for f in data['findings'] if f['severity'] == 'critical']
                if critical:
                    print(f"\n⚠️ Kritische Befunde:")
                    for finding in critical:
                        print(f"   - {finding['title']}")
                        print(f"     {finding['description']}")
                
            else:
                print(f"❌ Fehler: {result.error}")
    
    finally:
        await close_database()


async def analyze_cad_example():
    """Beispiel: CAD-Plan analysieren."""
    
    await init_database(DatabaseConfig.from_env())
    
    try:
        async with FireProtectionUnitOfWork() as uow:
            
            # Handler mit ODA Converter Path
            handler = CADAnalyzerHandler(
                uow,
                oda_converter_path="/opt/ODAFileConverter/ODAFileConverter"
            )
            
            result = await handler.process(CADAnalysisInput(
                file_path="path/to/grundriss.dwg",
                building_class="GK3",
                scale=1.0,  # 1:1
                unit="mm"
            ))
            
            if result.success:
                data = result.data
                
                print(f"✅ CAD-Analyse erfolgreich!")
                print(f"   Layer gefunden: {len(data['layers_found'])}")
                print(f"   Vollständigkeit: {data['completeness_score']:.1f}%")
                
                # Elemente ausgeben
                print(f"\n📊 Gefundene Elemente:")
                for elem_type, count in data['elements'].items():
                    if count > 0:
                        print(f"   {elem_type}: {count}")
                
                # Fluchtwege
                routes = data['escape_routes']
                if routes.get('max_length'):
                    print(f"\n🚪 Fluchtwege:")
                    print(f"   Max. Länge: {routes['max_length']:.1f}m")
                    print(f"   Anzahl Pfade: {routes['paths_count']}")
                
                # Findings
                if data['findings']:
                    print(f"\n⚠️ Befunde ({len(data['findings'])}):")
                    for finding in data['findings'][:5]:
                        print(f"   [{finding['severity']}] {finding['title']}")
            
            else:
                print(f"❌ Fehler: {result.error}")
    
    finally:
        await close_database()


async def query_database_example():
    """Beispiel: Direkte DB-Abfragen."""
    
    await init_database(DatabaseConfig.from_env())
    
    try:
        async with FireProtectionUnitOfWork() as uow:
            
            # Alle aktiven Normen laden
            norms = await uow.norms.get_active_norms()
            print(f"📚 {len(norms)} Normen in Datenbank:")
            for norm in norms[:5]:
                print(f"   {norm.code}: {norm.name}")
            
            # Anforderungen für Gebäudeklasse GK4
            requirements = await uow.norms.get_applicable_requirements(
                building_class="GK4",
                usages=["arbeitsstätte"]
            )
            print(f"\n📋 {len(requirements)} Anforderungen für GK4 + Arbeitsstätte:")
            for req in requirements[:5]:
                print(f"   {req.code}: {req.title}")
            
            # Checkliste laden
            checklist = await uow.checklists.get_by_code("standard_brandschutz_konzept")
            if checklist:
                print(f"\n✓ Checkliste: {checklist.name}")
                print(f"  Items: {len(checklist.items)}")
                
                # Kategorien
                categories = await uow.checklists.get_categories("standard_brandschutz_konzept")
                print(f"  Kategorien: {', '.join(categories)}")
            
            # Prompt-Template laden
            prompt = await uow.prompts.get_by_code("concept_analysis_v1")
            if prompt:
                print(f"\n💬 Prompt Template: {prompt.name}")
                print(f"   Typ: {prompt.template_type}")
                print(f"   Variablen: {prompt.required_variables}")
            
            # Analyzer-Config laden
            config = await uow.analyzers.get_by_code("cad_parser_v1")
            if config:
                print(f"\n⚙️ Analyzer: {config.name}")
                print(f"   Patterns: {len(config.extraction_patterns)} Felder")
                if config.cad_mappings:
                    layers = config.cad_mappings.get("layer_categories", {})
                    print(f"   Layer-Kategorien: {', '.join(layers.keys())}")
            
            # Severity-Werte laden
            severities = await uow.lookups.get_values_as_dict("severity")
            print(f"\n🔴 Severity-Level:")
            for code, info in severities.items():
                icon = info['config'].get('icon', '•')
                print(f"   {icon} {code}: {info['name']}")
    
    finally:
        await close_database()


if __name__ == "__main__":
    print("=" * 60)
    print("Fire Protection Analysis Examples")
    print("=" * 60)
    
    # Wähle Beispiel
    import sys
    
    if len(sys.argv) > 1:
        example = sys.argv[1]
        
        if example == "concept":
            asyncio.run(analyze_concept_example())
        elif example == "cad":
            asyncio.run(analyze_cad_example())
        elif example == "query":
            asyncio.run(query_database_example())
        else:
            print(f"Unknown example: {example}")
    else:
        print("\nUsage:")
        print("  python example_usage.py concept  # Konzept-Analyse")
        print("  python example_usage.py cad      # CAD-Analyse")
        print("  python example_usage.py query    # DB-Abfragen")
