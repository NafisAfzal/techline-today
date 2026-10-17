import json
import os
from pathlib import Path

path = Path('.cache/pipeline-attempt.json')
if not path.exists():
    path = Path('content/generated/run-report.json')
if path.exists():
    report = json.loads(path.read_text(encoding='utf-8'))
    report['deployment_status'] = os.getenv('DEPLOYMENT_OUTCOME') or 'not-attempted'
    lines = ['## Intelligence edition', '', f"Mode: {report['mode']} · Status: {report.get('status', 'unknown')} · Stories: {report.get('stories', 0)} · Cached summaries: {report.get('cached_summaries', 0)}",
             f"Generation: {report.get('generation_modes', {})} · Deployment: {report['deployment_status']}", '', '| Source | Status | Items |', '|---|---|---|']
    lines += [f"| {source['id']} | {source['status']} | {source['items']} |" for source in report.get('sources', [])]
    if report.get('provider_health'):
        lines += ['', '| Provider | Calls today | Errors | Rate limits | Valid outputs |', '|---|---|---|---|---|']
        lines += [f"| {name} | {health['calls']} | {health['errors']} | {health['rate_limits']} | {health['valid_outputs']} |" for name, health in report['provider_health'].items()]
else:
    lines = ['## Intelligence edition', '', 'No successful ingestion report was produced. Previous deployment remains available.']
summary = '\n'.join(lines) + '\n'
if os.getenv('GITHUB_STEP_SUMMARY'):
    with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a', encoding='utf-8') as stream:
        stream.write(summary)
else:
    print(summary)
