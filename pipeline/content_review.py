"""Private item review packets over the existing authenticated research evaluator.

This module records work to be done. Its exports are unsigned and never consumed
by a publication selector, signer, journal or authority registry.
"""

import argparse
import csv
import hashlib
import html
import io
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pipeline.authority.cli import ROOT, policy, snapshot
from pipeline.authority.protocol import AuthorityError
from pipeline.filesystem import confined_file, regular_path
from pipeline.generation import bounded_file
from pipeline.models import DIRECTION_CONTROLS
from pipeline.operations.redaction import refusal, scan_payload
from pipeline.research_approval import bind_research, readiness
from pipeline.review_governance import digest
from pipeline.strict_json import strict_json

STAGE_ROLES = {
    "RESEARCH_METADATA_APPROVED": "source-rights",
    "RESEARCH_EXTRACTIVE_APPROVED": "english-editor",
    "RESEARCH_FACTUAL_APPROVED": "fact-checker",
    "RESEARCH_CLASSIFICATION_APPROVED": "english-editor",
    "RESEARCH_PUBLICATION_APPROVED": "publisher",
    "RESEARCH_BANGLA_APPROVED": "native-bn",
}


class ReportArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "argument_error: Invalid operation arguments; run --help for valid options.\n")


def _source_packet(source, rights):
    entry = rights.get(source.source_registry_id, {})
    arxiv = source.source_registry_id == "arxiv"
    return {
        "source_item_id": source.id, "source_identity": source.source_registry_id,
        "publisher": source.publisher, "author_as_recorded": source.author,
        "original_url": source.original_url, "canonical_url": source.canonical_url,
        "source_content_hash_as_recorded": source.content_hash,
        "source_model_sha256": digest(source.model_dump(mode="json")),
        "published_at": source.published_at.isoformat() if source.published_at else None,
        "fetched_at": source.fetched_at.isoformat(), "missing_publication_time": source.missing_publication_time,
        "recorded_rights_policy": entry, "rights_policy_sha256": digest(entry),
        "metadata_rights": "Recorded policy only; item-scoped authenticated rights review remains required",
        "extractive_summary_rights": (
            "Verify each extract originates in arXiv abstract metadata; metadata policy does not cover paper bodies"
            if arxiv else "Verify the exact documentation revision, its applicable license and any exceptions"),
        "attribution_obligations": (
            "Retain author/title/version/source URL as editorial provenance; recorded CC0 has no attribution condition"
            if arxiv else "Verify creator/source/license attribution, identify changes and resolve any share-alike duty"),
        "rights_uncertainty": (
            "No item rights decision; confirm metadata-only origin, version identity and any third-party material"
            if arxiv else "No item rights decision; reconcile repository CC-BY-4.0 with Workers website CC-BY-SA-4.0 "
            "and retain the applicable exact-revision evidence"),
        "rights_evidence_urls_to_review": (
            ["https://info.arxiv.org/help/license/index.html",
             "https://info.arxiv.org/help/policies/submission_agreement.html"] if arxiv else
            ["https://github.com/cloudflare/cloudflare-docs/blob/production/LICENSE",
             "https://developers.cloudflare.com/fundamentals/reference/policies-compliances/licenses/"]),
        "item_hold": source.rights_review.model_dump(mode="json") if source.rights_review else None,
        "retrieved_from_network_by_this_command": False,
    }


