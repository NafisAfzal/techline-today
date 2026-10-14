# Backup and recovery readiness

**Independent source/data restoration passed on 2026-10-14**, using the owner's private Google Drive upload/download. [Gate A results](GITHUB_GATE_A_RELEASE.md) describe the proof and its limits; clean-machine toolchain/account recovery and hosted rollback remain untested. Keep backup generations outside public Git. The first audit pack is preserved but invalid under the corrected policy because it contains an unreferenced synthetic archive; use the subsequently verified generation.

## Manifest and classification

| State | Git/public policy | Regenerable? | Sensitive / irreplaceable | Disaster recovery requirement |
|---|---|---|---|---|
| Application/pipeline source, locks, config, feed/publisher registry, prompts, schemas, deployment policy | Prospective Git files; currently no commits | Installed dependencies regenerate; original code/config does not | Ownership-sensitive until approved; irreplaceable uncommitted work | Reviewed source export now, then approved Git revision plus a separate off-machine source copy |
| `content/generated/snapshot.json` and last-live snapshot | Ignored | Current feed subset partly regenerable; historical corrections and evidence may disappear upstream | Publisher text; corrections/history can be irreplaceable | Verified live-data pack |
| `.cache/state-live.json` | Ignored | Conditional request state regenerable; retained items/dedup history may not be | Public-source extracts; never put secrets here | Include in data pack |
| Referenced monthly/yearly archives | Ignored | Historic evidence may be unavailable from feeds | Publisher text, corrections; potentially irreplaceable | Referenced archive bundles and annual indexes are required by manifest validation |
| Translation cache | Ignored | Could be regenerated with approved provider, time and cost; editorial review may be irreplaceable | Publisher-derived text; future editorial review sensitive | Include in data pack when present |
| Provider reservations/usage | Ignored | Cannot safely regenerate a monetary ledger from feeds | Quota metadata; critical if inference is later allowed | Include when present; durable ledger required before enabling AI |
| Generated report/briefing | Ignored | Mostly regenerable | Operational/source metadata | Include for incident evidence |
| Unreferenced archive files | Ignored, preserved locally | Unknown provenance | May be synthetic, obsolete or user data | Quarantine/review separately; never export as validated live history |
| `.env`, API/deployment keys, account recovery codes | Ignored; excluded from all ordinary exports | Tokens should be reissued; recovery codes may be irreplaceable | Secret | Separate encrypted password manager/recovery kit, owner-controlled MFA and recovery contacts |
| Dist, indexes, dependencies, fixtures and browser captures | Dist/dependencies/traces ignored; curated screenshots and synthetic source fixtures prospective Git | Regenerable except evidence captures | Captures can include publisher material | Code/lock/data restoration plus rebuild; approved release bundle useful for rollback |

## Secure local generation

From the project root in Windows PowerShell, use a new destination each time:

```powershell
$generation = '.cache/operator-backups/REPLACE-WITH-UNIQUE-GENERATION'
$restored = '.cache/operator-restore/REPLACE-WITH-UNIQUE-GENERATION'
py -3.12 -m uv run python -m pipeline.backup export $generation
if ($LASTEXITCODE -ne 0) { throw 'Backup export failed' }
py -3.12 -m uv run python -m pipeline.backup verify $generation
if ($LASTEXITCODE -ne 0) { throw 'Backup integrity failed' }
py -3.12 -m uv run python -m pipeline.backup restore $generation --destination $restored
if ($LASTEXITCODE -ne 0) { throw 'Restoration failed' }
```

Every data-pack manifest records allowed paths, byte counts and SHA-256. Verification checks live contracts, referenced month/year membership, checksums and unsafe/symlink paths. Restoration only targets an empty directory. Existing files and backups are never deleted. Unreferenced synthetic archives are excluded, not silently relabelled as live data.

Before public source control exists, the preparation pass also copies the prospective public file set into a private local source generation with hashes. After a reviewed commit, produce a source archive at a new unique destination; never overwrite a prior generation:

```powershell
$sourcePack = '.cache/operator-source-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.zip'
if (Test-Path -LiteralPath $sourcePack) { throw 'Choose a new generation' }
git archive --format=zip --output=$sourcePack APPROVED_SHA
```

