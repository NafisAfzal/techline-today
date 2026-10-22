param(
  [Parameter(Mandatory=$true)][string]$AuditDirectory,
  [Parameter(Mandatory=$true)][string]$CanonicalSnapshot
)
# Run only in a newly created, isolated local worktree. All evidence stays private.
$ErrorActionPreference = 'Stop'
$auditPath = [IO.Path]::GetFullPath($AuditDirectory)
$canonicalPath = (Resolve-Path -LiteralPath $CanonicalSnapshot).Path
$workspacePath = (Get-Location).Path
if ($auditPath.StartsWith($workspacePath + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
  throw 'Audit evidence must remain outside the checkout.'
}
if (Test-Path -LiteralPath 'content/generated/snapshot.json') { throw 'Start from a clean checkout without generated content.' }
$expectedHash = 'd146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5'
if ((Get-FileHash -LiteralPath $canonicalPath).Hash.ToLowerInvariant() -ne $expectedHash) { throw 'Canonical evidence hash mismatch.' }
New-Item -ItemType Directory -Path $auditPath -Force | Out-Null
$env:CI = 'true'
$env:SITE_NOINDEX = 'true'
$env:PIPELINE_AI_ENABLED = 'false'
$env:WRANGLER_SEND_METRICS = 'false'
$env:ASTRO_TELEMETRY_DISABLED = '1'
foreach ($entry in @(Get-ChildItem Env:)) {
  if ($entry.Name -match '^(?:TECHLINE_AUTHORITY_|TECHLINE_EXTERNAL_CHECKPOINT|CLOUDFLARE_)') {
    Remove-Item -LiteralPath ('Env:' + $entry.Name)
  }
}
$checks = [Collections.Generic.List[object]]::new()
function Check-Step([string]$name, [scriptblock]$command, [int]$expected = 0) {
  $timer = [Diagnostics.Stopwatch]::StartNew()
  $ErrorActionPreference = 'Continue'
  & $command *> (Join-Path $auditPath ($name + '.log'))
  $code = $LASTEXITCODE
  $ErrorActionPreference = 'Stop'
  $timer.Stop()
  $checks.Add([ordered]@{step=$name; exit=$code; expected=$expected; passed=($code -eq $expected); seconds=$timer.Elapsed.TotalSeconds})
  [IO.File]::WriteAllText((Join-Path $auditPath 'results.json'), ($checks | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
  Write-Output "$name exit=$code expected=$expected"
  if ($code -ne $expected) { Get-Content -Tail 50 -LiteralPath (Join-Path $auditPath ($name + '.log')); exit 1 }
}
Check-Step install-js { pnpm.cmd install --frozen-lockfile }
Check-Step install-python { py -3.12 -m uv sync --frozen }
Check-Step lint-python { .venv/Scripts/python.exe -m ruff check pipeline }
Check-Step python { .venv/Scripts/python.exe -m pytest }
Check-Step synthetic-research-demo { .venv/Scripts/python.exe -m pipeline.research_cli demo }
if ((Get-Content -Raw -LiteralPath (Join-Path $auditPath 'synthetic-research-demo.log') | ConvertFrom-Json).status -ne 'PASS') { throw 'Synthetic workflow did not pass.' }
Check-Step fixtures { .venv/Scripts/python.exe -m pipeline --mode fixture }
Check-Step validate { .venv/Scripts/python.exe -m pipeline --validate }
Check-Step lint-js { pnpm.cmd lint }
Check-Step typecheck { pnpm.cmd typecheck }
Check-Step unit-js { pnpm.cmd test }
Check-Step dependencies-js { pnpm.cmd audit:dependencies }
Check-Step docs { pnpm.cmd verify:docs }
Check-Step repository { pnpm.cmd verify:repository }
Check-Step build { pnpm.cmd build }
Check-Step security { pnpm.cmd security }
Check-Step browser-install { pnpm.cmd exec playwright install chromium firefox webkit }
Check-Step browsers-accessibility { pnpm.cmd test:e2e }
Check-Step site { pnpm.cmd verify:site }
Check-Step budget { node scripts/verify-build.mjs }
$env:LIGHTHOUSE_REPORT_DIR = Join-Path $auditPath 'lighthouse-standard'
Check-Step performance-accessibility { pnpm.cmd performance }
Check-Step dryrun-standard { pnpm.cmd exec wrangler deploy --dry-run }
Check-Step dryrun-preview { pnpm.cmd exec wrangler deploy --config wrangler.preview.jsonc --dry-run }
Check-Step research-build { pnpm.cmd build:research }
Check-Step research-verify { pnpm.cmd verify:research }
$env:RESEARCH_SCREENSHOT_DIR = Join-Path $auditPath 'screenshots'
Check-Step research-browsers-accessibility { pnpm.cmd test:research }
Check-Step research-workerd { pnpm.cmd test:research:edge }
$env:TECHLINE_RESEARCH_REHEARSAL = 'true'
$env:LIGHTHOUSE_REPORT_DIR = Join-Path $auditPath 'lighthouse-research'
Check-Step research-performance-accessibility { pnpm.cmd performance }
Remove-Item Env:TECHLINE_RESEARCH_REHEARSAL
Check-Step research-dryrun { pnpm.cmd exec wrangler deploy --config wrangler.research-preview.jsonc --dry-run }
Check-Step research-publication-denied { node scripts/verify-research.mjs --publish } 1
Check-Step preview-publication-denied { node scripts/release-gate.mjs --publish --preview } 1
Check-Step production-publication-denied { node scripts/release-gate.mjs --publish } 1
Check-Step python-export { py -3.12 -m uv export --frozen --no-hashes --format requirements-txt --output-file (Join-Path $auditPath 'requirements.txt') }
Check-Step dependencies-python { py -3.12 -m uv tool run pip-audit==2.10.1 -r (Join-Path $auditPath 'requirements.txt') }
# Restore an exact copy in this isolated checkout; the supplied private original
# is read-only throughout. Canonical summaries, dates and translations are never edited.
Copy-Item -LiteralPath $canonicalPath -Destination 'content/generated/snapshot.json'
if ((Get-FileHash -LiteralPath 'content/generated/snapshot.json').Hash.ToLowerInvariant() -ne $expectedHash) { throw 'Canonical copy changed.' }
Check-Step canonical-readiness { .venv/Scripts/python.exe -m pipeline.research_cli report }
Check-Step canonical-selection { node scripts/research-inventory.mjs }
$selection = Get-Content -Raw -LiteralPath (Join-Path $auditPath 'canonical-selection.log') | ConvertFrom-Json
if ($selection.record_count -ne 37 -or $selection.eligible_count -ne 0 -or $selection.publication_allowed) { throw 'Canonical records gained authority.' }
Check-Step canonical-rights { node scripts/content-rights.mjs --snapshot-only }
Check-Step canonical-build { pnpm.cmd build }
Check-Step canonical-build-rights { pnpm.cmd verify:content-rights }
Check-Step real-research-build-denied { pnpm.cmd build:research } 1
Check-Step final-repository { pnpm.cmd verify:repository }
if (git status --porcelain) { throw 'Validation changed tracked files.' }
$revision = git rev-parse HEAD
[IO.File]::WriteAllText((Join-Path $auditPath 'verified-sha.txt'), $revision, [Text.UTF8Encoding]::new($false))
Write-Output "Verified local revision $revision; publication remains blocked."
