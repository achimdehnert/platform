"""Tests fuer tools/origin_tls_melder.py.

Zwei Ebenen mit Absicht: die Klassifikation gegen eine eingesetzte Attrappe, und
die Invarianten der ECHTEN `infra/ports.yaml` / `infra/hosts.yaml` ohne jede Naht.

Der Schwerpunkt liegt auf der Unterscheidung, die dieses Werkzeug ueberhaupt
rechtfertigt: ein Platzhalter-Zertifikat mit Laufzeit bis 2036 sieht fuer eine
reine Datums-Pruefung gesuender aus als ein Let's-Encrypt-Zertifikat mit 40 Tagen
Rest — und ist der eigentliche Befund. Wer nur `notAfter` prueft, dreht die
Rangfolge um. Genau dagegen sind `test_should_*fallback*` gerichtet.
"""

from __future__ import annotations

import importlib.util
import pathlib
from datetime import datetime, timedelta, timezone

import pytest

WURZEL = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "origin_tls_melder", WURZEL / "tools" / "origin_tls_melder.py"
)
om = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(om)

JETZT = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
LE = "C = US, O = Let's Encrypt, CN = YE1"
CF = 'C = US, O = "CloudFlare, Inc.", OU = CloudFlare Origin SSL Certificate Authority'
FALLBACK = "CN = invalid.localhost"


def _dienst(name="x-hub", status="aktiv", grund=None, host="prod"):
    return {
        "name": name,
        "domain": f"{name}.iil.pet",
        "host": host,
        "betriebsstatus": status,
        "grund": grund,
    }


def _in_tagen(n: int) -> datetime:
    return JETZT + timedelta(days=n, hours=1)


# --- Klassifikation ---------------------------------------------------------


def test_should_classify_valid_letsencrypt_as_gueltig():
    klasse, rest = om.klassifiziere(_in_tagen(88), LE, JETZT, om.WARN_TAGE)
    assert klasse == "gueltig"
    assert rest == 88


def test_should_classify_letsencrypt_below_threshold_as_laeuft_ab():
    klasse, rest = om.klassifiziere(_in_tagen(10), LE, JETZT, om.WARN_TAGE)
    assert klasse == "laeuft-ab"
    assert rest == 10


def test_should_classify_past_notafter_as_abgelaufen():
    klasse, rest = om.klassifiziere(JETZT - timedelta(days=5), LE, JETZT, om.WARN_TAGE)
    assert klasse == "abgelaufen"
    assert rest < 0


def test_should_classify_missing_certificate_as_kein_zertifikat():
    assert om.klassifiziere(None, "", JETZT, om.WARN_TAGE) == ("kein-zertifikat", None)


def test_should_classify_cloudflare_origin_ca_as_kein_befund():
    klasse, _ = om.klassifiziere(_in_tagen(5328), CF, JETZT, om.WARN_TAGE)
    assert klasse == "cloudflare-origin-ca"
    assert om.KLASSEN[klasse][0] is False


def test_should_classify_fallback_certificate_as_befund_despite_long_validity():
    """Der Kern: 3453 Tage Restlaufzeit und trotzdem ein Befund.

    `CN=invalid.localhost` heisst, dass fuer diesen Namen gar kein vhost mit
    Zertifikat existiert. Eine reine Datums-Pruefung meldet hier gruen.
    """
    klasse, rest = om.klassifiziere(_in_tagen(3453), FALLBACK, JETZT, om.WARN_TAGE)
    assert klasse == "fallback-zertifikat"
    assert rest > om.WARN_TAGE
    assert om.KLASSEN[klasse][0] is True


def test_should_rank_fallback_as_finding_but_fresh_letsencrypt_as_ok():
    """Falsifikationstest: die Rangfolge darf nicht am Datum haengen."""
    fallback, _ = om.klassifiziere(_in_tagen(3453), FALLBACK, JETZT, om.WARN_TAGE)
    frisch, _ = om.klassifiziere(_in_tagen(40), LE, JETZT, om.WARN_TAGE)
    assert om.KLASSEN[fallback][0] is True
    assert om.KLASSEN[frisch][0] is False


def test_should_treat_unparsable_notafter_as_kein_zertifikat():
    assert om._parse_notafter("Kraut und Rueben") is None


def test_should_parse_openssl_notafter_format():
    assert om._parse_notafter("Nov 21 09:15:53 2026 GMT") == datetime(
        2026, 11, 21, 9, 15, 53, tzinfo=timezone.utc
    )


# --- Messung je Host --------------------------------------------------------


def _laeufer(ausgabe: str, code: int = 0):
    return lambda cmd: (code, ausgabe)


