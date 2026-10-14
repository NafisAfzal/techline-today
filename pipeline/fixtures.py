from datetime import timedelta

from pipeline.models import ModelRelease, Offer, SourceConfig
from pipeline.normalize import normalize

DEMO = [
    ("ai", "Meridian releases an open multimodal model for local development", "Meridian publishes open weights for its multimodal model. The model card lists a 128K context window. API access is limited to the developer preview."),
    ("security", "Harbor publishes a security patch for its developer gateway", "Harbor has released a security patch for the developer gateway. The advisory identifies affected versions and an upgrade path. Administrators should review the official advisory."),
    ("dev-apis", "Relay adds batch requests to its developer API", "Relay adds batch requests to the developer API. The changelog describes asynchronous job handling. Existing endpoints remain available."),
    ("research", "A new retrieval paper publishes its evaluation dataset", "The authors publish a retrieval evaluation dataset. The preprint reports 24 evaluation tasks. Results have not been independently reproduced."),
    ("chips", "Atlas announces a developer accelerator with expanded memory", "Atlas announces its developer accelerator. The specification lists 48GB of memory. Independent performance measurements are not yet available."),
    ("devices", "Fieldbook updates its laptop with a repairable battery", "Fieldbook announces a laptop with a replaceable battery. The manufacturer lists a 14-inch display. Availability depends on the shipping region."),
    ("open-source", "Forge publishes a stable release of its build toolkit", "Forge publishes a stable build toolkit release. The release notes include dependency migration instructions. The project retains its open-source license."),
    ("jobs-skills", "Northstar opens applications for its developer fellowship", "Northstar opens developer fellowship applications. The program page lists eligibility requirements. Applicants should check the program terms."),
    ("freebies", "Cobalt offers a limited developer API credit for students", "Cobalt offers a student developer credit. Eligible applicants receive a $25 trial credit. The offer has an expiry date and requires student verification."),
]


def fixture_data(now):
    items = []
    for index, (category, title, text) in enumerate(DEMO):
        source = SourceConfig(id=f"demo_{category}", name="Demo " + title.split()[0], adapter="rss", source_class="primary",
                              endpoint="https://example.com/feed", allowed_hosts=["example.com"], categories=[category],
                              independence_group="demo-" + category, terms_url="https://example.com/terms")
        items.append(normalize({"url": f"https://example.com/demo/{category}", "title": title, "text": text,
                                "published_at": (now - timedelta(hours=index + 1)).isoformat(), "category": category,
                                "is_demo": True}, source, now))
    # Historical fixtures exercise completed calendar periods and archive paths.
    for offset, category in ((10, "research"), (40, "open-source"), (400, "ai"), (600, "devices")):
        original = next(item for item in items if item.category == category)
        historical = original.model_copy(update={"id": f"src_demo_history_{offset}", "original_url": f"https://example.com/demo/history/{offset}",
                                                 "canonical_url": f"https://example.com/demo/history/{offset}",
                                                 "published_at": now - timedelta(days=offset), "title": f"Archive demonstration: {original.title}"[:180]})
        items.append(historical)
    return items


def fixture_trackers(stories, now):
    ai = next(story for story in stories if story.category == "ai")
    offer = next(story for story in stories if story.category == "freebies")
    offers = [Offer(id="demo-credit", story_id=offer.id, provider="Cobalt (demo)", title="Student API credit (demo)",
                    offer_type="api-credit", value_text="$25 trial credit", eligibility=["Verified student status"],
                    regions=["Not specified in this fixture"], card_required=None,
                    claim_steps=["Read the official eligibility terms.", "Verify student status.", "Review billing settings before claiming."],
                    expires_at=now + timedelta(days=4), last_verified_at=now, status="expiring",
                    official_source_url="https://example.com/demo/freebies", source_ids=offer.source_ids,
                    integration_notes="Synthetic offer for interface testing. This credit cannot be claimed.", is_demo=True)]
    offers.append(offers[0].model_copy(update={"id": "demo-expired", "title": "Previous student credit (demo)",
                                            "expires_at": now - timedelta(days=1), "status": "expired"}))
    releases = [ModelRelease(id="demo-meridian", story_id=ai.id, provider="Meridian (demo)", model="Meridian Multimodal (demo)",
                             release_date=ai.published_at, modality=["Text", "Image"], context_window="128K",
                             pricing="Developer preview; pricing not specified", api_available=True, weights="open",
                             benchmark_claims=[], independent_references=[], key_change="Open multimodal weights for local development.",
                             source_ids=ai.source_ids, is_demo=True)]
    return offers, releases
