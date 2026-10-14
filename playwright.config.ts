import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir:'tests/e2e', fullyParallel:true, workers:2, retries:process.env.CI ? 1 : 0,
  use:{baseURL:'http://127.0.0.1:4327',trace:'retain-on-failure'},
  webServer:{command:'node scripts/preview.mjs',env:{PORT:'4327'},url:'http://127.0.0.1:4327',reuseExistingServer:false,timeout:30000},
  projects:[
    {name:'desktop',testIgnore:'mobile-release.spec.ts',use:{...devices['Desktop Chrome']}},
    {name:'mobile',testIgnore:'mobile-release.spec.ts',use:{...devices['iPhone 13'],defaultBrowserType:'chromium'}},
    {name:'android-chromium',testMatch:'mobile-release.spec.ts',use:{...devices['Pixel 7'],defaultBrowserType:'chromium'}},
    {name:'ios-webkit',testMatch:'mobile-release.spec.ts',use:{...devices['iPhone 13'],defaultBrowserType:'webkit'}},
    {name:'touch-firefox',testMatch:'mobile-release.spec.ts',use:{browserName:'firefox',viewport:{width:393,height:851},deviceScaleFactor:2,hasTouch:true}},
  ],
});
