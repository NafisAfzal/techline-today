# Source Candidates

This is a candidate map, not a license to scrape every domain. During implementation, verify each feed/API URL, robots policy and terms before enabling it.

## AI models and labs

Primary-source candidates:
- OpenAI official news, docs and model/API changelogs
- Anthropic official news/docs
- Google DeepMind / Google AI official blogs and Gemini API docs
- Meta AI official announcements/model cards
- Mistral official news/docs
- xAI official announcements/docs
- Hugging Face blog/model cards
- NVIDIA AI/developer news
- major open-source project GitHub release feeds

Use primary sources for release facts, availability, context limits and pricing. Add independent sources only for analysis/verification.

## AI benchmarks and model performance

Priority:
1. official model/system card for claimed results;
2. independent benchmark organization or reproducible repository;
3. paper/preprint;
4. community reports as anecdotes only.

Never merge vendor and independent numbers without preserving benchmark/version/hardware context.

## Research

Good machine-readable sources:
- arXiv API/feed
- official project repositories/releases
- research-lab publication pages

Optional later:
- OpenAlex or other scholarly APIs after checking current terms/limits.

Do not summarize every paper. Use category relevance, novelty and community/research signals to select a small number.

## Developer and open-source ecosystem

- GitHub Releases/REST API for configured repositories
- official framework/tool changelogs
- package/project release feeds where supported
- Hacker News API for discovery/community signal

Use authenticated GitHub API in Actions where useful to raise rate limits, using the built-in `GITHUB_TOKEN` with minimum permissions when possible.

## Free APIs, credits and student/developer offers

Only mark an offer active from an official source where possible:
- provider pricing/free-tier page
- developer program page
- student program page
- official announcement/changelog

The tracker should record:
- last verified timestamp;
- region restrictions;
- card/billing requirement;
- exact quota/credit;
- expiry;
- claim steps;
- link to official terms.

This category is especially sensitive to stale information, so active offers should be rechecked more frequently than ordinary evergreen stories.

## Chips and devices

Primary:
- NVIDIA, AMD, Intel, Qualcomm, Apple, Google, Samsung and other official newsrooms/product pages.

Independent:
- reputable device/semiconductor publications with RSS or permitted feeds.

For launch specs, prefer the official spec sheet. Use independent reviews for measured performance/battery/thermals and label them accordingly.

## Jobs and skills

V1 should focus on high-level career signals rather than scraping thousands of job listings.

Possible inputs:
- official company hiring/layoff announcements;
- legitimate public jobs APIs whose terms allow aggregation;
- research on skill demand;
- selected internship/fellowship/student programs from official pages.

If a job-board API is added, store expiry and source URL and automatically remove stale listings.

## Security

Primary:
- vendor advisories
- CVE/NVD or appropriate vulnerability feeds
- official security bulletins

Independent reporting can add context but should not override the primary advisory for affected versions/fixes.

## Source independence

Create an `independence_group` for each source. Examples:
- wire-service-derived copies share an independence group;
- syndicated press releases share the issuer's group;
- a publisher's multiple subdomains may share one group.

Cross-source corroboration counts groups, not raw article count.
