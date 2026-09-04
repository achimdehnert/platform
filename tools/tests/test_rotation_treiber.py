"""Drill fuer den Treiber ``github_repo_secret`` (#2813) — komplett mit Attrappen.

Die HTTP-Schicht ist eine injizierbare Funktion; hier wird eine Attrappe
eingesetzt, die aufgerufene Pfade mitschreibt. Damit ist die Verdrahtung
pruefbar, ohne dass je ein Token oder eine echte API im Spiel ist.

Der wichtigste Drill ist ``test_should_report_a_green_run_without_a_red_one_as_weak``:
ein Beleg-Workflow, der schon vorher gruen war, beweist nicht, dass er das
wegen des neuen Werts ist (AD-4). Das Werkzeug darf ihn annehmen — aber es muss
es sagen.
"""

from __future__ import annotations

import base64
import io
import sys
import zipfile
from pathlib import Path

import pytest
from nacl.public import PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rotation import treiber_github as tg  # noqa: E402

PROOF = {"workflow": "secret-probe.yml", "log_marker": "✓ ATTRAPPE_TOKEN gueltig"}

#: Echter, aber wegwerfbarer Curve25519-Public-Key. Ein Null-Key waere kein
#: gueltiger Punkt auf der Kurve — libsodium lehnt ihn ab, und der Drill haette
#: dann die Attrappe gemessen statt die sealed box.
ATTRAPPEN_PUBLIC_KEY = base64.b64encode(
    bytes(PrivateKey.generate().public_key)
).decode()


def _logzip(text: str) -> bytes:
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as archiv:
        archiv.writestr("0_probe.txt", text)
    return puffer.getvalue()


class AttrappenHttp:
    """Minimale GitHub-Attrappe. `laeufe` ist die Folge der Antworten auf die
    Lauf-Abfrage — so laesst sich 'noch nicht fertig' nachstellen."""

    def __init__(
        self, laeufe=None, logtext="✓ ATTRAPPE_TOKEN gueltig", vorher_rot=True
    ):
        self.pfade: list[str] = []
        self.gesetzt: list[dict] = []
        self.vorher = {
            "id": 1,
            "status": "completed",
            "conclusion": "failure" if vorher_rot else "success",
        }
        self.laeufe = (
            laeufe
            if laeufe is not None
            else [
                {
                    "id": 2,
                    "status": "completed",
                    "conclusion": "success",
                    "html_url": "u",
                }
            ]
        )
        self._lauf_abfragen = 0
        self.logtext = logtext

    def __call__(self, methode, pfad, token=None, koerper=None, roh=False):
        self.pfade.append(f"{methode} {pfad}")
        if pfad == "/app/installations":
            return 200, [{"id": 9, "account": {"login": "iilgmbh"}}]
        if pfad.endswith("/access_tokens"):
            return 201, {"token": "ATTRAPPE-installation-token"}
        if pfad.endswith("/actions/secrets/public-key"):
            return 200, {"key": ATTRAPPEN_PUBLIC_KEY, "key_id": "42"}
        if "/actions/secrets/" in pfad and methode == "PUT":
            self.gesetzt.append(koerper)
            return 204, {}
        if pfad.count("/") == 3 and methode == "GET":  # /repos/{org}/{repo}
            return 200, {"default_branch": "main"}
        if pfad.endswith("/dispatches"):
            return 204, {}
        if "/runs?" in pfad:
            self._lauf_abfragen += 1
            if self._lauf_abfragen == 1:
                return 200, {"workflow_runs": [self.vorher]}
            index = self._lauf_abfragen - 2
            lauf = self.laeufe[min(index, len(self.laeufe) - 1)]
            return 200, {"workflow_runs": [lauf] if lauf else []}
        if pfad.endswith("/logs"):
            return 200, _logzip(self.logtext)
        return 404, {}


def _treiber(http, **kwargs):
    return tg.GithubTreiber(
        http=http,
        app_id="1",
        pem=Path("/dev/null"),
        schlafen=lambda _s: None,
        wartezeit=0,
        **kwargs,
    )


# --------------------------------------------------------------------------
def test_should_refuse_a_sovereign_org_before_any_call():
    http = AttrappenHttp()
    with pytest.raises(tg.GovOrgAbgelehnt):
        _treiber(http).token("meiki-lra")
    assert http.pfade == [], "abgelehnt wird VOR dem ersten Netzzugriff"


@pytest.mark.parametrize("org", sorted(tg.GOV_ORGS))
def test_should_refuse_every_declared_sovereign_org(org):
    with pytest.raises(tg.GovOrgAbgelehnt):
        _treiber(AttrappenHttp()).token(org)


def test_should_resolve_the_installation_id_live():
    http = AttrappenHttp()
    treiber = _treiber(http)
    treiber._token_je_org["iilgmbh"] = "ATTRAPPE"  # JWT-Signatur braucht openssl+PEM
    assert treiber.token("iilgmbh") == "ATTRAPPE"


