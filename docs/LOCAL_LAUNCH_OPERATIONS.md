# Local launch operations

From the isolated checkout after the locked Python environment is installed,
run this one local PowerShell command:

```powershell
.\.venv\Scripts\python.exe -m pipeline.launch_console
```

Add `--json` for evidence details. Exit code 2 means operational prerequisites
remain blocked or inconclusive; 1 means local input or verification failed.
The command changes no content or authority and makes no external writes. When
an operator has explicitly configured an active custody operation, the existing
verifier may advance its local durable clock floor; JSON reports
`security_state_may_advance`. Without that operation it inspects local state only.
Credential-shaped keys and values are refused before printing or exporting.
Missing owner authority and human content approvals are operational blockers,
not failed software tests. The command neither authenticates a Cloudflare
account nor queries GitHub. Local plan/billing flags cannot prove either account
security or spending exposure. The local advisory result describes only its
recorded mitigation; current hosted alerts require dated read-only evidence.
Recovery inventory does not prove that a real backup or restore drill exists.

The report distinguishes local owner history, scoped reviewer grants,
independent checkpoint custody, emergency STOP, source rights, exact research
stages, native Bangla requirements, real eligible content and preview approval.
It reports PASS only for the stated check, FAIL for malformed/failed local
verification, BLOCKED for missing prerequisites and INCONCLUSIVE for insufficient
evidence. It provides no overall green launch status or progress percentage.

## Private item review exports

Restore the independently hash-verified canonical snapshot to the ignored
`content/generated/snapshot.json`. Preserve the original private evidence.
The export command reads this local snapshot and recomputes decisions through
the existing authenticated research evaluator. It never downloads sources or
changes content, policy, authority, approval journals or publication flags.

```powershell
.\.venv\Scripts\python.exe -m pipeline.content_review --expected-snapshot-sha256 d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5 --export 'C:\private\fresh-private-review-export'
```

Use a fresh destination outside every Git checkout; existing directories,
linked paths and checkout destinations are refused. Exports contain canonical
extractive content and private review context. Keep them outside public assets
and hosting uploads. Preserve `MANIFEST.json` and hash it separately with
`Get-FileHash -Algorithm SHA256` when handing a packet to a reviewer.

Each item has Markdown and JSON packets with the exact record ID, original
record digest, snapshot digest, existing authority bindings, original sources,
recorded dates and rights policy, extraction provenance, truncation flags,
limitations, fact/number checklists, role/stage requirements and missing
authenticated decisions. CSV and batches of up to six items help assign work.
CSV fields guard spreadsheet formula prefixes, and Markdown renders metadata
as inert text. File names use stable packet numbers, never source-controlled
record IDs. These unsigned exports confer no permissions or approval.

Start with rights and date exceptions. For arXiv, verify the exact extract is
abstract metadata; metadata licensing does not authorize paper bodies or figures.
For Cloudflare, reconcile the exact repository revision's license with the
Workers website license notice. Source URLs and recorded licenses are leads
for a qualified reviewer, rather than item clearance. The command does not
claim to have freshly verified those URLs or any facts on them.

English-only items require no invented Bangla review. Adding any translation
changes the exact binding and requires fresh applicable reviews. Automated and
fixture labels are never native Bangla approval. Proposed editorial repairs
must be reviewed separately; do not patch the preserved canonical inventory.

After authentic owner/reviewer provisioning and independent current checkpoint
custody, use the existing [prepare/sign/validate/record workflow](RESEARCH_APPROVAL_WORKFLOW.md).
Appointments, permissions, factual judgments and publication decisions remain
human acts. Final deployment and GitHub publication require separate exact-SHA
owner authorization. This local command authorizes neither.
