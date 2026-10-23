import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir:'tests/research', outputDir:'.cache/research-playwright', fullyParallel:true, workers:2, retries:0,
  use:{baseURL:'http://127.0.0.1:4337',trace:'retain-on-failure'},
  webServer:{command:'node scripts/preview.mjs --research',env:{PORT:'4337'},url:'http://127.0.0.1:4337',reuseExistingServer:false},
  projects:[
    {name:'desktop',use:{...devices['Desktop Chrome']}},
    {name:'mobile',use:{...devices['Pixel 7']}},
    {name:'webkit',use:{...devices['iPhone 13']}},
    {name:'firefox',use:{...devices['Desktop Firefox']}},
  ],
});