That archive contains committed source only; combine it with the matching data pack, lockfiles, operator record and separate secret recovery procedure. Never mistake it for a full ignored-state backup.

## Independent storage policy

Recommended destination: an owner-controlled encrypted removable drive stored apart from the laptop, or an existing encrypted/versioned storage account with access controls. No paid subscription or third-party upload is authorized. Use 14 daily, 8 weekly and 12 monthly successful generations, subject to actual capacity. Preserve at least one disconnected generation. Record source SHA, manifest checksum, successful Cloudflare version, timestamp and operator. Keep encryption keys in a separate recovery location; do not commit them or depend solely on the failed laptop.

Copy only after source/content approval, verify hashes at the destination, and restore on another machine into an empty directory. Complete that independent restoration before marking `durable_backup_verified=true`; repeat quarterly and after backup-tool changes. A same-laptop directory, GitHub repository, evictable Actions cache or short-retention artifact does not meet this requirement.

## Recovery sequence and assumptions

Disable publication/schedule; preserve the failing generation. Obtain the reviewed source revision and separate credentials; verify/restore its matching data pack in an isolated checkout. Compare the restored manifest, validate the snapshot and archives, rebuild, run content/security/site/smoke gates, and use the release approval gate before any deployment. Restore matching pipeline state after a hosted rollback so the bad edition is not immediately republished.

Planning assumptions, not measured SLAs: data RPO up to 24 hours with daily off-machine exports; current-edition fallback can lag six hours plus scheduler delays. History not retained by feeds cannot be reconstructed after a missed backup. RTO target 2–4 hours when source, data, credentials, network and a working toolchain are available; account recovery or missing encryption keys can make it much longer. The local checksum proof measures file recovery, not that full recovery time.

The pipeline writes individual archives before replacing snapshot/state; a local I/O interruption can leave mixed generations. Restore the entire prior data generation rather than continuing collection from partly written files. Failed production jobs retain the previous hosted edition and successful cache.

## Hosted cache loss

Workflow state now uses a verified `production-data-v3` pack. Legacy v1 caches are deliberately not imported. Missing cache blocks publication; initial seeding is a separately approved one-time action, never a substitute for lost history. After cache eviction, use the chosen durable destination to restore locally and publish manually through the gate. Resuming scheduled operation additionally requires a reviewed, destination-specific cache-import procedure. That part cannot be completed until a durable destination and its access policy are selected; keep scheduling disabled until it is tested. Public base-branch caches are accessible to fork workflows and may contain only rights-cleared, nonconfidential state.

## Owner launch recovery generation

The current clean live edition has a six-file manifest: snapshot, run report, Markdown briefing, live conditional/dedup state, last live snapshot and live translation cache. After a real deployment, an optional publication receipt is a seventh file; absent provider usage remains absent. Referenced archives/provider state are included only when present and valid. The historical seven-file contaminated pack is retained privately as incident evidence, never the release restore source.

A dated local package and source ZIP are verified in an isolated directory. Exact private paths/hashes/sizes are recorded in `.cache/owner-launch/recovery-location.json` and supplied to the owner separately; personal machine paths are excluded from public documentation. Source contains frozen locks/config/prompts/fixtures/notices, not `.git`, secrets or historical captures. Data remains a separate private pack because its rights differ. Restore source into an empty checkout, install frozen dependencies, verify/restore the matching live-data pack into an empty staging directory, copy only its manifest paths into the isolated checkout, then run validation/content/build/security checks. Keep local credentials outside the archive; recover scoped tokens via account recovery/password manager and rotate lost tokens.

Independent verification was completed on 2026-10-14 from the owner's private Google Drive upload/download. The supplied download matched the known outer SHA-256; fresh isolated source/data extraction and restoration matched every manifest entry and passed snapshot/content checks. Cloud storage provenance is owner-attested; no cloud account was accessed by the agent. [Gate A evidence and limitations](GITHUB_GATE_A_RELEASE.md). Keep that independent generation private and repeat recovery drills after relevant changes. Clean-machine toolchain installation, credential/account recovery and hosted rollback remain separate tests. Future generations should use owner-controlled access-controlled storage, verify hashes at the destination, and restore from that stored copy; same-machine relocation alone is insufficient.
