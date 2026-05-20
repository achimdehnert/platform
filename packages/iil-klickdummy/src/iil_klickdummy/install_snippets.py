"""Install bundled snippets (HTML+JS+templates) into a repo (platform:ADR-211 Rev 13).

Console-Script: `klickdummy-install-snippets [--target <dir>] [--symlink]`

Default target: `./platform-snippets/klickdummy/`. Creates dir if missing.
Default mode: copy (cross-platform-safe). `--symlink` creates symlinks for
live-updates during pip-upgrade.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from importlib.resources import files
from pathlib import Path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="./platform-snippets/klickdummy",
                        help="Target directory in the consuming repo")
    parser.add_argument("--symlink", action="store_true",
                        help="Symlink instead of copy (live-updates on pip-upgrade)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing target without backup")
    args = parser.parse_args(argv)

    src_root = files("iil_klickdummy") / "snippets"
    tgt = Path(args.target).resolve()

    print(f"== Install klickdummy snippets ==")
    print(f"  Source : {src_root}")
    print(f"  Target : {tgt}")
    print(f"  Mode   : {'symlink' if args.symlink else 'copy'}")

    if tgt.exists() and not args.force:
        print(f"  ✗ target exists, use --force or remove manually: {tgt}")
        return 1

    if tgt.exists():
        shutil.rmtree(tgt) if tgt.is_dir() else tgt.unlink()

    tgt.mkdir(parents=True, exist_ok=True)

    # Iterate package_data files (importlib.resources)
    def _copy_recursive(src, dst: Path):
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if args.symlink:
                # Resolve the underlying filesystem path of the package resource
                with files("iil_klickdummy").joinpath("snippets") as base_path:
                    rel = Path(str(src)).relative_to(base_path)
                    real = Path(str(base_path)) / rel
                    dst.symlink_to(real)
            else:
                dst.write_bytes(src.read_bytes())
            print(f"  ✓ {dst.relative_to(tgt)}")
        else:
            for child in src.iterdir():
                _copy_recursive(child, dst / child.name)

    _copy_recursive(src_root, tgt)
    print(f"\nDone. {tgt} ready. Include in shell.html:")
    print(f'  <script src="{tgt.name}/feedback-widget/widget.js" defer></script>')
    return 0


def main_cli() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main_cli())
