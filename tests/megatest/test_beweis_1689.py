"""BEWEIS-DATEI #1689 — wird vor dem Merge wieder entfernt.

Absichtlich roter Fall, um den Fehlerpfad des Megatest-Steps EINMAL scharf
zu beweisen: Step-outcome muss 'failure' werden, der Failure-Issue-Schritt
muss real feuern. Abnahme-Kriterium aus platform#1689.
"""


def test_should_fail_deliberately_beweis_1689():
    raise AssertionError("Beweis-Lauf #1689: dieser Fail MUSS den Step rot machen")
