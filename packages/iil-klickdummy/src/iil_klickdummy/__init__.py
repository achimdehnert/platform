"""iil-klickdummy — shared infrastructure for platform:ADR-211 conformance.

Public surface:
    check_i1, check_i2, check_i3, check_i4 — invariant checks
    extract_requirements                    — Spec → UC/FR/NFR/Lasten/Pflicht
    inventory                               — S11 Cross-Repo Legacy-Inventur

Version follows semver. Major-bump = ADR-update with migration cookbook.
"""

__version__ = "1.0.0"
__author__ = "Achim Dehnert"

# Re-exports for `python -m iil_klickdummy.<module>` compatibility
from . import check_i1, check_i2, check_i3, check_i4, extract_requirements, inventory  # noqa: F401, E402
