"""Demo-App: ein Dienst, den Autodiscovery beim Start finden muss."""

from iil_dienst import dienst


@dienst("demo-summe", datenklasse="intern", gate="keins", beschreibung="Addiert zwei Zahlen")
def summe(*, a: int, b: int = 1) -> dict:
    return {"summe": a + b}
