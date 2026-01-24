"""Beispiel: BFA Agent Nutzung."""

import asyncio
from bfa_agent import setup_openrouter, run_bfa_agent


async def demo():
    """Demonstriert verschiedene BFA Agent Funktionen."""
    
    # 1. OpenRouter initialisieren
    setup_openrouter()
    
    # 2. Beispiel-Anfragen
    examples = [
        # CAD-Analyse
        "Lies die Datei anlage.ifc und zeige mir alle Räume",
        
        # Zonen-Klassifizierung  
        "Klassifiziere einen Lackierraum mit 450m³, technischer Lüftung (25 Luftwechsel/h) und Aceton als Lösemittel",
        
        # Equipment-Prüfung
        "Ist ein Gerät mit Kennzeichnung 'II 2G Ex d IIB T4' für Zone 1 geeignet?",
        
        # Stoffdaten
        "Welche Eigenschaften hat Ethanol für die Ex-Zonen Beurteilung?",
    ]
    
    for i, query in enumerate(examples, 1):
        print(f"\n{'='*60}")
        print(f"Beispiel {i}: {query[:50]}...")
        print('='*60)
        
        result = await run_bfa_agent(query)
        print(f"\nErgebnis:\n{result}")
        print()


if __name__ == "__main__":
    asyncio.run(demo())
