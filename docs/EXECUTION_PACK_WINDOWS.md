# Windows Setup for This Project

Recommended location:

```powershell
mkdir "$HOME\Documents\Projects" -Force
cd "$HOME\Documents\Projects"
mkdir ai-tech-intelligence
cd ai-tech-intelligence
```

Extract the contents of this execution pack into that directory.

Then:

```powershell
git init
git branch -M main
```

Open the folder in VS Code if installed:

```powershell
code .
```

Start your Codex launcher from this folder:

```powershell
codex-plus
```

Then paste the full contents of `CODEX_MASTER_PROMPT.md`.

Do not put this project under `C:\xampp\htdocs` unless you specifically want XAMPP involved. This architecture does not require Apache/PHP/XAMPP.

Recommended prerequisites:
- Git
- Node.js current LTS
- pnpm via Corepack
- Python 3.13-compatible installation
- optional `uv` for Python dependency management

Let Codex create the exact project manifests and lockfiles from the master prompt, then commit only after tests/build succeed.
