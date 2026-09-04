"""Tests fuer den Waisen-Melder (platform#2586, K1).

Jede gruene Erwartung hat eine Gegenprobe: ein Melder, der nichts findet,
belegt erst dann eine Abwesenheit, wenn derselbe Vergleich nachweislich auch
etwas findet.
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from waisen_melder import (  # noqa: E402
    container_namen,
    erklaerte_container,
    erklaerte_repos,
    prod_compose_dateien,
    urteile,
    zuordnung_aus_ports,
)


# ---------------------------------------------------------------- Dateiauswahl


def test_should_pick_up_overlay_files_next_to_the_prod_file():
    # Der ganze Punkt des Melders: die Overlay-Dateien sind das Problem.
    namen = ["docker-compose.prod.yml", "docker-compose.llm-mcp.yml"]

    assert prod_compose_dateien(namen) == sorted(namen)


def test_should_drop_the_bare_compose_file_when_a_prod_file_exists():
    # Spiegelt scripts/deploy.sh: mit prod.yml ist die nackte Datei die
    # Entwicklungs-Datei. Ohne diese Regel meldete der Melder writing_hub_db_dev
    # und tradinghub-web als Waisen auf prod — beides war nie dafuer gedacht.
    namen = ["docker-compose.yml", "docker-compose.prod.yml"]

    assert prod_compose_dateien(namen) == ["docker-compose.prod.yml"]


def test_should_keep_the_bare_compose_file_when_there_is_no_prod_file():
    # Gegenprobe: die Regel darf nicht pauschal wegwerfen. chat-hub hat nur
    # docker-compose.yml — die IST dort der Stack.
    assert prod_compose_dateien(["docker-compose.yml"]) == ["docker-compose.yml"]


def test_should_ignore_files_describing_other_environments():
    namen = [
        "docker-compose.prod.yml",
        "docker-compose.staging.yml",
        "docker-compose.dev.yml",
        "docker-compose.ci.yml",
    ]

    assert prod_compose_dateien(namen) == ["docker-compose.prod.yml"]


def test_should_ignore_backup_files_left_behind_on_hosts():
    # Am 2026-09-01 lag docker-compose.llm-mcp.yml.bak in /opt/mcp-hub.
    assert prod_compose_dateien(["docker-compose.llm-mcp.yml.bak"]) == []


def test_should_ignore_files_that_are_not_compose_files_at_all():
    # Gegenprobe zum Test darueber: die Auswahl ist nicht einfach leer.
    namen = ["README.md", "Dockerfile", "docker-compose.prod.yml"]

    assert prod_compose_dateien(namen) == ["docker-compose.prod.yml"]


# ------------------------------------------------------------- Container-Namen


def test_should_read_the_explicit_container_name():
    text = "services:\n  rag_mcp:\n    container_name: mcp_hub_rag\n"

    assert container_namen(text) == {"rag_mcp": "mcp_hub_rag"}


def test_should_fall_back_to_the_service_name_when_none_is_given():
    # Lieber ein Name, der beim Vergleich auffaellt, als eine stille Luecke.
    text = "services:\n  grafana:\n    image: grafana/grafana\n"

    assert container_namen(text) == {"grafana": "grafana"}


def test_should_return_nothing_for_a_compose_file_without_services():
    assert container_namen("volumes:\n  data:\n") == {}


def test_should_skip_one_shot_containers_that_are_not_meant_to_keep_running():
    # cad-hubs `migrate` traegt restart: "no" und ist nach getaner Arbeit weg.
    text = 'services:\n  migrate:\n    restart: "no"\n  web:\n    image: x\n'

    assert container_namen(text) == {"web": "web"}


def test_should_skip_services_behind_a_profile_switch():
    text = "services:\n  debug:\n    profiles: [tools]\n  web:\n    image: x\n"

    assert container_namen(text) == {"web": "web"}


def test_should_keep_a_service_with_a_normal_restart_policy():
    # Gegenprobe zu den beiden darueber: es wird nicht alles ausgesiebt.
    text = "services:\n  web:\n    restart: unless-stopped\n"

    assert container_namen(text) == {"web": "web"}


# --------------------------------------------------------------------- Urteile


def _deklariert(*container: str, host: str = "prod") -> list[tuple[str, str, str, str]]:
    return [("mcp-hub", host, "docker-compose.prod.yml", c) for c in container]


def test_should_report_a_declared_container_that_is_not_running():
    ergebnis = urteile(
        _deklariert("llm_gateway"), {"prod": {"mcp_hub_db"}}, erklaert={}
    )

    assert [z["container"] for z in ergebnis["waisen"]] == ["llm_gateway"]


def test_should_not_report_a_declared_container_that_is_running():
    # Gegenprobe: derselbe Vergleich findet auch das Gesunde.
    ergebnis = urteile(_deklariert("mcp_hub_db"), {"prod": {"mcp_hub_db"}}, erklaert={})

    assert ergebnis["waisen"] == []
    assert len(ergebnis["laeuft"]) == 1


def test_should_excuse_a_missing_container_that_ports_yaml_declares_as_shut_down():
    ergebnis = urteile(
        _deklariert("altes_ding"),
        {"prod": {"mcp_hub_db"}},
        erklaert={"altes_ding": "stillgelegt"},
    )

    assert ergebnis["waisen"] == []
    assert ergebnis["entschuldigt"][0]["grund"] == "stillgelegt"


def test_should_count_a_container_once_even_when_two_compose_files_declare_it():
    # docker-compose.yml und docker-compose.prod.yml beschreiben oft denselben
    # Dienst — ohne Entdopplung meldete der Melder ihn zweimal.
    deklariert = [
        ("mcp-hub", "prod", "docker-compose.yml", "mcp_hub_db"),
        ("mcp-hub", "prod", "docker-compose.prod.yml", "mcp_hub_db"),
    ]

    ergebnis = urteile(deklariert, {"prod": {"mcp_hub_db"}}, erklaert={})

    assert len(ergebnis["laeuft"]) == 1


def test_should_keep_the_same_container_name_apart_on_two_different_hosts():
    # Gegenprobe zur Entdopplung: sie darf nicht ueber Hostgrenzen greifen.
    deklariert = [
        ("a-hub", "prod", "docker-compose.prod.yml", "web"),
        ("b-hub", "staging-dedicated", "docker-compose.prod.yml", "web"),
    ]

    ergebnis = urteile(
        deklariert, {"prod": {"web"}, "staging-dedicated": set()}, erklaert={}
    )

    assert len(ergebnis["laeuft"]) == 1
    assert len(ergebnis["waisen"]) == 1


def test_should_skip_hosts_that_could_not_be_read_instead_of_calling_them_orphans():
    # Ein unlesbarer Host ist nicht "nichts laeuft dort" — er ist unpruefbar.
    ergebnis = urteile(_deklariert("irgendwas", host="gx10"), {}, erklaert={})

    assert ergebnis == {"waisen": [], "laeuft": [], "entschuldigt": []}


# ------------------------------------------------------------------- ports.yaml


def test_should_map_repo_to_host_from_the_source_of_truth():
    ports = {
        "services": {
            "rag-mcp": {"repo": "achimdehnert/mcp-hub", "prod_host": "prod"},
            "ohne-host": {"repo": "achimdehnert/x-hub"},
        }
    }

    assert zuordnung_aus_ports(ports) == {"mcp-hub": "prod"}


def test_should_treat_only_non_active_services_as_explained():
    ports = {
        "services": {
            "laeuft": {"container_name": "a", "betriebsstatus": "aktiv"},
            "ruht": {"container_name": "b", "betriebsstatus": "stillgelegt"},
            "ohne_angabe": {"container_name": "c"},
        }
    }

    assert erklaerte_container(ports) == {"b": "stillgelegt"}


# ------------------------------------------------------- Urteil je Hub (K5)


def test_should_explain_every_container_of_a_shut_down_hub():
    # ports.yaml fuehrt pro Hub meist EINEN Dienst. Ohne Urteil je Hub blieben
    # worker/beat/db/redis eines stillgelegten Hubs als Waisen stehen — genau
    # der Zustand am 2026-09-01 bei coach-hub, wedding-hub und odoo.
    deklariert = [
        ("coach-hub", "prod-b", "docker-compose.prod.yml", "coach_hub_worker"),
        ("coach-hub", "prod-b", "docker-compose.prod.yml", "coach_hub_beat"),
    ]

    ergebnis = urteile(
        deklariert,
        {"prod-b": set()},
        erklaert={},
        erklaerte_hubs={"coach-hub": "stillgelegt"},
    )

    assert ergebnis["waisen"] == []
    assert len(ergebnis["entschuldigt"]) == 2
    assert "stillgelegt" in ergebnis["entschuldigt"][0]["grund"]


def test_should_still_report_a_container_of_a_hub_that_should_be_running():
    # Gegenprobe: die Hub-Erklaerung darf nicht alles zudecken.
    deklariert = [("mcp-hub", "prod", "docker-compose.llm-mcp.yml", "llm_gateway")]

    ergebnis = urteile(
        deklariert,
        {"prod": set()},
        erklaert={},
        erklaerte_hubs={"coach-hub": "stillgelegt"},
    )

    assert [z["container"] for z in ergebnis["waisen"]] == ["llm_gateway"]


def test_should_treat_a_hub_as_resting_when_ports_yaml_says_so():
    ports = {
        "services": {
            "apo-hub": {"repo": "achimdehnert/apo-hub", "betriebsstatus": "ruhend"}
        }
    }

    assert erklaerte_repos(ports) == {"apo-hub": "ruhend"}


def test_should_not_explain_a_hub_that_has_one_active_service():
    # decks-hub hat zwei Eintraege: einen aktiven und einen blockierten. Solange
    # irgendein Dienst laufen SOLL, ist der Hub nicht ruhend.
    ports = {
        "services": {
            "decks-hub": {"repo": "achimdehnert/decks-hub", "betriebsstatus": "aktiv"},
            "praes-iil-ai": {
                "repo": "achimdehnert/decks-hub",
                "betriebsstatus": "blockiert",
            },
        }
    }

    assert erklaerte_repos(ports) == {}
