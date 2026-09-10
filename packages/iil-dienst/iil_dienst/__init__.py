"""iil-dienst — ein Dienst, zwei Zugaenge (KONZ-platform-058, platform#3011).

Ein Dienst ist eine reine Funktion im Service-Layer eines Hubs. Der Dekorator
``@dienst`` haengt den Vertrag an (Name, Datenklasse, Gate, Beschreibung) und
traegt die Funktion in die Registry ein. Die App ruft die Funktion direkt; das
Gateway ruft sie ueber ``manage.py dienst_aufruf <name>`` — dieselbe Funktion,
derselbe Vertrag.

    from iil_dienst import dienst

    @dienst("plattform-status", datenklasse="intern", gate="keins",
            beschreibung="Zustand der Plattform-Dienste")
    def plattform_status(*, mandant: str = "devhub") -> dict: ...

Konventionen:
- Eingabe nur als Schluesselwort-Argumente mit JSON-faehigen Werten.
- Ausgabe ein JSON-faehiges dict; keine Modelle, keine QuerySets.
- Datenklasse und Gate nehmen exakt die Werte des Katalogs
  (docs/konzepte/KONZ-platform-058/iil-assist.yaml).
- Personenbezogene oder Mandantendaten duerfen kein ``gate: keins`` tragen —
  der Dekorator lehnt das ab, nicht erst das Gateway.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

__version__ = "0.1.0"

DATENKLASSEN = ("oeffentlich", "intern", "personenbezogen", "mandant")
GATES = ("keins", "raum-bindung", "entwurf-freigabe", "budget")
SCHUETZENSWERT = ("personenbezogen", "mandant")


class DienstFehler(Exception):
    """Vertragsverletzung oder unbekannter Dienst — kein Laufzeitfehler des Dienstes selbst."""


@dataclass(frozen=True)
class Parameter:
    name: str
    pflicht: bool
    standard: Any = None


@dataclass
class Dienst:
    name: str
    datenklasse: str
    gate: str
    beschreibung: str
    fn: Callable[..., Any]
    modul: str
    parameter: list[Parameter] = field(default_factory=list)

    def vertrag(self) -> dict[str, Any]:
        """Der Vertrag als JSON-faehiges dict — das, was Katalog und Gateway lesen."""
        return {
            "name": self.name,
            "datenklasse": self.datenklasse,
            "gate": self.gate,
            "beschreibung": self.beschreibung,
            "modul": self.modul,
            "parameter": [asdict(p) for p in self.parameter],
        }


REGISTRY: dict[str, Dienst] = {}


def _parameter(fn: Callable[..., Any]) -> list[Parameter]:
    out = []
    for p in inspect.signature(fn).parameters.values():
        if p.kind not in (p.KEYWORD_ONLY, p.POSITIONAL_OR_KEYWORD):
            raise DienstFehler(f"{fn.__name__}: nur Schluesselwort-Argumente erlaubt, nicht {p.name!r}")
        pflicht = p.default is inspect.Parameter.empty
        out.append(Parameter(p.name, pflicht, None if pflicht else p.default))
    return out


def dienst(name: str, *, datenklasse: str, gate: str, beschreibung: str = "") -> Callable:
    """Dekorator: Vertrag anhaengen und registrieren. Die Funktion bleibt unveraendert aufrufbar."""
    if datenklasse not in DATENKLASSEN:
        raise DienstFehler(f"{name}: datenklasse {datenklasse!r} nicht in {DATENKLASSEN}")
    if gate not in GATES:
        raise DienstFehler(f"{name}: gate {gate!r} nicht in {GATES}")
    if datenklasse in SCHUETZENSWERT and gate == "keins":
        raise DienstFehler(f"{name}: {datenklasse} braucht ein Gate (Charta Art. 2)")

    def wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        if name in REGISTRY and REGISTRY[name].fn is not fn:
            raise DienstFehler(f"{name}: doppelt registriert ({REGISTRY[name].modul} und {fn.__module__})")
        REGISTRY[name] = Dienst(name, datenklasse, gate, beschreibung, fn, fn.__module__, _parameter(fn))
        return fn

    return wrap


def katalog() -> list[dict[str, Any]]:
    """Alle Vertraege, sortiert nach Name — die Export-Form fuer das Gateway."""
    return [REGISTRY[n].vertrag() for n in sorted(REGISTRY)]


def aufruf(name: str, **args: Any) -> Any:
    """Den Dienst ueber seinen Vertrag aufrufen — genau das, was die App auch tut."""
    d = REGISTRY.get(name)
    if d is None:
        raise DienstFehler(f"unbekannter Dienst {name!r}; bekannt: {sorted(REGISTRY) or '—'}")
    bekannt = {p.name for p in d.parameter}
    fremd = set(args) - bekannt
    if fremd:
        raise DienstFehler(f"{name}: unbekannte Argumente {sorted(fremd)}; erlaubt: {sorted(bekannt)}")
    fehlend = [p.name for p in d.parameter if p.pflicht and p.name not in args]
    if fehlend:
        raise DienstFehler(f"{name}: Pflichtargumente fehlen: {fehlend}")
    return d.fn(**args)


def zuruecksetzen() -> None:
    """Nur fuer Tests."""
    REGISTRY.clear()
