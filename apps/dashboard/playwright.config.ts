import {defineConfig,devices} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:45000,fullyParallel:false,workers:1,
 use:{baseURL:process.env.E2E_BASE_URL||'http://127.0.0.1:3001',trace:'retain-on-failure'},
 projects:[{name:'desktop',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:1000}}},
 {name:'tablet',use:{...devices['iPad Mini'],browserName:'chromium'}},{name:'mobile',use:{...devices['iPhone 13'],browserName:'chromium'}}],
 reporter:[['list'],['html',{open:'never'}]]});
