#!/usr/bin/env python3
"""Pruef-Spike platform#3650: Logit-Scoring gegen Text-Klassifikation auf der gx10.

Drei Wege, dieselbe Entscheidung (Mail-Kategorie, vier Klassen):

  text   Ollama qwen2.5:7b erzeugt ein Wort, das Wort wird geparst — der heutige Weg.
  logit  Dasselbe Modell, derselbe Prompt, aber nur EIN Token (num_predict=1) mit
         `logprobs` + `top_logprobs=20`. Die Wahrscheinlichkeiten der Tokens, die ein
         Label-Praefix sind, werden je Label summiert und nur ueber die Labels neu
         normiert (restricted softmax, SGLang-/v1/score-Muster nachgebildet).
  kev    kev-4b (`/v1/systemone`, Frage vom Typ `choice`) — der bereits laufende
         Entscheidungsdienst aus platform#3337, der das Muster serverseitig macht.

Laeuft AUF der gx10 (kev lauscht nur auf 127.0.0.1), stdlib-only, Ausgabe JSONL:

  ssh hetzner-prod "ssh adehnert@10.99.0.4 python3 -" < spikes/logit-scoring/messung.py

Die Mails sind erfunden (keine echten Absender, Namen oder Anschriften).
Schutz fuer die geteilte gx10: num_predict immer begrenzt, Client-Timeout,
am Ende keep_alive=0 (siehe Ollama-Runaway 2026-09-24).
"""

from __future__ import annotations

import json
import math
import time
import urllib.request

OLLAMA = "http://10.99.0.4:11434/api/generate"
KEV = "http://127.0.0.1:8009/v1/systemone"
MODELL = "qwen2.5:7b"
RUNDEN = 3
TIMEOUT_S = 60

LABELS = {
    "rechnung": "Rechnung, Quittung oder Zahlungsbeleg",
    "termin": "Terminvorschlag, Einladung oder Terminverschiebung",
    "newsletter": "Newsletter, Werbung oder Rundschreiben",
    "anfrage": "fachliche Anfrage oder Auftragsanfrage eines Kunden",
}

#: (Gold, Mailtext) — erfunden; je Klasse drei Faelle, einer davon absichtlich unscharf.
FAELLE = [
    (
        "rechnung",
        "Betreff: Rechnung RE-2026-0815\nAnbei erhalten Sie unsere Rechnung fuer September. Zahlbar innerhalb von 14 Tagen.",
    ),
    (
        "rechnung",
        "Betreff: Ihre Zahlungsbestaetigung\nVielen Dank fuer Ihre Zahlung von 49,00 EUR. Den Beleg finden Sie im Anhang.",
    ),
    (
        "rechnung",
        "Betreff: Abo verlaengert\nIhr Jahresabo wurde verlaengert. Der Betrag von 120 EUR wurde abgebucht, Beleg anbei.",
    ),
    (
        "termin",
        "Betreff: Abstimmung naechste Woche\nPasst Ihnen Dienstag 10 Uhr fuer eine kurze Abstimmung per Video?",
    ),
    (
        "termin",
        "Betreff: Verschiebung Workshop\nWir muessen den Workshop vom 12. auf den 19. Oktober verschieben. Bitte kurz bestaetigen.",
    ),
    (
        "termin",
        "Betreff: Einladung Jahrestreffen\nWir laden Sie herzlich zu unserem Jahrestreffen am 5. November ein. Anmeldung bis Monatsende.",
    ),
    (
        "newsletter",
        "Betreff: Neuigkeiten im Oktober\nEntdecken Sie unsere neuen Funktionen und sichern Sie sich 20 % Rabatt. Abmelden: Link unten.",
    ),
    (
        "newsletter",
        "Betreff: Wochenrueckblick\nDie wichtigsten Branchenmeldungen der Woche in fuenf Minuten. Sie erhalten diese Mail als Abonnent.",
    ),
    (
        "newsletter",
        "Betreff: Nur heute: Webinar gratis\nMelden Sie sich jetzt fuer unser kostenloses Webinar an und erhalten Sie ein E-Book dazu.",
    ),
    (
        "anfrage",
        "Betreff: Angebot Schulung\nWir interessieren uns fuer eine zweitaegige Schulung fuer 12 Mitarbeitende. Koennen Sie ein Angebot schicken?",
    ),
    (
        "anfrage",
        "Betreff: Frage zur Gefaehrdungsbeurteilung\nMuss die Beurteilung fuer unser Lager jaehrlich erneuert werden oder nur bei Aenderungen?",
    ),
    (
        "anfrage",
        "Betreff: Rueckfrage zu Ihrer Rechnung\nIn Ihrer Rechnung ist eine Position doppelt. Koennen Sie das pruefen und korrigieren?",
    ),
]

