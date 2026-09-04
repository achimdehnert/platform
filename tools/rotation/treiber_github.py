"""Treiber ``github_repo_secret`` — der eine Kanal der Stufe 1.

Setzen ist der einfache Teil (``PUT /repos/{owner}/{repo}/actions/secrets/{name}``
mit dem Repo-Public-Key). Der schwierige Teil ist der **Beleg**: ein Workflow,
der auch ohne das Secret gruen wird, beweist nichts (AD-4, Realfall meiki-hub
``GH_TOKEN: ${{ secrets.X || secrets.GITHUB_TOKEN }}``). Deshalb:

* der Beleg ist ein ``workflow_dispatch`` eines **dedizierten** Prüf-Workflows
  (Vorlage ``docs/templates/secret-probe.yml``), der nichts deployt,
* gesucht wird ein Marker im Log, nicht der Exit-Code,
* und der **vorige** Lauf desselben Workflows wird mitgelesen: war er rot, ist
  das die Negativprobe (mit dem alten Wert rot, mit dem neuen gruen). War er
  gruen, wird das im Log als ``negativprobe: false`` vermerkt — nicht
  verschwiegen.

Die HTTP-Schicht ist eine **injizierbare Funktion**, damit die ganze Kette mit
Attrappen getestet werden kann, ohne je ein echtes Token zu berühren.

Autorisierung: Installation-Token der GitHub-App „rotation" (eigene App unter
``iilgmbh`` — nicht Profil B, das ein Break-Glass-Mandat ist, AD-8). Der JWT
wird wie in ``tools/gh-app-token.sh`` per ``openssl`` signiert; die Install-ID
wird je Org **live** aufgeloest statt hartkodiert.
"""

from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

API = "https://api.github.com"

#: Souveraenitaets-Orgs. Solange dort keine Installation der App existiert und
#: kein Owner-Go je Org vorliegt, lehnt der Treiber ab (§5.4, C6). Die Ablehnung
#: ist KEIN Fehler des Laufs — der Konsument wird als `abgelehnt` protokolliert.
GOV_ORGS = frozenset({"ttz-lif", "meiki-lra"})

APP_ID_ENV = "ROTATION_GH_APP_ID"
APP_KEY_ENV = "ROTATION_GH_APP_KEY"
STANDARD_PEM = Path.home() / ".secrets" / "github_app_rotation.pem"

#: §5.5 Punkt 6: hoechstens drei Abfragen, dann `ohne_beleg`. Messbar, nicht "bis es klappt".
BELEG_ABFRAGEN = 3
BELEG_WARTEZEIT = 60


class TreiberFehler(RuntimeError):
    """Etwas an der Verdrahtung stimmt nicht — nie ein Wert in der Meldung."""


class GovOrgAbgelehnt(TreiberFehler):
    pass


# --------------------------------------------------------------------------
# HTTP — eine Funktion, damit sie ersetzbar ist
# --------------------------------------------------------------------------
Antwort = tuple[int, Any]
HttpFunktion = Callable[..., Antwort]


def echtes_http(
    methode: str,
    pfad: str,
    token: str | None = None,
    koerper: dict | None = None,
    roh: bool = False,
) -> Antwort:
    """``(status, daten)``. ``roh=True`` liefert Bytes (Log-ZIP)."""
    url = pfad if pfad.startswith("http") else f"{API}{pfad}"
    daten = json.dumps(koerper).encode() if koerper is not None else None
    anfrage = urllib.request.Request(url, data=daten, method=methode)
    anfrage.add_header("Accept", "application/vnd.github+json")
    anfrage.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        anfrage.add_header("Authorization", f"Bearer {token}")
    if daten:
        anfrage.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            inhalt = antwort.read()
            if roh:
                return antwort.status, inhalt
            return antwort.status, json.loads(inhalt) if inhalt else {}
    except urllib.error.HTTPError as fehler:
        inhalt = fehler.read()
        if roh:
            return fehler.code, inhalt
        try:
            return fehler.code, json.loads(inhalt) if inhalt else {}
        except json.JSONDecodeError:
            return fehler.code, {"message": "nicht parsebare Fehlerantwort"}


# --------------------------------------------------------------------------
# App-Token
# --------------------------------------------------------------------------
def _b64url(roh: bytes) -> str:
    return base64.urlsafe_b64encode(roh).decode().rstrip("=")


