import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))


def test_workflows_have_least_privilege_and_pinned_actions():
    for file in (ROOT / ".github/workflows").glob("*.yml"):
        workflow = read(file.name)
        expected = {"contents": "read", **({"security-events": "write"} if file.name == "codeql.yml" else {})}
        assert workflow["permissions"] == expected
        triggers = workflow.get("on", workflow.get(True, {}))
        assert "pull_request_target" not in triggers
        for job in workflow["jobs"].values():
            assert "permissions" not in job or job["permissions"] == expected
            for step in job["steps"]:
                if "uses" in step:
                    assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", step["uses"])
                    if step["uses"].startswith("actions/checkout@"):
                        assert step["with"]["persist-credentials"] is False


def test_production_is_explicitly_gated_and_deploy_token_is_scoped():
    workflow = read("ingest.yml")
    assert workflow["concurrency"]["cancel-in-progress"] is False
    job = workflow["jobs"]["production"]
    assert "github.event.repository.default_branch" in job["if"]
    assert "vars.PRODUCTION_ENABLED == 'true'" in job["if"]
    assert job["environment"] == "production"
    deploy = next(step for step in job["steps"] if step.get("id") == "deploy")
    assert deploy["run"] == "pnpm deploy"
    assert deploy["env"]["SITE_URL"] == "${{ vars.SITE_URL }}"
    assert all("CLOUDFLARE_API_TOKEN" not in step.get("env", {}) for step in job["steps"] if step is not deploy)
    steps = job["steps"]
    assert any(step.get("run") == "node scripts/verify-build.mjs --production" for step in steps[:steps.index(deploy)])
    saved = next(step for step in steps if step.get("name") == "Save successful production snapshot")
    assert saved["if"] == "steps.deploy.outcome == 'success' || steps.changes.outputs.changed == 'false'"
    assert deploy["if"] == "steps.changes.outputs.changed == 'true'"
    changes = next(step for step in steps if step.get("id") == "changes")
    assert steps.index(changes) < steps.index(deploy)
    usage = next(step for step in steps if step.get("name") == "Preserve provider usage even if publication fails")
    assert usage["if"] == "always()"
    reservations = next(step for step in steps if step.get("name") == "Restore provider call reservations")
    for step in (usage, reservations):
        assert set(step["with"]["path"].splitlines()) == {
            ".cache/provider-usage-live.json", ".cache/translations-live.json"
        }


def test_pull_request_validation_has_no_production_secrets_or_publication():
    text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "secrets." not in text
    commands = [step.get("run", "") for step in read("ci.yml")["jobs"]["validate"]["steps"]]
    assert "pnpm deploy" not in commands
    for command in ["uv run python -m pipeline --mode fixture", "uv run python -m pipeline --validate", "pnpm test:e2e", "pnpm verify:site", "pnpm performance", "pnpm audit:dependencies", "pnpm deploy:check"]:
        assert command in commands


def test_preview_is_manual_isolated_and_noindex():
    workflow = read("preview.yml")
    assert set(workflow.get("on", workflow.get(True, {}))) == {"workflow_dispatch"}
    job = workflow["jobs"]["preview"]
    assert job["environment"] == "preview"
    assert "PREVIEW_ENABLED" in job["if"]
    steps = job["steps"]
    deploy = next(step for step in steps if step.get("run") == "pnpm deploy:preview")
    assert all("CLOUDFLARE_API_TOKEN" not in step.get("env", {}) for step in steps if step is not deploy)
    assert any(step.get("env", {}).get("SITE_NOINDEX") == "true" for step in steps)
    assert any(step.get("run") == "node scripts/release-gate.mjs --publish --preview" for step in steps)


def test_hosted_smoke_precedes_successful_state_promotion():
    workflow = (ROOT / ".github/workflows/ingest.yml").read_text(encoding="utf-8")
    assert workflow.index("Post-deployment hosted smoke") < workflow.index("Record published edition receipt")
    assert workflow.index("Post-deployment hosted smoke") < workflow.index("Save successful production snapshot")