def inventory(root, *, now=None, expected_sha256=None):
    """Recompute item decisions; never use exported readiness as authority."""
    root = Path(root)
    raw = bounded_file(confined_file(root, "content/generated/snapshot.json"), 50_000_000)
    sha256 = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and expected_sha256 != sha256:
        raise AuthorityError("snapshot_mismatch", "Snapshot differs from the independently supplied expected digest")
    original = strict_json(raw, max_bytes=50_000_000)
    edition, rights = snapshot(root), policy(root)
    report = readiness(root, edition, rights, now=now)
    # Do not mix content read before and after an interrupted/concurrent writer.
    if report["snapshot_sha256"] != sha256 or hashlib.sha256(
            confined_file(root, "content/generated/snapshot.json").read_bytes()).hexdigest() != sha256:
        raise AuthorityError("snapshot_changed", "Snapshot changed while preparing review inventory")
    rows = []
    for index, (story, original_story, eligibility) in enumerate(
            zip(edition.stories, original["stories"], report["items"], strict=True), 1):
        if original_story["id"] != story.id or eligibility["id"] != story.id:
            raise AuthorityError("inventory_identity", "Canonical and evaluated item order disagree")
        cited = [edition.sources[sid] for sid in story.source_ids]
        truncated = [name for name, text in [
            *((f"summary_bullets[{i}]", value) for i, value in enumerate(story.summary_bullets)),
            ("broader_summary", story.broader_summary),
            *((f"key_facts[{i}].text", value.text) for i, value in enumerate(story.key_facts)),
            *((f"claim_map[{i}].text", value.text) for i, value in enumerate(story.claim_map))]
            if "\u2026" in text or "..." in text]
        unreliable = any(source.missing_publication_time or source.published_at is None or
                         source.published_at != story.published_at for source in cited)
        stages = [{**stage, "required_role": STAGE_ROLES[stage["stage"]]} for stage in eligibility["stages"]]
        bindings = [bind_research(story, source, rights, edition.sources, language=language).model_dump(mode="json")
                    for source in cited for language in (["en", "bn"] if "bn" in story.translations else ["en"])]
        rows.append({
            "format": "techline.research.item-review-inventory/v1", "unsigned": True,
            "packet_number": index, "batch": (index - 1) // 6 + 1,
            "id": story.id, "headline": story.headline, "classification": eligibility["kind"],
            "canonical_snapshot_sha256": sha256, "canonical_record_sha256": digest(original_story),
            "digest_definition": "SHA-256 of canonical JSON of the original record object; bindings separately "
                                 "use existing parsed-model and cited-source digest semantics",
            "bindings": bindings, "sources": [_source_packet(source, rights) for source in cited],
            "publication_date_as_recorded": story.published_at.isoformat(),
            "publication_date_reliability": "REVIEW_REQUIRED" if unreliable else "CONSISTENT_WITH_STORED_SOURCE",
            "date_evidence_limit": "Stored agreement is not a fresh independent verification of publication time",
            "summary_bullets_as_recorded": story.summary_bullets,
            "broader_summary_as_recorded": story.broader_summary,
            "extractive_provenance_as_recorded": story.ai_metadata.model_dump(mode="json"),
            "ellipsis_fields": truncated, "has_ellipsis": bool(truncated),
            "summary_has_ellipsis": any(name.startswith(("summary_bullets", "broader_summary")) for name in truncated),
            "limitations_as_recorded": story.limitations,
            "limitations_review": "Review stated limitations against original evidence" if story.limitations else
                                  "No limitations recorded; qualified factual reviewer must assess and document limits",
            "english_review_requirements": [
                "Check each claim/number against the exact version of every cited original source",
                "Check truncation, incomplete sentences, attribution, uncertainty and meaningful limitations",
                "Distinguish author-reported results from independently established facts",
                "Verify research/reference label, dates, links and any retraction or withdrawal",
                "Propose any content repair separately; never edit canonical content through this packet"],
            "claim_verification_queue": [fact.model_dump(mode="json") for fact in story.key_facts],
            "number_verification_queue": [number.model_dump(mode="json") for number in story.key_numbers],
            "bangla_present": "bn" in story.translations,
            "bangla_requirements": "Exact Bangla content requires scoped native-bn authenticated approval; "
                                   "automated/fixture review labels do not supply it" if "bn" in story.translations else
                                   "No Bangla version in this item; English-only review. Any later translation "
                                   "changes the binding and requires fresh rights/editorial/native review",
            "required_decisions": stages,
            "missing_decisions": [stage for stage in stages if stage["status"] != "ACTIVE"],
            "existing_gate_blockers": eligibility["reasons"],
            "publication_allowed": False,
            "evaluation_publication_allowed": eligibility["publication_allowed"],
            "human_decision": None, "reviewer_identity": None, "signature": None,
        })
    return {"version": 1, "status": "PASS", "meaning": "Unsigned review inventory assembled; no approvals granted",
            "assessed_at": (now or datetime.now(UTC)).isoformat(), "snapshot_sha256": sha256,
            "record_count": len(rows), "research_count": sum(r["classification"] == "research" for r in rows),
            "reference_count": sum(r["classification"] == "reference" for r in rows),
            "ellipsis_count": sum(r["has_ellipsis"] for r in rows),
            "summary_ellipsis_count": sum(r["summary_has_ellipsis"] for r in rows),
            "missing_limitations_count": sum(not r["limitations_as_recorded"] for r in rows),
            "unreliable_date_count": sum(r["publication_date_reliability"] == "REVIEW_REQUIRED" for r in rows),
            "bangla_present_count": sum(r["bangla_present"] for r in rows),
            "eligible_count": report["eligible_count"], "checkpoint_custody": report["checkpoint_custody"],
            "items": rows, "publication_allowed": False, "network_access": False,
            "security_state_may_advance": bool(os.environ.get("TECHLINE_CUSTODIAN_RUN_TOKEN")),
            "note": "Packets describe exact stored content and missing authenticated decisions. Source URLs and "
                    "recorded licenses are review leads; this command grants no permissions or consent."}


