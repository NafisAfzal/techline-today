import httpx

import pipeline.security as security
from pipeline.ai import extractive
from pipeline.normalize import release_text
from pipeline.verification import numeric_tokens, validate_summary


def test_release_heading_cleanup_keeps_model_name_and_measurements():
    text = "## New Model additions\n### Nemotron 3 Diarization\nNemotron 3 Diarization supports up to eight speakers.\n### Known issues\nLatency may increase with 64 GB memory."
    cleaned = release_text(text)
    assert cleaned.count("Nemotron 3 Diarization") == 1
    assert "Known issues:" in cleaned and "may increase" in cleaned
    assert numeric_tokens(cleaned) == numeric_tokens(text)


def test_release_cleanup_preserves_preview_and_breaking_context():
    cleaned = release_text("## Release Notes\nReleased on 2026-10-01.\n### Preview features\n- An optional API.\n### Breaking changes\n- Requires a new configuration.")
    assert "Release Notes" not in cleaned and "2026-10-01" in cleaned
    assert "Preview features:" in cleaned and "Breaking changes:" in cleaned


def test_changeset_gratitude_does_not_replace_the_actual_fix():
    cleaned = release_text("## Patch Changes\n- [#18339](https://example.com/pull) [`fcc050c`](https://example.com/commit) Thanks [@author](https://example.com/author)! - Fixes routes failing with Cannot find native binding. Requires version 11.0.14.")
    assert "Thanks" not in cleaned and "fcc050c" not in cleaned and "Patch Changes" not in cleaned
    assert "Fixes routes failing with Cannot find native binding." in cleaned
    assert "11.0.14" in cleaned


def test_extractive_summary_prefers_supported_prose_to_repeated_title(items):
    source = items[0].model_copy(update={"title": "A developer model release", "excerpt": "Developers can test the model locally. Access requires registration."})
    summary = extractive([source])
    assert summary.summary_bullets[:2] == ["Developers can test the model locally.", "Access requires registration."]
    assert source.title not in summary.summary_bullets
    validate_summary(summary, [source])


def test_headline_only_summary_keeps_explicit_limits(items):
    source = items[0].model_copy(update={"excerpt": ""})
    summary = extractive([source])
    assert summary.summary_bullets[0] == source.title
    assert any("Only the headline" in bullet for bullet in summary.summary_bullets)
    assert any("Only source metadata" in limitation for limitation in summary.limitations)
    validate_summary(summary, [source])


async def test_normalizer_revision_refetches_cached_source(source, monkeypatch):
    headers = []

    def handler(request):
        headers.append(dict(request.headers))
        if request.headers.get("if-none-match"):
            return httpx.Response(304)
        return httpx.Response(200, text="<rss/>", headers={"Content-Type": "application/xml", "ETag": "stable"})

    state = {}
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        for revision in [security.SOURCE_TRANSFORM_VERSION, security.SOURCE_TRANSFORM_VERSION, "new-transform"]:
            monkeypatch.setattr(security, "SOURCE_TRANSFORM_VERSION", revision)
            await security.SafeFetcher(client, state, "TestBot").get(source.endpoint, source, accept=("application/xml",))
    assert "if-none-match" not in headers[0]
    assert headers[1]["if-none-match"] == "stable"
    assert "if-none-match" not in headers[2]