def app_jwt(app_id: str, pem: Path, jetzt: int | None = None) -> str:
    """RS256-JWT wie in ``tools/gh-app-token.sh`` — signiert per ``openssl``.

    Die stdlib kann RS256 nicht signieren, und eine zusaetzliche Abhaengigkeit
    (``cryptography``/``PyJWT``) nur dafuer waere ein neues Risiko im Pfad, der
    Schreibrechte auf Secrets traegt. ``openssl`` ist auf jeder Maschine da, auf
    der ``gh-app-token.sh`` heute schon laeuft.
    """
    if not pem.is_file():
        raise TreiberFehler(
            f"Privater Schluessel der App 'rotation' nicht lesbar: {pem}\n"
            f"Setzen ueber {APP_KEY_ENV}, oder App anlegen (Owner-Schritt, "
            "GitHub-UI unter iilgmbh: Secrets R/W + Metadata R, Installation auf "
            "iilgmbh und achimdehnert). Siehe Inventar-Eintrag "
            "platform.ROTATION_APP_PRIVATE_KEY."
        )
    jetzt = jetzt or int(time.time())
    kopf = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    nutzlast = _b64url(
        json.dumps(
            {"iat": jetzt - 60, "exp": jetzt + 540, "iss": str(app_id)}, separators=(",", ":")
        ).encode()
    )
    zu_signieren = f"{kopf}.{nutzlast}".encode()
    lauf = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(pem)],
        input=zu_signieren,
        capture_output=True,
        check=False,
    )
    if lauf.returncode != 0:
        raise TreiberFehler("openssl konnte den JWT nicht signieren (Schluessel unlesbar?)")
    return f"{kopf}.{nutzlast}.{_b64url(lauf.stdout)}"


def installation_token(org: str, http: HttpFunktion, jwt: str) -> str:
    """Install-ID live aufloesen, dann Token holen — kein hartkodiertes Mapping."""
    status, installationen = http("GET", "/app/installations", token=jwt)
    if status != 200 or not isinstance(installationen, list):
        raise TreiberFehler(f"/app/installations antwortete {status}")
    passend = [i for i in installationen if i["account"]["login"].lower() == org.lower()]
    if not passend:
        vorhanden = ", ".join(i["account"]["login"] for i in installationen) or "keine"
        raise TreiberFehler(
            f"App 'rotation' ist auf '{org}' nicht installiert. Installiert auf: {vorhanden}"
        )
    status, daten = http(
        "POST", f"/app/installations/{passend[0]['id']}/access_tokens", token=jwt
    )
    if status != 201 or "token" not in daten:
        raise TreiberFehler(f"Installation-Token fuer {org} nicht erhalten (HTTP {status})")
    return daten["token"]


# --------------------------------------------------------------------------
# Treiber
# --------------------------------------------------------------------------
@dataclass
class Belegergebnis:
    ergebnis: str  # ok | rot | ohne_beleg
    negativprobe: bool
    lauf_url: str | None = None
    hinweis: str | None = None


