"""Drill fuer tools/sitzungs_branches.py — Sitzungsabgrenzung (platform#2234).

Positivkontrollen am nachgebauten Realfall vom 2026-09-24, je mit Gegenprobe:

- Zuordnung: zwei Sitzungen desselben Kontos, Leases aktiv/geschlossen/archiviert
  — nur die Branches der eigenen Sitzung kommen heraus; Alt-Leases ohne
  `claude_session` werden gezaehlt, nie still ausgeschlossen.
- Nachlauf (E.3): Fragment 13:01Z (gemergt mit #3531 um 13:31Z), danach #3540
  angelegt und 16:08Z gemergt — muss als Nachlauf erscheinen. Gegenprobe: mit
  dem juengeren Fragment 17:06Z ist nichts mehr offen.

Kein Netz: der gh-Abruf wird ueber `--eingabe` ersetzt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sitzungs_branches as sb  # noqa: E402

EIGEN = "e911bf49-94e1-4b4c-86ed-f4a4337ba501"
FREMD = "54428acd-0000-4000-8000-000000000000"
B_EIGEN = "session/2026-09-24/achim-dehnert/mail-links-pdf"
B_EIGEN_2 = "session/2026-09-24/achim-dehnert/bauantrag"
B_FREMD = "session/2026-09-24/achim-dehnert/host-maintenance"
FRAG_RE = r"Z-e911bf49(-[0-9]+)?[.]md$"


def _lease(
    pfad: Path, branch: str, repo: str = "platform", cs: str | None = EIGEN
) -> None:
    daten = {"session_id": pfad.name.split(".")[0], "repo": repo, "branch": branch}
    if cs is not None:
        daten["claude_session"] = cs
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten), encoding="utf-8")


def _lease_baum(tmp_path: Path) -> Path:
    leases = tmp_path / "leases"
    _lease(leases / "a.json", B_EIGEN)
    _lease(leases / "b.json.closed", B_EIGEN_2, repo="cad-hub")
    _lease(leases / "c.json", B_FREMD, cs=FREMD)
    _lease(leases / "alt.json.closed", "session/2026-09-20/x/alt", cs=None)
    _lease(
        tmp_path / "leases-archive" / "2026-09" / "d.json.closed",
        "session/2026-09-24/achim-dehnert/archiviert",
    )
    (leases / "befund").mkdir()
    (leases / "befund" / "k.lock").write_text("nicht json", encoding="utf-8")
    return leases


class TestZuordnung:
    def test_should_return_only_branches_of_own_session_across_active_closed_and_archive(
        self, tmp_path
    ):
        z = sb.zuordnen(sb.lade_leases(_lease_baum(tmp_path)), EIGEN[:8])
        assert z["branches"] == sorted(
            [B_EIGEN, B_EIGEN_2, "session/2026-09-24/achim-dehnert/archiviert"]
        )
        assert B_FREMD not in z["branches"]
        assert z["repos"] == ["cad-hub", "platform"]
        assert z["grund"] is None

    def test_should_match_full_id_and_short_prefix_alike(self, tmp_path):
        leases = sb.lade_leases(_lease_baum(tmp_path))
        assert (
            sb.zuordnen(leases, EIGEN)["branches"]
            == sb.zuordnen(leases, EIGEN[:8])["branches"]
        )

    def test_should_count_old_leases_without_field_instead_of_dropping_them(
        self, tmp_path
    ):
        z = sb.zuordnen(sb.lade_leases(_lease_baum(tmp_path)), EIGEN[:8])
        assert z["ohne_feld"] == 1

    def test_should_report_not_assignable_when_no_lease_carries_the_session(
        self, tmp_path
    ):
        leases = tmp_path / "leases"
        _lease(leases / "alt.json", B_EIGEN, cs=None)
        z = sb.zuordnen(sb.lade_leases(leases), EIGEN[:8])
        assert z["branches"] == []
        assert "nicht zuordenbar" in z["grund"] and "1 Alt-Lease" in z["grund"]

    def test_should_refuse_ids_shorter_than_eight_chars(self, tmp_path):
        z = sb.zuordnen(sb.lade_leases(_lease_baum(tmp_path)), "e911")
        assert z["branches"] == [] and "kuerzer als 8" in z["grund"]


# Realfall 2026-09-24: Fragment 13:01Z, danach weitergearbeitet.
PR_FRAGMENT = {
    "number": 3531,
    "headRefName": B_EIGEN,
    "state": "MERGED",
    "createdAt": "2026-09-24T12:40:00Z",
    "mergedAt": "2026-09-24T13:31:00Z",
    # Pfad zusammengesetzt: als Literal hielte test_ci_trigger_covers_test_inputs
    # das echte Fragment im Repo fuer eine Testeingabe dieses Drills.
    "files": [
        {"path": "/".join(("docs", "handover.d", "2026-09-24T13-01-28Z-e911bf49.md"))}
    ],
}
PR_DANACH = {
    "number": 3540,
    "headRefName": B_EIGEN,
    "state": "MERGED",
    "createdAt": "2026-09-24T15:50:00Z",
    "mergedAt": "2026-09-24T16:08:00Z",
    "files": [{"path": "tools/mail_links.py"}],
}
PR_FREMD = {
    "number": 3532,
    "headRefName": B_FREMD,
    "state": "OPEN",
    "createdAt": "2026-09-24T15:00:00Z",
    "mergedAt": None,
    "files": [],
}


class TestNachlauf:
    def test_should_flag_pr_created_after_the_fragment(self):
        treffer = sb.prs_nach_fragment(
            [PR_FRAGMENT, PR_DANACH, PR_FREMD],
            [B_EIGEN],
            "2026-09-24T13:01:28Z",
            FRAG_RE,
        )
        assert [p["number"] for p in treffer] == [3540]

    def test_should_pass_when_a_younger_fragment_exists(self):
        """Gegenprobe: Fragment 17:06Z deckt #3540 — kein Nachlauf."""
        treffer = sb.prs_nach_fragment(
            [PR_FRAGMENT, PR_DANACH], [B_EIGEN], "2026-09-24T17:06:22Z", FRAG_RE
        )
        assert treffer == []

    def test_should_not_count_the_pr_that_carries_the_fragment(self):
        spaet = {**PR_FRAGMENT, "createdAt": "2026-09-24T13:05:00Z"}
        assert (
            sb.prs_nach_fragment([spaet], [B_EIGEN], "2026-09-24T13:01:28Z", FRAG_RE)
            == []
        )

    def test_should_not_count_prs_of_other_sessions(self):
        assert sb.prs_nach_fragment([PR_FREMD], [B_EIGEN], "2026-09-24T13:01:28Z") == []

    def test_should_count_pr_without_creation_date(self):
        ohne = {**PR_DANACH, "createdAt": None}
        assert sb.prs_nach_fragment([ohne], [B_EIGEN], "2026-09-24T13:01:28Z") == [ohne]


