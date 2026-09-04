"""Rotationswerkzeug Stufe 1 (KONZ-dev-hub-005, platform#2813).

Rotation ist ein **belegter Lauf ueber bekannte Konsumenten**, kein Skript je
Fall. Die Aufteilung der Module folgt genau dieser Kette:

* :mod:`inventar`        — was liegt wo, womit beweist man es (SSoT, nur lesen)
* :mod:`fingerprint`     — HMAC-Fingerabdruck des Werts, nie der Wert
* :mod:`log`             — append-only Lauf-Protokoll + Ausgabefilter
* :mod:`treiber_github`  — der eine Kanal der Stufe 1: github_repo_secret
* :mod:`cli`             — die Unterbefehle

Zwei Regeln gelten in jedem Modul und sind der Grund fuer den Zuschnitt:
der Wert wird nie ausgegeben und nie protokolliert, und ein Konsument ohne
``proof`` wird **gemeldet und gezaehlt**, nicht still uebersprungen.
"""
