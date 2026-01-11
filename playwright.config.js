const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./ui-tests",
  timeout: 30000,
  expect: { timeout: 5000 },
  retries: 0,
  workers: 1,
  outputDir: "test-results",
  use: {
    baseURL: process.env.BASE_URL || "https://localhost:8443",
    ignoreHTTPSErrors: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure"
  },
  reporter: [
    ["list"],
    ["html", { open: "never" }]
  ]
});
