from pathlib import Path

from cad_services.utils.hash import sha256_file


def test_sha256_file(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text("abc", encoding="utf-8")
    assert sha256_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
