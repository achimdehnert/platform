"""Unit tests for scripts/render_staging.py ingress modes (ADR-210 / ADR-212).

Covers the Traefik opt-in (ADR-212 Klausel-3) without regressing the default
nginx host-port model — the renderer gates every staging repo via R7 drift-verify,
so the nginx path must stay byte-stable while traefik is added.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_staging.py"
_spec = importlib.util.spec_from_file_location("render_staging", _SCRIPT)
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)


def _repo(ingress: str | None) -> dict:
    staging = {
        "image": "ghcr.io/achimdehnert/dev-hub:${IMAGE_TAG:-latest}",
        "web_container": "dev_hub_staging_web",
        "web_service": "dev-hub-staging-web",
        "port": 19002,
        "hostnames": ["staging-devhub.iil.pet"],
    }
    if ingress is not None:
        staging["ingress"] = ingress
    return {"staging": staging, "oidc": {}}


def test_should_default_to_nginx_host_port_when_ingress_absent():
    out = rs.render_compose("dev-hub", _repo(None))
    assert 'ports:\n      - "127.0.0.1:19002:8000"' in out
    assert "traefik" not in out
    assert "expose:" not in out
    # default networks block has no external traefik_public
    assert "external: true" not in out


def test_should_render_traefik_ingress_when_opted_in():
    out = rs.render_compose("dev-hub", _repo("traefik"))
    # no host-port binding under Traefik
    assert "127.0.0.1:19002:8000" not in out
    assert 'expose:\n      - "8000"' in out
    # web joins the external traefik_public network
    assert "networks: [dev_hub_staging_network, traefik_public]" in out
    assert "traefik_public:\n    external: true" in out
    # router/service labels derived from hostname + repo
    assert "traefik.enable=true" in out
    assert (
        "traefik.http.routers.devhub-staging.rule=Host(`staging-devhub.iil.pet`)"
        in out
    )
    assert (
        "traefik.http.services.devhub-staging.loadbalancer.server.port=8000" in out
    )


def test_should_drop_nginx_vhost_artifact_for_traefik_repo():
    paths = {p.name for p in rs.render_all("dev-hub", _repo("traefik"))}
    assert "docker-compose.staging.yml" in paths
    assert "nginx-vhost.conf" not in paths


def test_should_keep_nginx_vhost_artifact_for_default_repo():
    paths = {p.name for p in rs.render_all("dev-hub", _repo(None))}
    assert "nginx-vhost.conf" in paths