def test_should_explain_a_missing_app_id():
    treiber = tg.GithubTreiber(http=AttrappenHttp(), app_id="", pem=Path("/dev/null"))
    with pytest.raises(tg.TreiberFehler, match="ROTATION_GH_APP_ID"):
        treiber.token("iilgmbh")


def test_should_explain_a_missing_private_key(tmp_path):
    with pytest.raises(tg.TreiberFehler, match="rotation"):
        tg.app_jwt("1", tmp_path / "fehlt.pem")


def test_should_seal_the_value_before_setting_it():
    http = AttrappenHttp()
    treiber = _treiber(http)
    treiber._token_je_org["iilgmbh"] = "ATTRAPPE"
    treiber.setze("iilgmbh/risk-hub", "ATTRAPPE_TOKEN", b"ATTRAPPE-1234")
    assert len(http.gesetzt) == 1
    versiegelt = http.gesetzt[0]["encrypted_value"]
    assert "ATTRAPPE-1234" not in versiegelt, "der Wert geht nur versiegelt raus"
    assert http.gesetzt[0]["key_id"] == "42"


def test_should_find_the_marker_and_report_the_negative_control():
    http = AttrappenHttp(vorher_rot=True)
    treiber = _treiber(http)
    treiber._token_je_org["iilgmbh"] = "ATTRAPPE"
    beleg = treiber.belege("iilgmbh/risk-hub", PROOF, "ATTRAPPE_TOKEN")
    assert beleg.ergebnis == "ok" and beleg.negativprobe is True


def test_should_report_a_green_run_without_a_red_one_as_weak():
    http = AttrappenHttp(vorher_rot=False)
    treiber = _treiber(http)
    treiber._token_je_org["iilgmbh"] = "ATTRAPPE"
    beleg = treiber.belege("iilgmbh/risk-hub", PROOF, "ATTRAPPE_TOKEN")
    assert beleg.ergebnis == "ok"
    assert beleg.negativprobe is False, "ohne roten Vorlauf ist der Beleg schwaecher"


def test_should_be_red_when_the_marker_is_missing():
    http = AttrappenHttp(logtext="Job erfolgreich beendet")
    treiber = _treiber(http)
    treiber._token_je_org["iilgmbh"] = "ATTRAPPE"
    beleg = treiber.belege("iilgmbh/risk-hub", PROOF, "ATTRAPPE_TOKEN")
    assert beleg.ergebnis == "rot" and beleg.hinweis == "Marker nicht im Log"


def test_should_give_up_after_three_polls():
    """§5.5 Punkt 6: messbares Abbruchkriterium, nicht 'bis es klappt'."""
    http = AttrappenHttp(laeufe=[{"id": 2, "status": "in_progress"}])
    treiber = _treiber(http, abfragen=3)
    treiber._token_je_org["iilgmbh"] = "ATTRAPPE"
    beleg = treiber.belege("iilgmbh/risk-hub", PROOF, "ATTRAPPE_TOKEN")
    assert beleg.ergebnis == "ohne_beleg" and "3 Abfragen" in (beleg.hinweis or "")


def test_should_not_mistake_the_previous_run_for_the_new_one():
    """Der alte Lauf hat den Marker im Log — wer nicht auf eine NEUE Lauf-ID
    achtet, liest ihn und meldet gruen, ohne dass etwas gelaufen ist."""
    http = AttrappenHttp(
        laeufe=[{"id": 1, "status": "completed", "conclusion": "failure"}]
    )
    treiber = _treiber(http, abfragen=2)
    treiber._token_je_org["iilgmbh"] = "ATTRAPPE"
    assert (
        treiber.belege("iilgmbh/risk-hub", PROOF, "ATTRAPPE_TOKEN").ergebnis
        == "ohne_beleg"
    )


def test_should_retry_the_dispatch_without_inputs_on_422():
    class Http422(AttrappenHttp):
        def __init__(self):
            super().__init__()
            self.dispatch_koerper = []

        def __call__(self, methode, pfad, token=None, koerper=None, roh=False):
            if pfad.endswith("/dispatches"):
                self.dispatch_koerper.append(koerper)
                if len(self.dispatch_koerper) == 1:
                    self.pfade.append(f"{methode} {pfad}")
                    return 422, {"message": "Unexpected inputs"}
            return super().__call__(methode, pfad, token, koerper, roh)

    http = Http422()
    treiber = _treiber(http)
    treiber._token_je_org["iilgmbh"] = "ATTRAPPE"
    assert treiber.belege("iilgmbh/risk-hub", PROOF, "ATTRAPPE_TOKEN").ergebnis == "ok"
    assert "inputs" in http.dispatch_koerper[0]
    assert "inputs" not in http.dispatch_koerper[1]


def test_should_call_ohne_beleg_when_proof_is_incomplete():
    beleg = _treiber(AttrappenHttp()).belege("iilgmbh/risk-hub", {"workflow": "x.yml"})
    assert beleg.ergebnis == "ohne_beleg"
