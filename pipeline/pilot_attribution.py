"""Internal presentation specification only; never a public article input."""

from pipeline.review_governance import (
    ItemBinding,
    ReviewDecision,
    ReviewLedger,
    decision_reason,
    evaluate,
    latest_event,
)


def attribution_contract(item, source, binding, now, *, ledger=None, decision=None):
    binding = ItemBinding.model_validate(binding.model_dump(mode="json"))
    if (item.source_registry_id != source.id or binding.source_id != source.id
            or item.id != binding.item_id or item.canonical_url != binding.canonical_url
            or item.content_hash != binding.content_sha256):
        raise ValueError("Cross-source or changed attribution evidence")
    if (binding.provenance == "synthetic") != item.is_demo:
        raise ValueError("Attribution item and binding provenance disagree")
    if decision is not None:
        decision = ReviewDecision.model_validate(decision.model_dump(mode="json"))
        if decision.binding != binding:
            raise ValueError("Attribution decision does not match evidence")
    ledger = ReviewLedger.model_validate((ledger if ledger is not None else ReviewLedger()).model_dump(mode="json"))
    rights = evaluate(binding, ledger, now)
    event = latest_event(binding, ledger)
    authoritative = event.decision if event else None
    current = authoritative if rights["reason"] == "review_required" else None
    # A standalone caller-supplied decision is a visible proposal only. It can
    # never override authoritative history or create an approved display claim.
    proposed = decision if event is None else None
    if proposed and decision_reason(binding, proposed, now) != "review_required":
        proposed = None
    claims = current or proposed
    evidence = claims.evidence if claims else []
    result = {
        "contract_version": 2, "internal_only": True, "synthetic": binding.provenance == "synthetic",
        "provenance": binding.provenance,
        "item_id": item.id, "source_id": source.id, "publisher": source.name,
        "canonical_source": item.canonical_url, "required_attribution_link": item.canonical_url,
        "original_publication_url": claims.original_publication_url if claims else None,
        "original_creator": claims.original_creator if claims else None,
        "creator_evidence_status": "recorded-unapproved" if claims and claims.original_creator else "unestablished",
        "applicable_license": claims.applicable_license if claims else None,
        "license_evidence_urls": [e.url for e in evidence if e.scope == "license-grant"],
        "license_status": "unresolved" if authoritative and not current else "unapproved",
        "rights_review": rights,
        "rights_status": ("denied" if (authoritative and authoritative.review_status in {"REVOKED", "REJECTED"}
                          or item.rights_review and item.rights_review.state == "REJECTED") else
                          "review_required" if current else "unknown"),
        "reviewer_authority": "unverified-operator-metadata",
        "review_decision": ({**authoritative.model_dump(mode="json"), "event_sha256": event.event_sha256,
                             "ledger_head_sha256": ledger.head_sha256,
                             "evidence_validity": rights["reason"]} if authoritative else None),
        "proposed_review": proposed.model_dump(mode="json") if proposed else None,
        "quarantined_review": authoritative.model_dump(mode="json") if authoritative and not current else (
            decision.model_dump(mode="json") if decision and not event and not proposed else None),
        "cached_decision_status": ("superseded" if decision and authoritative and decision != authoritative
                                   else "matching" if decision and authoritative else "proposal" if decision else "absent"),
        "permitted_fields": claims.permitted_fields if claims else [],
        "permitted_transformations": claims.permitted_transformations if claims else [],
        "reuse_scope_status": "proposed-only" if claims else "unresolved",
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "independently_verified": False, "breaking_news": False,
        "attribution_obligations": claims.attribution_obligations if claims else [],
        "license_exceptions": claims.license_exceptions if claims else [],
        "modification_notice": "Normalized metadata for local evaluation; excerpt may be shortened.",
    }
    if source.id == "kubernetes":
        if item.rights_review is None:
            raise ValueError("Kubernetes attribution requires a held rights observation")
        result.update(editorial_classification="source-reported-announcement",
                      rights_observation_state=item.rights_review.state,
                      published_at=item.published_at.isoformat() if item.published_at and not item.missing_publication_time else None,
                      attribution_gaps=["Item license scope and exceptions need review",
                                        "Original creator and origin need evidence",
                                        "Credit, license link and modification obligations need confirmation"])
    elif source.id == "cisa_kev":
        if item.advisory is None or item.published_at is not None or not item.missing_publication_time:
            raise ValueError("KEV contract requires date-only advisory evidence")
        result.update(editorial_classification="official-single-source-security-advisory",
                      cve_id=item.external_id, catalog_added_on=item.advisory.catalog_added_on.isoformat(),
                      remediation_due_on=(item.advisory.remediation_due_on.isoformat()
                                          if item.advisory.remediation_due_on else None),
                      original_cisa_catalog_link=item.canonical_url, published_at=None,
                      date_labels=item.advisory.presentation(),
                      third_party_references={"policy": "link-only; separate rights required for reuse",
                                              "status": "unresolved", "vendor_identity": None, "urls": [],
                                              "fetched": False, "excerpted": False},
                      attribution_gaps=["Confirm item/database reuse scope and third-party exceptions",
                                        "Review advisory copy and applicable deadline context"])
    else:
        raise ValueError("Only the disabled local pilots have an attribution specification")
    return result
