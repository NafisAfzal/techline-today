"""Operational recovery: asset inventory, offline backup validation and drills.

Nothing in this package contacts a network, provisions a credential, appoints a
reviewer or grants a permission. Every drill builds a synthetic newsroom in an
isolated temporary directory; the operator's real checkout is never a restore
target and never a drill fixture.
"""

from pipeline.recovery.inventory import RECOVERY_ASSETS, RecoveryAsset, inventory_report
from pipeline.recovery.verify import (
    RecoveryVerification,
    build_recovery_pack,
    verify_recovery_pack,
)

__all__ = [
    "RECOVERY_ASSETS",
    "RecoveryAsset",
    "inventory_report",
    "RecoveryVerification",
    "build_recovery_pack",
    "verify_recovery_pack",
]