PROMPT = (
    "Ordne die folgende E-Mail genau einer Kategorie zu.\n"
    + "".join(f"- {k}: {v}\n" for k, v in LABELS.items())
    + "\nE-Mail:\n{mail}\n\n"
    "Antworte nur mit einem Wort: " + ", ".join(LABELS) + "."
)


def _post(url: str, body: dict) -> tuple[dict, float]:
    daten = json.dumps(body).encode("utf-8")
    anfrage = urllib.request.Request(
        url, data=daten, headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(anfrage, timeout=TIMEOUT_S) as antwort:
        ergebnis = json.loads(antwort.read().decode("utf-8"))
    return ergebnis, (time.perf_counter() - t0) * 1000


def _ollama(
    mail: str, num_predict: int, logprobs: bool, keep_alive: str = "5m"
) -> tuple[dict, float]:
    body = {
        "model": MODELL,
        "prompt": PROMPT.replace("{mail}", mail),
        "stream": False,
        "think": False,
        "keep_alive": keep_alive,
        "options": {"temperature": 0, "num_predict": num_predict},
    }
    if logprobs:
        body |= {"logprobs": True, "top_logprobs": 20}
    return _post(OLLAMA, body)


def text_weg(mail: str) -> dict:
    antwort, ms = _ollama(mail, num_predict=8, logprobs=False)
    roh = antwort.get("response", "")
    wort = roh.strip().strip(".").lower()
    label = next((k for k in LABELS if wort.startswith(k)), None)
    return {"label": label, "roh": roh, "ms": ms}


def restricted_softmax(top_logprobs: list[dict]) -> dict[str, float]:
    """Wahrscheinlichkeit je Label = Summe der Tokens, die ein Label-Praefix sind, neu normiert.

    Grenze: Ollama liefert hoechstens 20 Kandidaten. Ein Label ausserhalb der
    Top-20 bekommt 0 — echte Logits ALLER Labels gibt es ueber Ollama nicht.
    """
    masse = dict.fromkeys(LABELS, 0.0)
    for kandidat in top_logprobs:
        tok = kandidat["token"].strip().lower()
        if not tok:
            continue
        for k in LABELS:
            if k.startswith(tok):
                masse[k] += math.exp(kandidat["logprob"])
                break
    summe = sum(masse.values())
    return {k: (v / summe if summe else 0.0) for k, v in masse.items()}


def logit_weg(mail: str) -> dict:
    antwort, ms = _ollama(mail, num_predict=1, logprobs=True)
    tops = antwort["logprobs"][0]["top_logprobs"]
    p = restricted_softmax(tops)
    label = max(p, key=p.get) if any(p.values()) else None
    return {"label": label, "p": p, "ms": ms}


def kev_weg(mail: str) -> dict:
    body = {
        "state": mail,
        "model": "kev-latest",
        "questions": {
            "kategorie": {
                "type": "choice",
                "instructions": "Welcher Kategorie gehoert diese E-Mail an?",
                "criteria": LABELS,
            }
        },
    }
    antwort, ms = _post(KEV, body)
    a = antwort["answers"]["kategorie"]
    return {"label": a.get("choice"), "p": a.get("probabilities"), "ms": ms}


def main() -> None:
    wege = {"text": text_weg, "logit": logit_weg, "kev": kev_weg}
    # Aufwaermen: Modell laden, damit die Ladezeit nicht in die erste Messung faellt.
    for f in wege.values():
        f(FAELLE[0][1])
    for runde in range(1, RUNDEN + 1):
        for nr, (gold, mail) in enumerate(FAELLE, 1):
            for name, f in wege.items():
                zeile = {"runde": runde, "fall": nr, "gold": gold, "weg": name}
                try:
                    zeile |= f(mail)
                except Exception as exc:  # Messung: jeden Fehler als Zeile festhalten
                    zeile["fehler"] = repr(exc)
                print(json.dumps(zeile, ensure_ascii=False), flush=True)
    _ollama(FAELLE[0][1], num_predict=1, logprobs=False, keep_alive="0")
    print(
        json.dumps(
            {"meta": {"modell": MODELL, "runden": RUNDEN, "faelle": len(FAELLE)}}
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