def markdown_text(value):
    """Render untrusted metadata as inert Markdown text."""
    text = html.escape(str(value), quote=True)
    return "".join(char if ord(char) >= 32 and ord(char) != 127 and char not in DIRECTION_CONTROLS else " "
                   for char in text).replace("|", "&#124;").replace(
        "[", "&#91;").replace("]", "&#93;").replace("`", "&#96;")


def packet_markdown(row):
    lines = [f"# Item {row['packet_number']}: {markdown_text(row['headline'])}", "",
             "UNSIGNED PRIVATE WORK LIST. No human decision, appointment, signature or approval is supplied.", "",
             f"Record: {markdown_text(row['id'])}", f"Snapshot SHA-256: {row['canonical_snapshot_sha256']}",
             f"Record JSON SHA-256: {row['canonical_record_sha256']}",
             f"Classification: {row['classification']} (requires signed classification review)",
             f"Publication date: {row['publication_date_as_recorded']} / {row['publication_date_reliability']}",
             row["date_evidence_limit"], "", "## Original sources and rights", ""]
    for source in row["sources"]:
        lines.extend(f"- {field}: {markdown_text(source[field])}" for field in (
            "source_item_id", "source_identity", "publisher", "author_as_recorded", "original_url",
            "canonical_url", "published_at", "fetched_at", "missing_publication_time", "source_model_sha256",
            "rights_policy_sha256", "metadata_rights", "extractive_summary_rights", "attribution_obligations",
            "rights_uncertainty"))
        lines.append("- Recorded rights policy: " + markdown_text(json.dumps(source["recorded_rights_policy"])))
        lines.extend("- Rights evidence lead: " + markdown_text(url) for url in source["rights_evidence_urls_to_review"])
    lines.extend(["", "## Exact existing extractive content", ""])
    lines.extend("- " + markdown_text(bullet) for bullet in row["summary_bullets_as_recorded"])
    lines.extend(["", markdown_text(row["broader_summary_as_recorded"]), "",
                  "Ellipsis fields: " + markdown_text(", ".join(row["ellipsis_fields"]) or "none detected"),
                  "Provenance as recorded: " + markdown_text(json.dumps(row["extractive_provenance_as_recorded"])),
                  "", "## Limits, facts and editorial work", "", row["limitations_review"]])
    lines.extend("- Recorded limitation: " + markdown_text(limit) for limit in row["limitations_as_recorded"])
    lines.extend("- " + requirement for requirement in row["english_review_requirements"])
    lines.extend("- Fact: " + markdown_text(json.dumps(fact, ensure_ascii=False)) for fact in row["claim_verification_queue"])
    lines.extend("- Number: " + markdown_text(json.dumps(number)) for number in row["number_verification_queue"])
    lines.extend(["", row["bangla_requirements"], "", "## Authenticated decisions", "",
                  "| Source item | Language | Stage | Required role | State |", "|---|---|---|---|---|"])
    lines.extend("| " + " | ".join(markdown_text(stage[key]) for key in
                 ("source_item_id", "language", "stage", "required_role", "status")) + " |"
                 for stage in row["required_decisions"])
    lines.extend(["", "Exact bindings are in the companion JSON. Existing gate blockers:", ""])
    lines.extend("- " + markdown_text(reason) for reason in row["existing_gate_blockers"])
    lines.extend(["", "Human review notes: ____________________", "Evidence digest(s): ____________________",
                  "Proposed decision (unsigned): ____________________", "",
                  "Prepare/sign/validate/record through pipeline.research_cli and pipeline.authority only after "
                  "real appointment and a fresh independent checkpoint. A completed packet is never an approval."])
    return "\n".join(lines) + "\n"


