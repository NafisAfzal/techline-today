"""Which assets a small newsroom must protect, and which it can never recover.

The important distinction is between *data* and *credential*. A journal, a
rights decision or a public key registry can be copied, replayed and verified.
An Ed25519 private key cannot: once it is lost, no backup restores it, and the
only lawful remedy is a reviewed rotation or a reviewed recovery decision.
Reporting both under one word, "backup", is how small teams accidentally
believe they are protected when they are not.
"""

from dataclasses import dataclass
from typing import Literal

Recoverability = Literal["recoverable", "reconstructible", "irrecoverable"]
Category = Literal["authority", "credential", "editorial", "rights", "operational"]


@dataclass(frozen=True)
class RecoveryAsset:
    """One protected asset and what an operator must actually do about it."""

    asset_id: str
    name: str
    category: Category
    recoverability: Recoverability
    location: str
    protection: str
    required_action: str
    notes: str

    def as_dict(self) -> dict:
        return {"asset_id": self.asset_id, "name": self.name, "category": self.category,
                "recoverability": self.recoverability, "location": self.location,
                "protection": self.protection, "required_action": self.required_action,
                "notes": self.notes}


RECOVERY_ASSETS: tuple[RecoveryAsset, ...] = (
    RecoveryAsset(
        asset_id="owner-trust-root",
        name="Owner trust root (public key material)",
        category="authority",
        recoverability="recoverable",
        location="Operator-held trust pin outside the checkout (TECHLINE_AUTHORITY_TRUST_FILE)",
        protection="Independent custody channel plus a separately recorded fingerprint",
        required_action="Keep two independently verified copies of the pin and its SHA-256 fingerprint",
        notes="Public material, but authenticity comes from the custody channel, not from the file",
    ),
    RecoveryAsset(
        asset_id="owner-private-signing-key",
        name="Owner private signing key",
        category="credential",
        recoverability="irrecoverable",
        location="Offline operator-managed encrypted PKCS8 file outside the checkout",
        protection="Encrypted backup held separately from the machine that signs",
        required_action="Rehearse passphrase access offline; if lost, run a reviewed root-rotation "
                        "and recovery-authorization decision",
        notes="Excluded from this project's recovery packs. A separately held encrypted key backup may "
              "support human recovery; if every copy is lost, the journal cannot reconstruct the key",
    ),
    RecoveryAsset(
        asset_id="reviewer-public-key-registry",
        name="Reviewer public-key registry",
        category="authority",
        recoverability="reconstructible",
        location="Replayed from the signed authority journal",
        protection="The journal plus the pinned owner root",
        required_action="Back up the journal; verify the replayed registry matches the pinned root",
        notes="Derived state, but only trustworthy when the pinned root is independently trusted",
    ),
    RecoveryAsset(
        asset_id="reviewer-private-signing-keys",
        name="Reviewer private signing keys",
        category="credential",
        recoverability="irrecoverable",
        location="Reviewer-managed, never in this repository",
        protection="Reviewer's own custody procedures",
        required_action="Owner rotates the affected key after a verified loss; old approvals lapse",
        notes="A reviewer key compromise is a rotation and scope-review event, not a restore",
    ),
    RecoveryAsset(
        asset_id="authority-journal",
        name="Signed authority journal",
        category="authority",
        recoverability="recoverable",
        location=".cache/authority/journal.json",
        protection="Off-machine backup plus an independently held checkpoint",
        required_action="Back up after every recorded transaction and verify continuity offline",
        notes="Append-only history; a restored copy is only continuous when the chain verifies",
    ),
    RecoveryAsset(
        asset_id="revocations",
        name="Signed revocations and denials",
        category="authority",
        recoverability="recoverable",
        location="Inside the authority journal as signed records",
        protection="The same journal backup; never filtered out",
        required_action="Preserve denials during every restore; never restore a pre-denial journal "
                        "as if it were current",
        notes="A denial that is omitted from a restored history cannot be detected locally",
    ),
    RecoveryAsset(
        asset_id="external-trusted-checkpoints",
        name="Independently held trusted checkpoints",
        category="authority",
        recoverability="irrecoverable",
        location="An operator-controlled custodian outside this repository",
        protection="Access-controlled storage or a protected history the operator maintains",
        required_action="Capture a fresh checkpoint after each publication and confirm the custodian "
                        "actually retained it",
        notes="This project can prepare a checkpoint but cannot retain it for the operator",
    ),
    RecoveryAsset(
        asset_id="source-candidate-ledger",
        name="Source candidate onboarding ledger",
        category="rights",
        recoverability="recoverable",
        location=".cache/phase6/source-candidates.json",
        protection="Off-machine backup",
        required_action="Back up with the journal; verify the candidate chain on restore",
        notes="Local proposals only; it can never contain an approval",
    ),
    RecoveryAsset(
        asset_id="rights-evidence",
        name="Source rights evidence",
        category="rights",
        recoverability="recoverable",
        location="Private retained evidence referenced by digest from source records",
        protection="Private storage with access control",
        required_action="Keep the evidence bodies with their digests; a digest alone proves nothing",
        notes="A digest reference without the retained body is not evidence of a licence",
    ),
    RecoveryAsset(
        asset_id="rights-policy",
        name="Source rights policy",
        category="rights",
        recoverability="recoverable",
        location="config/source-rights.json and config/sources.yaml",
        protection="Version control plus backup",
        required_action="Include both files in every recovery pack",
        notes="Policy drift changes the meaning of every signed rights decision",
    ),
    RecoveryAsset(
        asset_id="translation-review-evidence",
        name="Translation review evidence",
        category="editorial",
        recoverability="recoverable",
        location=".cache/phase5/translations/ plus signed translation decisions",
        protection="Off-machine backup",
        required_action="Back up with the journal; re-verify the native-review binding on restore",
        notes="Machine translation is not native review; restored evidence does not change that",
    ),
    RecoveryAsset(
        asset_id="canonical-snapshot",
        name="Generated canonical edition",
        category="operational",
        recoverability="reconstructible",
        location="content/generated/snapshot.json",
        protection="Backup plus a repeatable live collection",
        required_action="Back up the exact snapshot bytes and its digest",
        notes="Regenerating it requires collection rights and time; the exact bytes are the evidence",
    ),
    RecoveryAsset(
        asset_id="emergency-stop-marker",
        name="Emergency publication stop",
        category="operational",
        recoverability="reconstructible",
        location=".cache/authority/STOP_PUBLICATION",
        protection="Presence of the marker",
        required_action="Clear it only by hand after a fresh independent verification",
        notes="It is deliberately not auto-cleared by any restore",
    ),
    RecoveryAsset(
        asset_id="recovery-metadata",
        name="Recovery manifests and drill records",
        category="operational",
        recoverability="recoverable",
        location="Operator-controlled recovery packs and drill reports",
        protection="Off-machine backup",
        required_action="Retain every pack manifest so a restore can be audited later",
        notes="Without the manifest a restore cannot prove what it restored",
    ),
)


def inventory_report() -> dict:
    """Machine-readable inventory with the credential boundary made explicit."""
    assets = [asset.as_dict() for asset in RECOVERY_ASSETS]
    irrecoverable = [a["asset_id"] for a in assets if a["recoverability"] == "irrecoverable"]
    return {
        "version": 1,
        "asset_count": len(assets),
        "assets": assets,
        "recoverable": [a["asset_id"] for a in assets if a["recoverability"] == "recoverable"],
        "reconstructible": [a["asset_id"] for a in assets if a["recoverability"] == "reconstructible"],
        "irrecoverable": irrecoverable,
        "irrecoverable_note": "These assets cannot be reconstructed or restored from this project's packs. "
                              "Separate authenticated custody or encrypted credential backups require human "
                              "verification. Loss of every key copy cannot be repaired by journal replay.",
        "credential_count": sum(1 for a in assets if a["category"] == "credential"),
        "publication_allowed": False,
    }
