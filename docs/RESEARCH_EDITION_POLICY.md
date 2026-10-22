# Research/reference edition policy

Prepared against protected main `b85e8dd0747a32f98c32b51af47a0b5569b2e639`. This is a separate, disabled publication policy. It grants no publisher rights, appoints no reviewer and changes no news, ingestion, inference, source-onboarding or checkpoint authorization.

The canonical 37-record snapshot remains byte-for-byte unchanged, SHA-256 `d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5`. Its legacy build exception permits an unchanged local build; it is not item-level approval for a new public edition. The [production editorial check](../scripts/editorial-quality.mjs) still requires current news and must keep refusing this corpus.

## Eligibility decision

**Zero real records are eligible for this new edition.** All 36 arXiv research records and the one Cloudflare documentation reference are excluded until a separately reviewed authenticated research approval pathway verifies item scope and current authority. An allowlisted source, accessible URL, unsigned reviewer name, code commit, synthetic signature, old snapshot digest, or `publication_enabled` flag cannot supply that approval. The selector accepts no approval parameter and always reports real publication false. The configuration is descriptive and cannot activate an approval adapter.

| Corpus | Reuse assessment | New-edition publication decision |
|---|---|---|
| 36 arXiv records | Existing CC0 basis covers descriptive metadata; it does not cover e-print bodies, figures or PDFs. Review title/abstract-derived wording, authors, origin and preprint limitations per item. | Excluded: no verified item publication decision or current trusted research checkpoint; research approval adapter unavailable. |
| 1 Cloudflare reference | Existing CC BY 4.0 documentation basis requires attribution, license link and changes notice. Unknown original creator must remain unknown. | Excluded for the same authority gaps. Also review captured document revision, attribution, missing publication time, and outdated offer/pricing statements before any future reference release. |
| Other sources, news, advisories, translations, archives, trackers | No new rights or editorial scope inferred. | Excluded from this profile. No automatic source activation or AI submission. |

The [arXiv API terms](https://info.arxiv.org/help/api/tou.html) distinguish descriptive metadata from copyrighted e-prints. The [Cloudflare documentation license](https://github.com/cloudflare/cloudflare-docs/blob/production/LICENSE) supports the existing scoped attribution assessment. These checks confirm the stated reuse basis, not actual human publication consent. [Existing rights inventory](CONTENT_RIGHTS_REVIEW.md) and [review contract](RIGHTS_REVIEW_CONTRACT.md) retain their authority. Per-record diagnostic IDs and exclusions are saved only in the private preparation evidence.

## Required future approval design

Any real edition needs a separately reviewed implementation and new exact-SHA approval. It must verify authenticated item-bound rights decisions, source validation, editorial selection and a current trusted checkpoint, with revocation, expiry, evidence/content/policy binding and replay protection. Existing local checkpoints cannot be promoted to independent current authority. Preserve all risk-reducing local withdrawals and source suspensions. Missing or conflicting evidence denies.

Research and reference have explicit semantic scope: research preprints retain peer-review/replication limits; documentation remains reference with captured revision and verification time. A research edition need not claim current news. Any future research freshness rule belongs in this separate policy; never relax the existing news gate or reuse generation timestamps as publication dates. English remains canonical. Bangla UI is separate from story translation, which needs its own authorized processing and native review. No such adapter or approval is implemented here.

## Local rehearsal

`pnpm build:research` accepts only an isolated fixture snapshot whose stories and evidence are synthetic with reserved example source URLs. It selects synthetic research examples and reconstructs the evidence closure, dropping digests, trackers, archives and unrelated sources. It writes `apps/web/dist-research`, never the production output. The original input is read under the existing generation lock, never rewritten. The fixture pipeline must run only in a dedicated worktree; never overwrite a live workspace for testing.

All pages carry localized research/rehearsal and synthetic notices. RSS is labelled. Existing layout, navigation, accessible controls, local preferences, Pagefind/JSON search and English fallback remain. Every HTML route is noindex; robots disallows crawling; all responses carry `X-Robots-Tag` and `no-store`. Analytics and public environment injection are refused; CSP stays same-origin with exact inline hashes. Provenance binds source, input, assets, revision and profile. A rehearsal manifest fails ordinary production/preview verification.

Noindex is not access control. A future workers.dev deployment would be publicly reachable. Only synthetic or expressly eligible content may ever reach a rehearsal surface. Local loopback and Cloudflare edge behavior are different verification scopes.

The research verifier's `--publish` mode deliberately exits nonzero. Real eligibility is zero even if a config flag is edited. Existing `deploy` and `deploy:preview` retain their complete news/release gates and cannot publish this output.

See [Cloudflare preparation and exact future commands](RESEARCH_EDITION_PREVIEW.md). Nothing in this policy authorizes a push, PR, merge, account action, upload or deployment.
