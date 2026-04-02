"""
iil_testkit/contract/__init__.py

Fix H4: Package-Struktur mit expliziten Exports.

Öffentliche API:
    from iil_testkit.contract import (
        ContractVerifier,
        CallableContractVerifier,
        TaskContractVerifier,
        ResponseShapeVerifier,
        BaseContractVerifier,
    )
"""
from iil_testkit.contract.verifier import (
    BaseContractVerifier,
    CallableContractVerifier,
    ContractVerifier,
    ResponseShapeVerifier,
    TaskContractVerifier,
)

__all__ = [
    "BaseContractVerifier",
    "CallableContractVerifier",
    "ContractVerifier",
    "ResponseShapeVerifier",
    "TaskContractVerifier",
]