def csv_cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def export_inventory(report, destination, *, root):
    """Create a fresh private directory outside every Git checkout; never overwrite."""
    destination = Path(destination).absolute()
    if scan_payload(report) or scan_payload({"destination": str(destination)}):
        raise AuthorityError("sensitive_output_refused", "Credential-shaped review output was refused")
    regular_path(destination / "boundary-check")
    if destination.is_relative_to(Path(root).absolute()) or any((p / ".git").exists() for p in
                                                              (destination, *destination.parents)):
        raise AuthorityError("private_output", "Review exports must stay outside Git checkouts and public assets")
    files = {"inventory.json": json.dumps(report, ensure_ascii=False, indent=2) + "\n"}
    buffer = io.StringIO(newline="")
    columns = ["id", "headline", "batch", "classification", "canonical_record_sha256", "original_urls",
               "publication_date_as_recorded", "publication_date_reliability", "has_ellipsis",
               "limitations_count", "bangla_present", "missing_stages", "publication_allowed"]
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in report["items"]:
        values = {**row, "original_urls": " | ".join(s["original_url"] for s in row["sources"]),
                  "limitations_count": len(row["limitations_as_recorded"]),
                  "missing_stages": " | ".join(s["stage"] for s in row["missing_decisions"])}
        writer.writerow([csv_cell(values[column]) for column in columns])
        stem = f"item-{row['packet_number']:03d}"
        files[stem + ".json"] = json.dumps(row, ensure_ascii=False, indent=2) + "\n"
        files[stem + ".md"] = packet_markdown(row)
    files["inventory.csv"] = buffer.getvalue()
    lines = ["# Private content review batches", "", report["meaning"], "",
             f"Snapshot SHA-256: {report['snapshot_sha256']}",
             f"Records: {report['record_count']}; eligible: {report['eligible_count']}", "",
             "Start with source-rights and resolve date/rights exceptions before downstream editorial review. "
             "Batches contain up to six exact records and confer no authority.", ""]
    for row in report["items"]:
        lines.append(f"- Batch {row['batch']}, item-{row['packet_number']:03d}.md: " + markdown_text(row["id"]) +
                     " / " + markdown_text(row["headline"]))
    files["README.md"] = "\n".join(lines) + "\n"
    manifest = {name: hashlib.sha256(value.encode("utf-8")).hexdigest() for name, value in files.items()}
    files["MANIFEST.json"] = json.dumps({"version": 1, "files": manifest, "publication_allowed": False}, indent=2) + "\n"
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        target = regular_path(destination / name)
        with target.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
    return {"status": "PASS", "exported_records": report["record_count"], "file_count": len(files),
            "destination": str(destination), "snapshot_sha256": report["snapshot_sha256"],
            "publication_allowed": False}


def main(argv=None):
    parser = ReportArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--expected-snapshot-sha256")
    parser.add_argument("--export", type=Path, help="Fresh private directory outside any Git checkout")
    args = parser.parse_args(argv)
    try:
        report = inventory(args.root, expected_sha256=args.expected_snapshot_sha256)
        detections = scan_payload(report)
        if detections:
            print(json.dumps(refusal(detections), ensure_ascii=True))
            return 1
        result = export_inventory(report, args.export, root=args.root) if args.export else report
        detections = scan_payload(result)
        if detections:
            print(json.dumps(refusal(detections), ensure_ascii=True))
            return 1
        print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(json.dumps({"status": "FAIL", "code": getattr(error, "code", type(error).__name__),
                          "detail": "Inventory refused; preserve existing files and inspect inputs or destination",
                          "publication_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
