"""BFA Agent Runner - Haupteinstiegspunkt."""

import asyncio
from agents import Runner, RunConfig

from .config import setup_openrouter
from .agents import triage_agent


async def run_bfa_agent(user_input: str, max_turns: int = 15) -> str:
    """Führt den BFA Agent aus.
    
    Args:
        user_input: Benutzeranfrage
        max_turns: Maximale Iterationen
        
    Returns:
        Agent-Antwort als String
    """
    result = await Runner.run(
        triage_agent,
        user_input,
        run_config=RunConfig(max_turns=max_turns)
    )
    
    return result.final_output


async def run_interactive():
    """Interaktive Konsolen-Session."""
    print("=" * 60)
    print("BFA Agent - Explosionsschutz Assistent")
    print("=" * 60)
    print("Befehle: 'quit' zum Beenden, 'help' für Hilfe")
    print()
    
    while True:
        try:
            user_input = input("Sie: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                print("Auf Wiedersehen!")
                break
            
            if user_input.lower() == "help":
                print("""
Verfügbare Funktionen:
- CAD-Analyse: "Lies die Datei anlage.ifc"
- Zonen-Klassifizierung: "Klassifiziere den Lackierraum als Ex-Zone"
- Equipment-Prüfung: "Ist II 2G Ex d IIB T4 für Zone 1 geeignet?"
- Bericht: "Erstelle einen Bericht über die Analyse"

Beispiele:
- "Analysiere einen Lackierraum mit 500m³ und Aceton"
- "Prüfe ob eine Pumpe mit Ex d für Zone 2 geeignet ist"
- "Welche Zone gilt für einen Mischraum mit natürlicher Lüftung?"
                """)
                continue
            
            print("\nBFA Agent arbeitet...\n")
            response = await run_bfa_agent(user_input)
            print(f"Agent: {response}\n")
            
        except KeyboardInterrupt:
            print("\nAbgebrochen.")
            break
        except Exception as e:
            print(f"Fehler: {e}\n")


def main():
    """CLI Einstiegspunkt."""
    # OpenRouter initialisieren
    setup_openrouter()
    
    # Interaktive Session starten
    asyncio.run(run_interactive())


if __name__ == "__main__":
    main()
