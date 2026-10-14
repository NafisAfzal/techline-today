# Freebie Verification Prompt Contract

Extract only verifiable offer terms from official or clearly identified evidence.

Required fields:
- provider
- offer title
- free amount/allowance
- eligibility
- geography restrictions
- billing/card requirement
- start date if known
- expiry date if known
- claim steps
- integration notes
- source IDs
- uncertainty

Never infer that an offer is available worldwide. Never call a trial “free forever.” If expiry or card requirement is unknown, return null/unknown rather than guessing.
