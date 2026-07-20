"""Tests für den Deploy-ADR-Supersession-Gate (KONZ-011 / ADR-264)."""
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import check_deploy_adr_supersession as gate  # noqa: E402


def _write(tmp_path, adr_id, title, status="proposed", supersedes="[]", extra_fm="", body="Body."):
    fm = f"---\nid: ADR-{adr_id}\ntitle: {title}\nstatus: {status}\nsupersedes: {supersedes}\n{extra_fm}---\n\n{body}\n"
    p = tmp_path / f"ADR-{adr_id}-{title}.md"
    p.write_text(fm, encoding="utf-8")
    return str(p)


def test_should_flag_new_deploy_adr_without_supersedes(tmp_path):
    p = _write(tmp_path, "265", "final-deployment-pipeline", supersedes="[]")
    assert gate.violation_for(p) is not None


def test_should_pass_grandfathered_deploy_adr(tmp_path):
    # ADR-120 existierte vor dem Gate → auch mit leerem supersedes konform.
    p = _write(tmp_path, "120", "unified-deployment-pipeline", status="accepted", supersedes="[]")
    assert gate.violation_for(p) is None


def test_should_pass_new_deploy_adr_with_supersedes(tmp_path):
    p = _write(tmp_path, "265", "final-deployment-pipeline", supersedes="[ADR-021, ADR-120]")
    assert gate.violation_for(p) is None


def test_should_pass_new_deploy_adr_with_block_supersedes(tmp_path):
    p = _write(tmp_path, "266", "deployment-strategy-v2", supersedes="\n  - ADR-021\n  - ADR-120")
    assert gate.violation_for(p) is None


def test_should_ignore_new_non_deploy_adr(tmp_path):
    # Content-„pipeline" ist kein Deployment-ADR → nie geflaggt.
    p = _write(tmp_path, "265", "llm-powered-research-pipeline", supersedes="[]")
    assert gate.violation_for(p) is None


def test_should_pass_with_frontmatter_waiver(tmp_path):
    p = _write(tmp_path, "265", "narrow-deployment-addition", supersedes="[]",
               extra_fm="supersedes_waiver: enge Ergänzung, löst nichts ab\n")
    assert gate.violation_for(p) is None


def test_should_pass_with_body_waiver(tmp_path):
    p = _write(tmp_path, "265", "narrow-deployment-addition", supersedes="[]",
               body="<!-- supersedes-waiver: enge Ergänzung -->\nBody.")
    assert gate.violation_for(p) is None


def test_should_ignore_draft_status(tmp_path):
    p = _write(tmp_path, "265", "final-deployment-pipeline", status="draft", supersedes="[]")
    assert gate.violation_for(p) is None


def test_should_pass_on_current_adr_tree():
    """Der heutige docs/adr-Baum muss den Gate passieren (Grandfathering greift)."""
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import glob
    paths = glob.glob(os.path.join(repo, "docs", "adr", "ADR-*.md"))
    offenders = [gate.violation_for(p) for p in paths]
    offenders = [o for o in offenders if o]
    assert offenders == [], f"Gate darf heutigen Baum nicht flaggen: {offenders}"