class TestCli:
    def _eingabe(self, tmp_path: Path, prs: list[dict]) -> str:
        pfad = tmp_path / "prs.json"
        pfad.write_text(json.dumps({"achimdehnert/platform": prs}), encoding="utf-8")
        return str(pfad)

    def test_should_end_with_nachlauf_result_on_the_real_case(self, tmp_path, capsys):
        leases = _lease_baum(tmp_path)
        rc = sb.main(
            [
                "nachlauf",
                "--sitzung",
                EIGEN[:8],
                "--lease-dir",
                str(leases),
                "--fragment-zeit",
                "2026-09-24T13:01:28Z",
                "--fragment-muster",
                FRAG_RE,
                "--eingabe",
                self._eingabe(tmp_path, [PR_FRAGMENT, PR_DANACH, PR_FREMD]),
            ]
        )
        aus = capsys.readouterr().out
        assert rc == 1
        assert "RESULT: NACHLAUF 1 platform#3540" in aus

    def test_should_end_ok_with_the_younger_fragment(self, tmp_path, capsys):
        """Gegenprobe zum Realfall."""
        leases = _lease_baum(tmp_path)
        rc = sb.main(
            [
                "nachlauf",
                "--sitzung",
                EIGEN[:8],
                "--lease-dir",
                str(leases),
                "--fragment-zeit",
                "2026-09-24T17:06:22Z",
                "--fragment-muster",
                FRAG_RE,
                "--eingabe",
                self._eingabe(tmp_path, [PR_FRAGMENT, PR_DANACH]),
            ]
        )
        assert rc == 0
        assert "RESULT: OK" in capsys.readouterr().out

    def test_should_say_not_assignable_instead_of_ok(self, tmp_path, capsys):
        leases = tmp_path / "leases"
        _lease(leases / "alt.json", B_EIGEN, cs=None)
        rc = sb.main(
            [
                "nachlauf",
                "--sitzung",
                EIGEN[:8],
                "--lease-dir",
                str(leases),
                "--fragment-zeit",
                "2026-09-24T13:01:28Z",
                "--eingabe",
                self._eingabe(tmp_path, [PR_DANACH]),
            ]
        )
        aus = capsys.readouterr().out
        assert rc == 0
        assert "RESULT: NICHT_ZUORDENBAR" in aus and "RESULT: OK" not in aus

    def test_should_print_branches_as_json(self, tmp_path, capsys):
        leases = _lease_baum(tmp_path)
        assert (
            sb.main(["branches", "--sitzung", EIGEN, "--lease-dir", str(leases)]) == 0
        )
        assert B_EIGEN in json.loads(capsys.readouterr().out)["branches"]
