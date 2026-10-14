import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';
import lighthouse from 'lighthouse';
import { chromium } from '@playwright/test';

const config = JSON.parse(fs.readFileSync('lighthouserc.json', 'utf8'));
const base = 'http://127.0.0.1:4322';
const server = spawn(process.execPath, ['scripts/performance-preview.mjs'], {stdio: 'ignore'});
let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 60; attempt++) {
    try {ready = (await fetch(base)).ok;} catch { /* Wait for the local server. */ }
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  assert(ready, 'Performance preview failed to start');
  browser = await chromium.launch({executablePath:chromium.executablePath(),args:['--remote-debugging-port=4325','--remote-debugging-address=127.0.0.1']});
  const reportDir = process.env.LIGHTHOUSE_REPORT_DIR || '.lighthouseci/reports';
  fs.mkdirSync(reportDir, {recursive: true});
  const reports = [];
  for (let run = 0; run < config.ci.collect.numberOfRuns; run++) {
    const result = await lighthouse(base, {port:4325, output: 'html', logLevel: 'error', onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo']});
    assert(result && !result.lhr.runtimeError, 'Lighthouse did not produce a valid report');
    fs.writeFileSync(path.join(reportDir, `run-${run + 1}.html`), result.report);
    fs.writeFileSync(path.join(reportDir, `run-${run + 1}.json`), JSON.stringify(result.lhr));
    reports.push(result.lhr);
  }
  const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
  for (const [name, [severity, threshold]] of Object.entries(config.ci.assert.assertions)) {
    const scores = reports.map(report => name.startsWith('categories:') ? report.categories[name.split(':')[1]].score : report.audits[name].numericValue);
    const value = median(scores);
    const passed = threshold.minScore === undefined ? value <= threshold.maxNumericValue : value >= threshold.minScore;
    console.log(`${name}: ${scores.join(', ')}; median ${value}; ${passed ? 'PASS' : severity.toUpperCase()}`);
    assert(passed || severity !== 'error', `Performance budget failed: ${name}`);
  }
  console.log('Lighthouse reports saved in the configured report directory.');
} finally {
  try {await browser?.close();} finally {server.kill();}
}
