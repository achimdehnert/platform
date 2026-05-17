from adr_review.cli import is_adr_file, label_for


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