class GithubTreiber:
    kind = "github_repo_secret"

    def __init__(
        self,
        http: HttpFunktion | None = None,
        app_id: str | None = None,
        pem: Path | None = None,
        schlafen: Callable[[float], None] | None = None,
        abfragen: int = BELEG_ABFRAGEN,
        wartezeit: int = BELEG_WARTEZEIT,
    ) -> None:
        self.http = http or echtes_http
        self.app_id = app_id or os.environ.get(APP_ID_ENV, "")
        self.pem = pem or Path(os.environ.get(APP_KEY_ENV, "") or STANDARD_PEM)
        self.schlafen = schlafen or time.sleep
        self.abfragen = abfragen
        self.wartezeit = wartezeit
        self._token_je_org: dict[str, str] = {}

    # -- Autorisierung ------------------------------------------------------
    def token(self, org: str) -> str:
        if org in GOV_ORGS:
            raise GovOrgAbgelehnt(
                f"'{org}' ist eine Souveraenitaets-Org — der Treiber setzt dort nichts, "
                "solange keine Installation und kein Owner-Go je Org vorliegt (KONZ-dev-hub-005 §5.4)."
            )
        if org not in self._token_je_org:
            if not self.app_id:
                raise TreiberFehler(
                    f"{APP_ID_ENV} nicht gesetzt — die App 'rotation' ist noch nicht angelegt "
                    "(Owner-Schritt, platform#2813)."
                )
            self._token_je_org[org] = installation_token(
                org, self.http, app_jwt(self.app_id, self.pem)
            )
        return self._token_je_org[org]

    # -- Setzen -------------------------------------------------------------
    def setze(self, ref: str, name: str, wert: bytes) -> None:
        org, repo = ref.split("/", 1)
        token = self.token(org)
        status, schluessel = self.http(
            "GET", f"/repos/{org}/{repo}/actions/secrets/public-key", token=token
        )
        if status != 200 or "key" not in schluessel:
            raise TreiberFehler(f"Public-Key von {ref} nicht lesbar (HTTP {status})")
        status, _ = self.http(
            "PUT",
            f"/repos/{org}/{repo}/actions/secrets/{name}",
            token=token,
            koerper={
                "encrypted_value": versiegle(schluessel["key"], wert),
                "key_id": schluessel["key_id"],
            },
        )
        if status not in (201, 204):
            raise TreiberFehler(f"Setzen von {name} in {ref} fehlgeschlagen (HTTP {status})")

    # -- Belegen ------------------------------------------------------------
    def belege(self, ref: str, proof: dict[str, Any], secret_name: str = "") -> Belegergebnis:
        workflow = proof.get("workflow")
        marker = proof.get("log_marker")
        if not workflow or not marker:
            return Belegergebnis("ohne_beleg", False, hinweis="proof ohne workflow/log_marker")

        org, repo = ref.split("/", 1)
        token = self.token(org)

        # Negativprobe: der Zustand VOR dem Dispatch. Ein roter Vorlauf ist der
        # Beweis, dass der Workflow ohne den neuen Wert nicht gruen wird.
        vorher = self._letzter_lauf(org, repo, workflow, token)
        negativprobe = bool(vorher and vorher.get("conclusion") == "failure")
        vorher_id = (vorher or {}).get("id")

        zweig = self._standardzweig(org, repo, token)
        pfad = f"/repos/{org}/{repo}/actions/workflows/{workflow}/dispatches"
        status, _ = self.http(
            "POST", pfad, token=token,
            koerper={"ref": zweig, "inputs": {"secret_name": secret_name}},
        )
        if status == 422:
            # Der Workflow kennt den Input nicht (aeltere Pruef-Workflows ohne
            # `secret_name`). Kein Grund aufzugeben — noch einmal ohne Inputs.
            status, _ = self.http("POST", pfad, token=token, koerper={"ref": zweig})
        if status != 204:
            return Belegergebnis(
                "ohne_beleg", negativprobe, hinweis=f"workflow_dispatch antwortete {status}"
            )

        lauf = None
        for versuch in range(self.abfragen):
            self.schlafen(self.wartezeit)
            lauf = self._letzter_lauf(org, repo, workflow, token)
            if lauf and lauf.get("id") != vorher_id and lauf.get("status") == "completed":
                break
            lauf = None
        if lauf is None:
            return Belegergebnis(
                "ohne_beleg",
                negativprobe,
                hinweis=f"Lauf nach {self.abfragen} Abfragen nicht abgeschlossen",
            )

        if marker in self._logtext(org, repo, lauf["id"], token):
            return Belegergebnis("ok", negativprobe, lauf.get("html_url"))
        return Belegergebnis(
            "rot", negativprobe, lauf.get("html_url"), hinweis="Marker nicht im Log"
        )

    # -- Hilfen -------------------------------------------------------------
    def _standardzweig(self, org: str, repo: str, token: str) -> str:
        status, daten = self.http("GET", f"/repos/{org}/{repo}", token=token)
        return daten.get("default_branch", "main") if status == 200 else "main"

    def _letzter_lauf(self, org: str, repo: str, workflow: str, token: str) -> dict | None:
        status, daten = self.http(
            "GET",
            f"/repos/{org}/{repo}/actions/workflows/{workflow}/runs?per_page=1",
            token=token,
        )
        if status != 200:
            return None
        laeufe = daten.get("workflow_runs") or []
        return laeufe[0] if laeufe else None

    def _logtext(self, org: str, repo: str, lauf_id: int, token: str) -> str:
        status, roh = self.http(
            "GET", f"/repos/{org}/{repo}/actions/runs/{lauf_id}/logs", token=token, roh=True
        )
        if status not in (200, 302) or not isinstance(roh, (bytes, bytearray)):
            return ""
        try:
            with zipfile.ZipFile(io.BytesIO(roh)) as archiv:
                return "\n".join(
                    archiv.read(n).decode("utf-8", "replace") for n in archiv.namelist()
                )
        except zipfile.BadZipFile:
            return roh.decode("utf-8", "replace")


# --------------------------------------------------------------------------
# Verschluesselung
# --------------------------------------------------------------------------
def versiegle(public_key_b64: str, wert: bytes) -> str:
    """libsodium sealed box, base64. Fallback auf ``gh`` waere hier falsch:
    ``gh secret set`` verschluesselt selbst, braucht aber den Wert auf stdin —
    also einen zweiten Weg, auf dem der Wert durch einen Subprozess laeuft.
    PyNaCl ist im uv-venv vorhanden (geprueft 2026-09-04: 1.6.2); fehlt es,
    bricht der Lauf mit einer Anleitung ab, statt still einen anderen Pfad zu
    nehmen."""
    try:
        from nacl import encoding, public
    except ImportError as fehler:  # pragma: no cover - Umgebungsfrage
        raise TreiberFehler(
            "PyNaCl fehlt — ohne sealed box kann kein Secret gesetzt werden.\n"
            "  python3 -m pip install pynacl\n"
            "Rueckfall von Hand (der Owner setzt, das Werkzeug belegt):\n"
            "  gh secret set <NAME> --repo <org>/<repo> --body-file <datei>"
        ) from fehler
    schluessel = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    return base64.b64encode(public.SealedBox(schluessel).encrypt(wert)).decode()
