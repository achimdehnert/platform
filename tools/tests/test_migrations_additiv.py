"""Tests für tools/migrations_additiv.py (platform#3804, Kriterium 7).

Die Quelltext-Prüfung läuft ohne Git gegen Strings; der Git-Pfad einmal
end-to-end gegen ein Fixture-Repo mit zwei Commits.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import migrations_additiv as ma  # noqa: E402

KOPF = "from django.db import migrations, models\n\nclass Migration(migrations.Migration):\n    operations = [\n"
FUSS = "    ]\n"


def _mig(*ops: str) -> str:
    return KOPF + "".join(f"        {op},\n" for op in ops) + FUSS


def test_should_accept_create_add_index_constraint():
    quelle = _mig(
        'migrations.CreateModel(name="Lauf", fields=[])',
        'migrations.AddField(model_name="lauf", name="x", field=models.IntegerField(null=True))',
        'migrations.AddIndex(model_name="lauf", index=models.Index(fields=["x"]))',
        'migrations.AddConstraint(model_name="lauf", constraint=models.UniqueConstraint(fields=["x"], name="u"))',
        'migrations.AlterModelOptions(name="lauf", options={"ordering": ["x"]})',
    )
    assert ma.verstoesse_in_quelle(quelle, "a/migrations/0002_x.py") == []


@pytest.mark.parametrize(
    "op",
    [
        'migrations.RemoveField(model_name="lauf", name="x")',
        'migrations.DeleteModel(name="Lauf")',
        'migrations.AlterField(model_name="lauf", name="x", field=models.TextField())',
        'migrations.RenameField(model_name="lauf", old_name="x", new_name="y")',
        "migrations.RunPython(lambda a, s: None)",
        'migrations.RunSQL("DROP TABLE lauf")',
        'migrations.AlterUniqueTogether(name="lauf", unique_together=set())',
    ],
)
def test_should_flag_non_additive_operation(op):
    befunde = ma.verstoesse_in_quelle(_mig(op), "a/migrations/0003_y.py")
    assert len(befunde) == 1
    assert op.split("(")[0].split(".")[1] in befunde[0]


def test_should_measure_separate_database_and_state_by_database_ops():
    harmlos = _mig(
        'migrations.SeparateDatabaseAndState(state_operations=[migrations.RemoveField(model_name="l", name="x")], database_operations=[])'
    )
    assert ma.verstoesse_in_quelle(harmlos, "p") == []
    boese = _mig(
        'migrations.SeparateDatabaseAndState(state_operations=[], database_operations=[migrations.RemoveField(model_name="l", name="x")])'
    )
    assert len(ma.verstoesse_in_quelle(boese, "p")) == 1


def _repo_mit_zwei_staenden(
    tmp_path: Path, zweite_migration: str, alt_aendern: bool = False
) -> Path:
    repo = tmp_path / "hub"
    mig = repo / "apps" / "x" / "migrations"
    mig.mkdir(parents=True)
    (mig / "__init__.py").write_text("")
    (mig / "0001_initial.py").write_text(
        _mig('migrations.CreateModel(name="A", fields=[])')
    )

    def git(*a: str) -> None:
        subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "eins")
    git("tag", "alt")
    (mig / "0002_zwei.py").write_text(zweite_migration)
    if alt_aendern:
        (mig / "0001_initial.py").write_text(
            _mig('migrations.CreateModel(name="B", fields=[])')
        )
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "zwei")
    git("tag", "neu")
    return repo


def test_should_pass_end_to_end_for_additive_commit(tmp_path):
    repo = _repo_mit_zwei_staenden(
        tmp_path,
        _mig(
            'migrations.AddField(model_name="a", name="n", field=models.IntegerField(null=True))'
        ),
    )
    assert ma.pruefe(repo, "alt", "neu") == []
    assert ma.main(["x", str(repo), "alt", "neu"]) == 0


def test_should_fail_end_to_end_for_removed_field_and_rewritten_history(tmp_path):
    repo = _repo_mit_zwei_staenden(
        tmp_path,
        _mig('migrations.RemoveField(model_name="a", name="n")'),
        alt_aendern=True,
    )
    befunde = ma.pruefe(repo, "alt", "neu")
    assert any("RemoveField" in b for b in befunde)
    assert any("Alt-Migration M" in b for b in befunde)
    assert ma.main(["x", str(repo), "alt", "neu"]) == 1


def test_should_return_two_on_bad_ref(tmp_path):
    repo = _repo_mit_zwei_staenden(tmp_path, _mig())
    assert ma.main(["x", str(repo), "alt", "gibt-es-nicht"]) == 2
