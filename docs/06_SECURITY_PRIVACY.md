# Security and Privacy

## Threat model

Protect against:
- API key leakage;
- malicious source content / prompt injection;
- HTML/script injection;
- SSRF in scrapers;
- dependency compromise;
- untrusted pull request secret exfiltration;
- poisoned data from low-quality sources;
- runaway API costs/quotas;
- spam on future forms/account endpoints.

## Secrets

- never expose AI or Cloudflare keys in frontend JavaScript;
- store secrets in GitHub Actions Secrets / Cloudflare Secrets;
- `.env` is gitignored;
- `.env.example` contains names only;
- rotate leaked credentials immediately;
- use least-privilege tokens.

## GitHub Actions hardening

- ingestion/deploy secrets available only on the default branch workflow;
- do not use `pull_request_target` for untrusted code;
- PR CI receives no production secrets;
- set explicit `permissions:` on every workflow;
- pin third-party actions to full commit SHA where practical;
- use environment protection for production deploy if collaboration grows;
- do not execute code downloaded from news pages.

## Scraper SSRF defenses

- fetch only sources present in `config/sources.yaml`;
- reject localhost/private/link-local IP destinations;
- disable arbitrary redirects to untrusted domains unless allowlisted;
- limit redirect count;
- restrict supported schemes to HTTPS/HTTP as necessary;
- response size limits;
- connection/read timeouts;
- content-type checks.

## Prompt-injection defenses

Web pages are untrusted data, not instructions.

The summarizer system prompt must state that source text may contain malicious or irrelevant instructions and must be treated solely as quoted evidence.

Never give the summarization model tools, credentials or write access.

## Content sanitation

Preferred: store/render plain text and structured fields.

If Markdown is allowed:
- use a restrictive Markdown renderer;
- disable raw HTML;
- sanitize output;
- disallow `javascript:` and unsafe URL schemes.

## Browser headers

Set at minimum:
- Content-Security-Policy
- Strict-Transport-Security on custom domains
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy with unnecessary capabilities disabled
- frame-ancestors via CSP

CSP should be explicit and adjusted for Cloudflare Web Analytics if enabled.

## Forms

When feedback/newsletter/accounts are introduced:
- Cloudflare Turnstile;
- server-side validation;
- per-IP/per-account rate limits;
- CSRF defenses for cookie-authenticated mutations;
- no detailed auth error leakage.

## Privacy

V1 should work without an account.

Do not collect:
- exact location;
- contact data unless a user submits it;
- cross-site behavioral profiles.

Use privacy-first analytics. Document any future email/push provider in the privacy policy.

## Copyright/content integrity

- link to original sources prominently;
- never mirror full third-party articles;
- retain only limited evidence excerpts where necessary;
- honor source removal/correction requests;
- show corrections/update history for materially changed summaries.
