# Local setup on Windows

Use the project root in PowerShell. Node 24+, Git, pnpm 10.33.1 and uv 0.12.22 are required. uv installs Python 3.13 without replacing your existing Python.

```powershell
npm.cmd install --global pnpm@10.33.1
py -3.12 -m pip install uv==0.12.22
py -3.12 -m uv python install 3.13
pnpm.cmd install --frozen-lockfile
py -3.12 -m uv sync --frozen
py -3.12 -m uv run python -m pipeline --mode fixture
pnpm.cmd dev
```

Replace `py -3.12` with your existing Python launcher version if needed. With uv on PATH, `uv` replaces `py -3.12 -m uv`. The `.cmd` suffix avoids PowerShell execution-policy issues with npm/pnpm script wrappers.

Open http://127.0.0.1:4321. Stop with Ctrl+C. Stop/restart after changing the snapshot; build-time data is loaded once.

```powershell
# Live public sources, no provider keys required
py -3.12 -m uv run python -m pipeline --mode live
pnpm.cmd dev

# Production preview with deployment security headers
pnpm.cmd build
pnpm.cmd preview
```

Copy optional settings only if you have no existing `.env`:

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
$env:SITE_URL = 'https://ai-tech-intelligence.YOUR-SUBDOMAIN.workers.dev'
```

Python loads the root `.env`. Export `SITE_URL` before a production build for canonical links/RSS/sitemap. Fixtures are synthetic, noindexed and rejected by production validation. Use fixtures before E2E tests.

Bash uses `pnpm`, `uv`, and `export SITE_URL=...`; the commands otherwise match the README. Frozen installs use `pnpm-lock.yaml` and `uv.lock`. XAMPP/PHP is unnecessary.
