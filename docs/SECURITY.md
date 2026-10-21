# Security implementation

The [operational trust limits](PHASE11_TRUST_LIMITS.md) correct Phase 10's
independent-custody and freshness claims. Production anchor verification remains
blocked until authenticated independent current-state evidence is supported.
Recovery preflights bounded allowlisted packs and refuses existing destinations.
The 2026-10-21 advisory reassessment verified npm's 4.3.0 tarball integrity and
reproduced all five restricted max-stale cases upstream. Retain the locked local
patch and the 2026-11-03 reassessment deadline; a clean audit is not proof of a fix.

Use ignored `.env` or GitHub production environment secrets. The example contains blank values. Inference/deploy credentials are separate. Source scanning finds common keys/private keys; build scanning rejects secret names or configured values in public assets. Enable repository secret push protection when publishing.

Fetching is HTTPS-only and allowlisted, rejects credentials/nonstandard ports/private destinations, validates every DNS answer and pins the selected public IP while retaining TLS SNI. Multicast and deprecated IPv6 site-local addresses are explicitly blocked despite Python marking them global. Redirect/MIME/size/time/domain-rate protections apply. HTML requires explicit permission and robots approval. Locked httpx/httpcore backend integration must be rechecked during upgrades.

HTML/scripts are stripped before storage. UI renders escaped plain text without raw HTML Markdown. External links use HTTPS and safe attributes. Source content is untrusted evidence in prompts; models receive no tools/credentials/write access. Checks cover schema, numeric/citation/evidence/expiry consistency and source conflicts. Semantic truth still benefits from review.

CSP uses exact inline Astro hydration hashes with no unsafe-inline or unrestricted eval. Pagefind requires the narrower wasm-unsafe-eval capability. Optional analytics adds only Cloudflare beacon/reporting origins. HSTS/nosniff/referrer/frame/permissions policies are built into `_headers`. Local preview uses the same policies except HTTP localhost upgrading.

PR CI has no production secrets, read-only repository permissions and no pull_request_target. Production runs only on the default branch, serializes jobs and deploys after validation. Every third-party Action is pinned to a full SHA. Dependabot and CodeQL are configured.

## Temporary transitive patch — reviewed 2026-10-04, expires 2026-11-03

### Phase 10 reassessment on October 20

The advisory record is now structured and machine-readable in
`config/security-advisories.json`, and the launch-readiness report reads it
so the mitigation state cannot silently drift from the documentation.

