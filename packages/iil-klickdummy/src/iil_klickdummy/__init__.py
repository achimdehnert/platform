"""iil-klickdummy — shared infrastructure for platform:ADR-211 Rev 13.

Public surface:
    check_i1, check_i2, check_i3, check_i4 — invariant checks
    extract_requirements                    — Spec → UC/FR/NFR/Lasten/Pflicht
    inventory                               — S11 Cross-Repo Legacy-Inventur
    install_snippets                        — copy/symlink HTML+JS+templates into a repo

Distribution: pip via Git-URL (v1.0+, ADR-211 Rev 13 §Distribution).
Snippets shipped as package_data; consumers install them via
`klickdummy-install-snippets` console-script.
"""

__version__ = "1.0.0"
__author__ = "Achim Dehnert"

from . import (  # noqa: F401
    check_i1, check_i2, check_i3, check_i4,
    extract_requirements, inventory, install_snippets,
)
