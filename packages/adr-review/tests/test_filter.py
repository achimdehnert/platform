from adr_review.cli import is_adr_file, label_for, should_escalate


def test_should_match_adr_paths():
    assert is_adr_file("docs/adr/ADR-208-foo.md")
    assert is_adr_file("adr/ADR-001.md")
    assert is_adr_file("some/nested/ADR-042-bar.md")
    assert is_adr_file("concepts/adr-actions/note.md")


def test_should_reject_non_adr_paths():
    assert not is_adr_file("README.md")
    assert not is_adr_file("docs/guides/setup.md")
    assert not is_adr_file("concepts/adr-actions/install.sh")
    assert not is_adr_file("src/app.py")


def test_should_map_score_to_label():
    assert label_for(9) == "adr-review-passed"
    assert label_for(7) == "adr-review-passed"
    assert label_for(6) == "adr-review-concerns"
    assert label_for(5) == "adr-review-concerns"
    assert label_for(4) == "adr-review-failed"
    assert label_for(1) == "adr-review-failed"


def test_should_escalate_on_deep_label():
    ok, why = should_escalate(["adr-deep-review"], 1, 9, 6, "adr-deep-review")
    assert ok and "Label" in why


def test_should_escalate_on_multi_adr():
    ok, why = should_escalate([], 3, 9, 6, "adr-deep-review")
    assert ok and "cross-cutting" in why


def test_should_escalate_on_low_score():
    ok, why = should_escalate([], 1, 5, 6, "adr-deep-review")
    assert ok and "Erstpass-Score" in why


def test_should_not_escalate_when_clean():
    ok, why = should_escalate([], 1, 8, 6, "adr-deep-review")
    assert not ok and why == ""
