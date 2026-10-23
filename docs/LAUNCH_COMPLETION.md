# Local launch operations

Local preparation does not provision human authority or authorize publication. Keep keys, item packets, signed journals, custody state and account evidence outside Git and Astro public directories. Reuse the existing authority and research CLIs. Readiness labels are PASS, FAIL, BLOCKED or INCONCLUSIVE; synthetic rehearsals do not provision production.

The critical path is owner custody, independently authenticated current checkpoint, scoped reviewer appointment, item rights and factual/editorial review, authenticated eligibility, a local research candidate, then separately authorized preview. Use the [owner runbook](PHASE8_OWNER_RUNBOOK.md), [research workflow](RESEARCH_APPROVAL_WORKFLOW.md), and [trust limits](PHASE11_TRUST_LIMITS.md).

The existing Ed25519 registry enforces grants, role/language/item/source scope, expiry, rotation and revocation. The journal holds authenticated decisions. Independent custody adds currency; another local folder or Git history cannot establish it. Static research output consumes the verified item selection. Recovery and observation rehearsals demonstrate software behavior, not a running newsroom.

## Two launch paths

The smallest honest public proposal is an English research/reference catalogue with individually approved metadata and extractive summaries. Its distinct policy remains disabled. Preprint labels, source attribution and dates must be truthful. If no item clears review, the real eligible count stays zero; an empty catalogue is not a completed content launch.

Full current-news publishing additionally requires active licensed publishers, genuine current-news evidence, operating reviewers, independent checkpoints, genuine observations, scheduling/monitoring, backup recovery and production authorization. Research metadata cannot satisfy these requirements. No live source activation or schedule is included in preparation.

## Cloudflare account verification — human owner

The intended architecture is Astro static assets on Workers Free, with separate preview and production Worker names. Local packaging verifies neither account ownership nor plan/billing. Record dated private evidence before requesting deployment:

1. Personally verify intended account ID and ownership. Enable two-factor authentication and retain recovery codes securely. Review account members and recovery contacts.
2. Inspect Workers & Pages plan, all subscriptions/invoices, payment settings and enabled billable products/add-ons. Confirm Workers Free. Static serving does not establish an account-wide spending cap. Inaccessible settings remain INCONCLUSIVE.
3. Choose workers.dev subdomain and distinct preview/production names/origins matching release configuration. Example URLs reserve nothing. Keep version preview URLs disabled pending separate review.
4. Inspect Workers Builds/Git integration and GitHub installed-app permissions. Initial proposal is manual exact-revision publication. Automatic deployment on push risks unapproved content. Do not connect GitHub or enable automatic builds during preparation.
5. Decide whether preview may be public. Noindex is not access control. Confidential review requires verified Access coverage of every hostname/asset route, or continued local review. An untested Access rule is not verified protection.
6. Confirm static-only configuration: no application Worker entrypoint, AI, storage, databases, paid bindings or cron. Inspect packaged assets and provenance against conservative file, size, rollback and client bundle budgets.
7. Review CSP hashes, HSTS, frame denial, nosniff, referrer policy, robots/noindex and no-store. Later edge verification must include homepage, direct articles, search, RSS, sitemap, missing paths and both locales.
8. Separately approve destination, cost assumptions, source provenance, exact SHA and asset manifest. Only then provision minimal credentials/resources. This preparation creates neither.

Official references checked 2026-10-23: [static billing/limits](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/), [Workers limits](https://developers.cloudflare.com/workers/platform/limits/), [version URLs](https://developers.cloudflare.com/workers/versions-and-deployments/version-urls/), [Access configuration](https://developers.cloudflare.com/workers/configuration/access/). Static requests and Worker execution have different billing. Actual subscriptions remain owner-verification work.

## Future preview operation and recovery

Before any authorized upload, retain reviewed revision, lockfiles, canonical hash, eligibility evidence, current custodian receipt, complete asset digest manifest and known-good previous version outside CI caches. Use a frozen install in an isolated checkout, disabled AI, no public environment injection, research verification and local workerd. Wrangler `deploy --dry-run` packages locally; it proves neither account nor edge readiness.

After separately authorized preview deployment, verify HTTPS routes, headers, noindex, access restrictions, asset hashes, excluded-item absence, mobile/keyboard behavior and source links. Record genuine observations over the intended window. Production needs a further explicit publication approval.

Rollback uses the retained approved bundle and known-good Cloudflare version under explicit authorization, followed by route/header/content checks. Local emergency STOP freezes new approvals but cannot remove hosted bytes. A content incident also needs signed withdrawal/revocation and a new checkpoint. Emergency disable requires an authorized operator to disable every public route, workers.dev and version URL, or deploy a reviewed empty holding bundle, then verify externally. Preserve evidence; reconcile interrupted deployment against the actual hosted version before retrying.

Review dashboard usage/subscriptions after preview and periodically after launch. Record who can disable delivery and recover account access. Alerts are observations, not assumed spending caps. Inference, cron and paid integrations stay absent until separately authorized.
