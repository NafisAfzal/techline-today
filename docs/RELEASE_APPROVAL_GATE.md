# Three independent release gates

**Gate A is owner-authorized, subject to successful safety checks.** This authorizes the exact public GitHub destination below, reviewed commits/pushes and safe hosted validation. Cloudflare preview, production, inference and recurring execution remain unauthorized. The owner additionally requires verified independent backup restoration before GitHub publication.

| Gate | Destination | Conditions before authorization |
|---|---|---|
| A: public GitHub | `NafisAfzal/techline-today` | Confirmed personal account, MIT/notice, reviewed public inventory/content rights, clean staged secret/history checks, independent backup restoration, authorized working name, reviewed commit and explicit owner authorization. |
| B: noindex preview | `ai-tech-intelligence-preview` in the confirmed Cloudflare account | Gate A complete, hosted CI green, Free/zero-spend verified, exact account/subdomain/origin, separate Worker, scoped credentials and explicit preview authorization. Public noindex is still public. |
| C: indexed production | `ai-tech-intelligence` in the same approved account | Hosted preview/smoke/rollback evidence, rights-approved real content, independent off-machine restore, monitoring and explicit production authorization. |

`config/release.json` records the Gate A authorization and completed local inventory/content/backup reviews. Preview, production, initial-seed, AI and schedule flags remain false. CLI checks bind reviewed SHA, actual repository visibility, clean checkout, exact account and matching Worker/subdomain origin. Gate A fails closed without content review or independent restoration. Gate B rejects the production destination. Gate C requires preview and durable-backup proof. Inference remains prohibited even if keys appear. `PREVIEW_ENABLED`/`PRODUCTION_ENABLED` remain unset or false; no cron is present.

Use `node scripts/release-gate.mjs --github`, `--preview`, or the default production check to inspect pending decisions. `--publish` makes missing conditions fail before external commands. The tool itself does not create repositories or deploy.

Do not use blanket staging. Generate/review the prospective path inventory, stage those exact paths, inspect all staged changes, scan the index/history, and commit only with the local noreply identity. The prepared PowerShell commands and account-bound creation/preview sequence are in the launch plan. The owner's Gate A authorization includes safety-reviewed release repairs and corrective commits; it does not authorize other destinations or deployments.
