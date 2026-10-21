# Phase 10 — source intelligence, rights evidence and onboarding

Status: **research only**. Nothing in this document grants rights, activates a
source, approves a candidate or authorises republication. No real reviewer has
been appointed.

## Coverage the newsroom actually needs

The editorial categories the platform must eventually cover are artificial
intelligence and machine learning, cybersecurity, consumer technology, software
engineering and developer tools, cloud and infrastructure, research
publications, semiconductors and hardware, and the Bangladesh technology
ecosystem.

The shortlist below is deliberately small. A small team on a limited budget
cannot verify, refresh and review hundreds of feeds, and an unverified feed is
a liability rather than coverage.

## What was actually checked, and how

Official publisher feeds, official API documentation and official
licence/terms pages were fetched directly on **2026-10-20**. Publisher article
bodies were not fetched for reuse, no paywall was bypassed and no robots
restriction was circumvented. The structured record lives in
`config/source-research.json` with `status: RESEARCH_ONLY`.

| Candidate | Technical availability | Licence | Confidence |
|---|---|---|---|
| `cisa_kev` — CISA Known Exploited Vulnerabilities | Verified | **CC0-1.0**, publisher licence file retrieved | High |
| `arxiv_metadata` — arXiv descriptive metadata | Verified by the prior release | **CC0-1.0**, metadata only | High |
| `cloudflare_docs` — Cloudflare documentation | Verified by the prior release | **CC BY 4.0**, attribution required | High |
| `osv_dev` — OSV.dev | Verified | **Apache-2.0 for the infrastructure only**; the aggregated data terms are unconfirmed | Medium |
| `nvd_api` — NVD API 2.0 | Verified (rate limits documented) | **NOT_VERIFIED** — the terms-of-use page did not render retrievable text | Low |
| `cisa_advisories` — CISA advisory feed | Verified | **NOT_VERIFIED** — the site terms grant no republication licence | Medium |
| `ubuntu_usn` — Ubuntu Security Notices | Verified | **NOT_VERIFIED** — the policy clause governing notice text was not isolated | Medium |
| `bd_cert` — Bangladesh CERT | **NOT_PERFORMED** — unreachable from this workstation | NOT_VERIFIED | Low |
| `ict_division_bd` — ICT Division Bangladesh | **NOT_PERFORMED** — unreachable from this workstation | NOT_VERIFIED | Low |

Unresolved legal questions are recorded per candidate. Three of them are
material:

1. **The CISA KEV CC0 licence covers the KEV catalogue only.** It does not
   cover the advisory feed. A naive RSS adapter would capture the full
   advisory body from the feed description, which is exactly the reuse that
   has not been cleared.
2. **The OSV licence covers the infrastructure, not automatically the records
   it serves.** The contributing data sources — including the CVE Program
   terms — were not separately retrieved.
3. **NVD description text is publisher prose.** Identifier reuse and
   description reuse are different questions.

Two coverage categories have no candidate at all: consumer technology and
semiconductors/hardware. No openly licensed current-news feed with an explicit
republication grant was identified for either. Bangladesh coverage is
unverified because both official bodies were unreachable from this workstation.

## Never treat these as authorisation

- An accessible RSS feed is not a republication licence.
- An API key is not a copyright licence.
- A public web page is not permission to republish.
- A US Government publisher is not automatically free of third-party content;
  the KEV licence itself warns that linked third-party material keeps its own
  terms.

## The evidence workflow

```text
research shortlist  ->  candidate proposal  ->  technical validation
      ->  rights pending  ->  evidence report  ->  editorial queue  ->  refused
```

```sh
uv run python -m pipeline.source_onboarding register-research --root .
uv run python -m pipeline.source_onboarding evidence --root .
uv run python -m pipeline.source_onboarding report --root .
```

`register-research` records a proposal per researched candidate with a tool
label as the actor. It never names a person, never appoints a reviewer and
never grants a permission. `evidence` produces the reviewer-facing report.

Every researched candidate is registered as `RIGHTS_UNVERIFIED` with **every
permission unknown**. Unknown is never treated as satisfied.

## What the evidence checker reports

| Code | Blocking? | Meaning |
|---|---|---|
| `license_evidence_missing` | Yes | No publisher terms or licence document is recorded |
| `rights_reviewer_missing` | Yes | No named human rights reviewer, or no decision time |
| `article_body_reuse_unsupported` | Yes when unknown, advisory when refused | Whether article bodies may be republished is unresolved |
| `image_rights_unknown` | Yes | Image reuse rights are unknown; unknown must never become media-publishable |
| `ai_permissions_unclear` | Yes | Whether the material may go to a paid AI provider is unresolved |
| `attribution_unverified` | Yes | The publisher's attribution requirement has not been verified |
| `stable_identity_missing` | Yes | The candidate has no stable publisher identity |
| `terms_review_stale` | Yes | The recorded terms review is older than the operator freshness policy |
| `terms_never_reviewed` | Yes | The terms have never been reviewed |
| `endpoint_unvalidated` | Yes | The endpoint has never been confirmed to work |
| `retention_policy_unresolved` | Yes | The permitted retention period is unresolved |
| `rights_status_not_evidence_recorded` | Yes | The candidate's rights status is not recorded evidence |
| `image_reuse_refused` / `ai_submission_refused` | Advisory | A documented refusal, so the constraint is visible |

Each finding names the field, the required decision and the required role
(`source-rights`). The report never reports `publication_allowed`,
`activation_allowed` or `ai_submission_allowed` as true.

## Promotion stays structurally blocked

A candidate that has every metadata field populated is still not approved.
Promotion into `RIGHTS_EVIDENCE_RECORDED`, `ELIGIBLE_FOR_ACTIVATION` or
`ACTIVATED` raises `AuthorityUnavailable`: those transitions require an
authenticated reviewer authority that this project does not have. Preserved
unsigned proposals reconcile only with a signed source eligibility decision
for the exact candidate digest, and historical suspension or revocation stays
a blocker.

## Safe fixtures

Integration tests use synthetic candidates only. No third-party content is
submitted to a paid model and no live collection is scheduled. The fixture
path is:

```text
candidate feed -> technical metadata validation -> rights pending
   -> evidence report -> editorial onboarding queue -> publication refusal
```

## What a human rights reviewer still has to do

For each candidate, read the publisher's own terms, decide the reuse scope
field by field, decide attribution, decide images, decide AI processing,
decide retention, record the evidence with its digest, and record the
decision with a name and a time. This project supplies the checklist and the
evidence trail, not the judgement.

Related: [adding sources](ADDING_SOURCES.md) ·
[rights review contract](RIGHTS_REVIEW_CONTRACT.md) ·
[content rights review](CONTENT_RIGHTS_REVIEW.md) ·
[newsroom operations](PHASE10_NEWSROOM_OPERATIONS.md)