Fresh official npm metadata on the access date still identifies
`http-cache-semantics` **4.3.0** as `dist-tags.latest`. The
[GitHub advisory](https://github.com/advisories/GHSA-ch52-4w7c-c8xp) still
lists affected versions `<= 4.2.0` and **patched versions: None**, last
updated 2026-10-02, severity High (CVSS 4.0 8.7). The
[maintainer PR](https://github.com/kornelski/http-cache-semantics/pull/58)
remains closed and disputes the premise; a separate
[dispute thread](https://github.com/github/advisory-database/issues/10139)
records the same objection.

**Interpretation is unchanged.** Being outside the database's listed range is
not a verified fix. The locked local patch
`patches/http-cache-semantics@4.3.0.patch`, the 14 regression tests and the
explicit `pnpm audit:dependencies` gate all remain required, and the
**2026-11-03** deadline stands. No dependency version, override or lockfile
entry was changed by Phase 10, and no broad upgrade was attempted.

Exposure remains build-time only: the deployed architecture is asset-only
static output with no shared cache, so the advisory's cross-user
cache-disclosure path is not reachable in production.

Next maintenance action, before 2026-11-03: re-download the current upstream
release, verify its SHA-512 against npm metadata, re-run the five restricted
max-stale probes against the unmodified implementation, and re-read the
advisory text. Remove the patch only when the unmodified upstream release
rejects every probe, or when Astro removes the dependency.

### Reassessment on October 20

The Phase 9 review fetched current official npm metadata and verified the SHA-512
integrity of the 4.3.0 tarball. It remains the latest release; the [advisory](https://github.com/advisories/GHSA-ch52-4w7c-c8xp)
still lists no patched version and the [maintainer PR](https://github.com/kornelski/http-cache-semantics/pull/58)
remains closed. All five isolated restricted-response max-stale probes still
allow reuse in unpatched upstream code; the installed locked patch refuses them,
including cookie stale-while-revalidate and stale-error fallbacks. Keep the
existing patch and **2026-11-03T00:00:00Z** reassessment deadline.

Offline editorial signatures do not add a server, remote-image path, shared
HTTP response cache or reader dependency. Source/build/deployment architecture
remains static. No dependency version or lockfile was changed by this audit.
Empty registry results are not evidence that the upstream behavior is fixed.

### Reassessment on October 13

The owner-directed UI correction passed source/build security scans and full/production Node audits with zero registry advisories. A frozen Python export of 31 requirements passed pip-audit 2.10.1. The explicit dependency gate still reports the local mitigation rather than silently treating that clean audit as an upstream fix.

Fresh official npm metadata still identifies http-cache-semantics 4.3.0 as latest. Its tarball integrity was verified and all five restricted max-stale probes still returned unsafe reuse in the unpatched implementation; the cookie probe also permits stale-while-revalidate and stale error reuse. The locked patch and 14 regression tests remain. The [GitHub database](https://github.com/advisories/GHSA-ch52-4w7c-c8xp) still lists no patched version, and the [closed maintainer PR](https://github.com/kornelski/http-cache-semantics/pull/58) still disputes the premise. Retain the **2026-11-03** reassessment deadline.

The headline timer is local UI code using static published story data. It adds no network polling, provider request, external runtime dependency, application binding or shared response cache. Static exposure and strict headers remain unchanged. [Exact validation](IMPLEMENTATION_VALIDATION.md).

### Reassessment on October 12

The fresh complete-tree audit initially failed on [Sharp GHSA-wq5f-xc86-pv6w](https://github.com/advisories/GHSA-wq5f-xc86-pv6w), published to the advisory database on October 6. The installed path was `wrangler@4.147.0 -> miniflare@5.20261001.0-alpha -> sharp@0.35.4`. The advisory identifies 0.35.5 as fixed. Miniflare pins the older version exactly, so `pnpm-workspace.yaml` overrides only that exact parent path to Sharp 0.35.5. Frozen installation and deployment dry-run check compatibility. No broad suppression or unrelated framework upgrade was introduced. Full and production registry audits subsequently report zero advisories.

The official npm registry still identifies http-cache-semantics 4.3.0 as latest. Its tarball integrity was verified against npm metadata before testing the unpatched implementation. `max-stale` was accepted in five probes: shared Set-Cookie, private, no-cache, proxy-revalidate and s-maxage=0. The cookie probe also accepted stale-while-revalidate and stale error reuse. The patched installation rejects those probes and retains all 14 regression tests. The [GitHub advisory](https://github.com/advisories/GHSA-ch52-4w7c-c8xp) still provides no verified patched version, and [the maintainer's closed PR](https://github.com/kornelski/http-cache-semantics/pull/58) disputes the premise. Retain the conservative patch, explicit dependency gate, static exposure review and **2026-11-03** deadline. An empty registry audit is not proof of a behavioral fix.

Source-transform and summary policy revisions invalidate processed evidence after release prose cleanup. Candidate data still passes unchanged numeric, attribution, evidence and schema validation. No visitor inference, remote-image or SSR path was added.

[GHSA-ch52-4w7c-c8xp / CVE-2026-93748](https://github.com/advisories/GHSA-ch52-4w7c-c8xp) lists **http-cache-semantics <=4.2.0** with no fixed version. Exact installed chain is now `@intelligence/web -> astro@7.3.5 -> http-cache-semantics@4.3.0`, with a locked local patch. The advisory is high severity (CVSS 3.1 7.5 / CVSS 4.0 8.7). It concerns reuse of shared responses/cookies through client-controlled max-stale directives.

**Upstream 4.3.0 is not a verified security fix.** Published on October 4, it changes status reporting and Vary matching; comparison of the official npm tarballs confirms that the reported reuse logic is unchanged. Controlled requests against unpatched 4.3.0 still accept max-stale for cookie, private, no-store, proxy-revalidate and s-maxage=0 responses. The [maintainer closed PR 58 and disputes the CVE](https://github.com/kornelski/http-cache-semantics/pull/58); the database has not marked a fixed version. We retain conservative mitigation rather than treating a version outside its current range as proof of safety.

The deployed code path is unaffected: output is static, Wrangler has no application entrypoint, binding, authenticated response cache or remote image route. Astro imports this package only in its build-time remote-image utility; this project has no remote images. That utility calls `storable()` and `timeToLive()`, not vulnerable request-evaluation methods. The module is absent from browser assets. This conclusion must be reassessed if SSR, remote images or an application cache is added.

Removing the transitive package breaks Astro imports. Astro 7.3.5 requires `^4.2.0`; upgrading naturally to compatible 4.3.0 supplies its other fixes without an override. Substituting a different cache implementation would introduce an unverified API change. The compatible mitigation is `patches/http-cache-semantics@4.3.0.patch`, pinned by the lockfile. It rejects private/no-store/no-cache, shared cookie responses without explicit public permission (including immutable cookies conservatively), and restricted stale responses before max-stale, stale-while-revalidate or stale-if-error reuse. Revalidation must match URL/method/Vary. Fourteen tests cover security cases, serialization and legitimate public reuse; all pass on the patched 4.3.0 installation.

**Raw `pnpm audit` and `pnpm audit --prod` now report zero advisories and exit 0 because 4.3.0 is outside the database's listed range. Nothing is globally ignored. This does not eliminate the known upstream behavior.** `pnpm audit:dependencies` scans the complete tree and always visibly reports the local mitigation, including when raw audit is empty. It checks the exact installed versions, public cache API behavior and static architecture, rejects unreviewed advisories or dependency changes, and expires on 2026-11-03. If the database extends this advisory to 4.3.0, only the exact reviewed patched Astro path can be accepted; all other findings fail. Remove the patch and special gate only after a compatible upstream release passes the unchanged exploit tests, or Astro removes the dependency. Regenerate the lockfile and rerun the complete audit/build. Reassess by the expiry date if upstream remains disputed.

The final audit also removed six additional advisories from the previous Lighthouse CI dependency tree (`tmp`, `uuid`, `extract-zip`, `basic-ftp`) by replacing that obsolete wrapper with pinned Lighthouse 13.5.0 and a small local runner using Playwright's existing browser lifecycle. No broad overrides or suppression were used. Source and generated-content scans, full dependency audit and browser/performance checks run in CI.

Python locked production and full dependency sets passed pip-audit during local validation. Scans are time-sensitive and should be repeated before launch.

## Release hardening, 2026-10-14

External publication is disabled. Exact repository/visibility/account/Worker/origin/approved revision, budget, rights, license and backup decisions are checked before provider work and deployment. Ingestion/CodeQL schedules were removed; Dependabot remains a dormant planning template. Fork PRs have no publication credentials. Inference defaults off even if keys exist. Cloudflare delivery contains static assets only; no privileged runtime endpoint or browser inference key is introduced.

Fresh registry/Python audits are recorded in [release verification](RELEASE_VALIDATION.md). The visible locked cache mitigation remains required and expires for reassessment on 2026-11-03; zero advisories is not proof of an upstream fix. No security scan proves legal content rights, complete semantic summary accuracy, physical-device accessibility or edge configuration. Off-machine backups and paid quota durability remain owner-gated limitations.

The October 14 reassessment downloaded the official 4.3.0 tarball, verified its SHA-512 integrity and read only the two allowlisted package files outside the repository. All five unpatched private/cookie/revalidation max-stale probes remain unsafe; the locked local patch stays required. [Exact current audit evidence](RELEASE_VALIDATION.md).