def test_should_read_domain_notafter_and_issuer_from_host_output():
    out = "TLS_TERMINIERT\t15\t-\na.iil.pet\tNov 21 09:15:53 2026 GMT\t" + LE + "\n"
    ergebnis = om.messe_host("root@x", ["a.iil.pet"], _laeufer(out))
    assert ergebnis["_tls_terminiert"] is True
    assert ergebnis["a.iil.pet"] == ("Nov 21 09:15:53 2026 GMT", LE)


def test_should_mark_host_without_certificates_as_not_terminating_tls():
    out = "TLS_TERMINIERT\t0\t-\na.iil.pet\tKEINS\tKEINS\n"
    ergebnis = om.messe_host("root@x", ["a.iil.pet"], _laeufer(out))
    assert ergebnis["_tls_terminiert"] is False


def test_should_not_report_green_when_ssh_fails():
    """Eine leere Antwort ist keine Aussage — sie darf nie als gruen durchgehen."""
    ergebnis = om.messe_host("root@x", ["a.iil.pet"], _laeufer("", code=255))
    assert ergebnis["_tls_terminiert"] is None

    dienste = [_dienst("a")]
    messung = om.messe(
        dienste, {"prod": "root@x"}, laeufer=_laeufer("", code=255), jetzt=JETZT
    )
    assert messung["a"][0] == "nicht-messbar"
    assert om.KLASSEN["nicht-messbar"][0] is True


def test_should_classify_tunnel_host_domains_as_kein_tls_am_origin():
    out = "TLS_TERMINIERT\t0\t-\na.iil.pet\tKEINS\tKEINS\n"
    messung = om.messe(
        [_dienst("a")], {"prod": "root@x"}, laeufer=_laeufer(out), jetzt=JETZT
    )
    assert messung["a"][0] == "kein-tls-am-origin"
    assert om.KLASSEN["kein-tls-am-origin"][0] is False


def test_should_not_probe_hosts_without_ssh_target():
    messung = om.messe(
        [_dienst("a", host="prod-b")], {}, laeufer=_laeufer(""), jetzt=JETZT
    )
    assert messung["a"][0] == "nicht-messbar"


def test_should_quote_domains_in_remote_command():
    befehl = om.fernbefehl(["a.iil.pet", "b.de"])
    assert "'a.iil.pet'" in befehl and "'b.de'" in befehl
    assert "TLS_TERMINIERT" in befehl


# --- Bewertung / Lebenszyklus ----------------------------------------------


def test_should_park_inactive_service_with_reason():
    e = om.bewerte([_dienst("a", status="stillgelegt", grund="Owner-Entscheid")], {})
    assert len(e["geparkt"]) == 1 and not e["befunde"]


def test_should_flag_inactive_service_without_reason_as_silent_exception():
    e = om.bewerte([_dienst("a", status="stillgelegt")], {})
    assert len(e["stumme_ausnahme"]) == 1 and not e["geparkt"]


def test_should_flag_unknown_betriebsstatus():
    e = om.bewerte([_dienst("a", status="halb-aus", grund="egal")], {})
    assert len(e["stumme_ausnahme"]) == 1


def test_should_sort_findings_by_remaining_days():
    messung = {"a": ("abgelaufen", -3), "b": ("laeuft-ab", 10)}
    e = om.bewerte([_dienst("a"), _dienst("b")], messung)
    assert [z["name"] for z in e["befunde"]] == ["a", "b"]


def test_should_not_report_offline_run_as_green():
    e = om.bewerte([_dienst("a")], {"a": ("nicht-geprueft", None)})
    assert "NICHT geprueft" in om._kurzzeile(e)


# --- Invarianten der echten Registry ---------------------------------------


def test_should_load_real_ports_yaml_with_domains():
    dienste = om.lade_dienste(str(WURZEL / "infra" / "ports.yaml"))
    assert len(dienste) >= 20
    assert all(d["domain"] for d in dienste)


def test_should_resolve_real_prod_hosts_with_ssh_targets():
    hosts = om.lade_hosts(str(WURZEL / "infra" / "hosts.yaml"))
    assert "prod" in hosts and hosts["prod"].startswith("root@")
    assert set(hosts) <= set(om.PROD_HOSTS)


def test_should_keep_every_class_in_the_klassen_table():
    """Jede Klasse, die messe()/klassifiziere() erzeugen kann, braucht ein Urteil."""
    erzeugt = {
        "gueltig",
        "laeuft-ab",
        "abgelaufen",
        "kein-zertifikat",
        "fallback-zertifikat",
        "cloudflare-origin-ca",
        "nicht-messbar",
        "kein-tls-am-origin",
        "nicht-geprueft",
    }
    assert erzeugt <= set(om.KLASSEN)


@pytest.mark.parametrize("flag", ["--kurz", "--json"])
def test_should_run_offline_without_network(flag, capsys):
    import sys

    argv = sys.argv
    sys.argv = ["origin_tls_melder.py", "--offline", flag]
    try:
        assert om.main() == 0
    finally:
        sys.argv = argv
    assert capsys.readouterr().out.strip()
