# GitHub repository readiness

The owner authorized public **NafisAfzal/techline-today**, branch `main`, subject to the safety gates. The personal account and independent recovery copy are verified. [Current Gate A results](GITHUB_GATE_A_RELEASE.md) record actual publication and hosted checks; [release controls](RELEASE_APPROVAL_GATE.md) keep Cloudflare, inference and scheduling separately gated.

## Prepared locally

- Accurate README, architecture diagram, contribution guidance, editor configuration and separate code/content licensing review.
- pnpm/uv locks and the visible cache-policy patch included; real news snapshots/archives, credentials, dependency trees, traces and build output ignored.
- Read-only PR CI performs lint, types, Python/Vitest/browser tests, static verification, dependencies/security, Lighthouse and offline Cloudflare packaging. Fork PRs receive no production secrets. Actions use full commit SHA pins and checkout credentials are not retained.
- CodeQL covers Python and JavaScript/TypeScript and supports safe manual verification. Cron triggers are absent. Dependabot is a planning template in `docs/planning/dependabot.yml.example`, not active update configuration. Consult the current report for hosted results and enabled security features.
- The six public screenshots passed hash and content review under the conservative source policy. Files over 1 MiB and personal machine paths are rejected by repository verification. Verification stages only reviewed paths in a temporary index and leaves real staging untouched.

## Owner-approved publication sequence

Verify actual visibility and owner identity, MIT/NOTICE, content/working-name scope, independent restoration and the exact public inventory. Follow the disabled-Actions first-push procedure in [the preparation plan](OWNER_GITHUB_LAUNCH_PLAN.md), using the current owner authorization. Run all gates, stage only the reviewed NUL path list, inspect the staged tree and repeat credential/content/history checks. Confirm the local noreply identity, commit, and bind the checked revision to the release guard. Create the exact approved empty repository only if absent, then use a normal push. Never replace an unexpected destination or history.

Set default Actions token permissions to read contents. Enable secret scanning/push protection and review CodeQL findings. Require the passing `pull-request-ci / validate` check on main, block force pushes/deletion and use pull requests; a solo owner cannot self-approve a review. [GitHub branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule).

Keep preview, production and live-source-health workflows disabled during Gate A. Enable only reviewed validation/security workflows with read-only default tokens and safe fork permissions. Configure Cloudflare environments, secrets and approved revisions only under separate authorization. Dependency-update jobs and news schedules need separate approval. See [Cloudflare configuration](CLOUDFLARE_DEPLOYMENT.md).
