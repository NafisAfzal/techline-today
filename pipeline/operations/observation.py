"""Review existing receipts with explicit context; never authenticate local claims."""

from datetime import UTC, datetime

from pipeline.observations import ObservationContext
from pipeline.readiness import observation_evidence, read_observation_receipts


def review_observations(root, *, environment_id, ledger_id, now=None):
    expected = ObservationContext(version=1, environment_id=environment_id, ledger_id=ledger_id,
                                  provenance="operator-local")
    rows = read_observation_receipts(root)
    window = observation_evidence(rows, now or datetime.now(UTC))
    unbound, mismatched, synthetic = [], [], []
    for index, row in enumerate(rows):
        context = row.get("context")
        if context is None:
            unbound.append(index)
            continue
        checked = ObservationContext.model_validate(context)
        if checked.environment_id != expected.environment_id or checked.ledger_id != expected.ledger_id:
            mismatched.append(index)
        if checked.provenance == "synthetic" or not row.get("live"):
            synthetic.append(index)
        if (checked.provenance == "operator-local") != row["live"]:
            mismatched.append(index)
    return {"version": 1, "status": "FAIL" if mismatched or window["anomalies"] else "BLOCKED",
            "window": window, "environment_id": expected.environment_id, "ledger_id": expected.ledger_id,
            "unbound_receipts": unbound, "mismatched_receipts": sorted(set(mismatched)),
            "synthetic_receipts": synthetic, "local_context_consistent": bool(rows) and not unbound and not mismatched,
            "independent_provenance_verified": False, "genuinely_authenticated_days": 0,
            "eligible": False, "publication_allowed": False,
            "note": "Context and hash integrity are local claims. A genuine elapsed window still requires "
                    "independently authenticated provenance, clock and environment; none is provisioned."}
