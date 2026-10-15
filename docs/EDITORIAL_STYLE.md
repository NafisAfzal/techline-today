# Editorial style

English is the canonical editorial language. Summaries explain what the collected evidence supports. Significance is included only when supported; unassessed significance stays unknown and extractive category advice is omitted from reader previews/details. This contract applies to provider prompts, extractive fallback, digests and translations.

## Voice and structure

- Use plain international English, familiar verbs and short sentences. Aim for one idea per sentence where practical; do not enforce an arbitrary reading-grade score.
- Lead with the concrete change: who released, found, changed or reported what.
- Explain significance in terms the available evidence supports. Identify constraints, availability and missing independent evaluation.
- Keep useful technical names: CUDA, H100, GPT, Gemini, Claude, Llama, API, tokens, parameters, latency, throughput and benchmark names. Explain unfamiliar concepts briefly when evidence supplies that explanation.
- Remove corporate language, hype, exaggerated adjectives, filler and repetitive attribution. Avoid phrases such as “operationalized,” “transformative breakthrough” and “unprecedented potential.”
- Use selective emphasis for an important fact or number. Do not bold entire paragraphs.
- Use “Summary,” “Today’s brief” and “Key facts.” Avoid unsupported reading-duration promises.

Bad: “The organization operationalized a multimodal inference architecture facilitating heterogeneous modality processing.”

Better, **only if supported by the source**: “The company released a system that can work with text and images.”

## Evidence and uncertainty

Rephrasing may change wording, never facts. Preserve numbers, units, versions, product names, source IDs and claim attribution. Do not infer price, access, eligibility, performance or availability from a headline. Preserve **may, could, reported, claimed, preliminary**, negation and limitations. Separate what a source says from interpretation. Vendor-reported benchmark results remain vendor claims; multiple dependent reports do not establish independent confirmation.

A headline-only record must disclose that only the headline was collected. The extractive fallback keeps source wording rather than attempting an unsafe synonym rewrite. Some source prose therefore remains technical without a configured provider. This is preferable to invented clarity.

## Bangla

Use natural, modern Bangla sentence structure: direct, readable and neither bureaucratic nor childish. Keep proper names in English. Familiar technology terms such as GPU, API, model, token, benchmark, open source and latency may remain English when this helps understanding. Keep numbers, units and currency exactly as supplied. Translate uncertainty and negation explicitly, within the same field. Do not copy English sentence order mechanically.

UI labels use ordinary Bangla: আজ, সারসংক্ষেপ, কেন গুরুত্বপূর্ণ, সূত্র, সংরক্ষণ, খুঁজুন, বিভাগ and সেটিংস. Source quotations and legal/offer terms retain their verified source language and are labelled accordingly.

## Implementation and review

The generation contracts are [story_summary.md](../prompts/story_summary.md), [digest.md](../prompts/digest.md) and [story_translation.md](../prompts/story_translation.md). Prompt version 3 and summary policy 7 invalidate older summaries. Source-transform revision 6 reprocesses cached release evidence after prose cleanup. Translation cache keys include the canonical evidence/content, prompt, schema, language and policy.

The October 12 refinement removes generic release headings, duplicated model headings and changeset thank-you prefixes without removing a fix on the same line. Preview, breaking-change and known-issue context remain. Extraction prefers substantive source prose to repeating the headline; rendered article bullets omit an identical headline and attribution filler, while canonical three-bullet records and claim attribution remain available. No synonym rewrite or unsupported implication is introduced. The reviewed live collection has 47 headline-only records out of 112 (41.96%); their notices remain explicit. A source offering only a title cannot support an invented summary. Human editing or additional permitted evidence is the next quality improvement, not weakening validation.

Before accepting editorial or translated output, ask: Can a general reader understand the change? Are every number and named product preserved? Does each uncertainty remain? Can every claim still be traced to the same evidence? Automated checks catch structure, Unicode, numbers and some names/uncertainty; they cannot guarantee semantic accuracy or literary quality. Native-reader review remains necessary for production Bangla. See [LOCALIZATION.md](LOCALIZATION.md).

## Wave 1 evidence language

The stored `primary-confirmed` enum remains compatible; the reader calls it **Primary source**. It establishes provenance, not independent corroboration or review. arXiv stories disclose that peer review is unestablished from metadata and paper limitations have not been assessed from the abstract. This avoids claiming that every arXiv paper is necessarily unreviewed. Extractive facts remain source-reported; supported means supported by cited text. AI interpretation remains labelled and needs semantic editorial review before activation. Negated review evidence must never license an affirmative peer-review claim.
