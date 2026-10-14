# Data Model

The static JSON contracts should match the future D1 schema closely.

## StoryCluster

Key fields:

```text
id
slug
canonical_topic
category
subcategory
headline
summary_bullets[3]
why_it_matters
broader_summary
key_facts[]
key_numbers[]
limitations[]
evidence_state
source_ids[]
primary_source_id
published_at
first_seen_at
updated_at
last_verified_at
importance_score_internal
novelty_score_internal
language
tags[]
entities[]
change_log[]
claim_map[]
ai_metadata
schema_version
```

`importance_score_internal` is not shown as a “truth score.”

## SourceItem

```text
id
source_registry_id
canonical_url
domain
title
author
published_at
fetched_at
source_type
source_independence_group
language
content_hash
excerpt
external_id
http_etag
http_last_modified
```

`source_independence_group` prevents counting syndicated copies as independent corroboration.

## Claim

```text
id
story_id
text
claim_type
normalized_value
unit
source_ids[]
attribution
status
notes
```

Statuses:
- supported
- conflicting
- uncertain
- retracted/updated

## Offer / Freebie

```text
id
provider
title
offer_type
value_text
eligibility[]
regions[]
card_required
claim_steps[]
starts_at
expires_at
last_verified_at
status
official_source_url
integration_notes
```

Statuses:
- active
- expiring
- expired
- unverified

## Digest

```text
id
period_type
period_start
period_end
category
story_ids[]
summary
watch_next[]
generated_at
schema_version
```

## Future D1 indexes

When D1 is introduced:
- unique index on source canonical URL hash;
- index on story updated_at;
- compound index on category + published_at;
- index on offer status + expires_at;
- index on digest period_type + period_start;
- unique user_id + story_id for bookmarks.

Avoid queries that scan all rows because free-tier D1 usage counts rows read.
