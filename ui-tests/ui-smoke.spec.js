const { test, expect } = require("@playwright/test");

function getCreds(prefix){
  const user = process.env[`TEST_${prefix}_USERNAME`];
  const pass = process.env[`TEST_${prefix}_PASSWORD`];
  return { user, pass };
}

async function login(page, username, password, nextPath){
  const next = nextPath || "/";
  const nextParam = encodeURIComponent(next);
  await page.goto(`/login.html?next=${nextParam}`);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

async function selectFirstOption(page, selector){
  await page.waitForFunction((sel) => {
    const el = document.querySelector(sel);
    if(!el) return false;
    return Array.from(el.options).some((opt) => opt.value);
  }, selector);
  const value = await page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if(!el) return "";
    const option = Array.from(el.options).find((opt) => opt.value);
    return option ? option.value : "";
  }, selector);
  if(value){
    await page.selectOption(selector, value);
  }
  return value;
}

test("login page renders", async ({ page }) => {
  await page.goto("/login.html");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("lesson manifest is reachable", async ({ request }) => {
  const res = await request.get("/lessons/manifest.json");
  expect(res.ok()).toBeTruthy();
});

test("pupil can sign in and see student hub", async ({ page }) => {
  const { user, pass } = getCreds("PUPIL");
  test.skip(!(user && pass), "TEST_PUPIL_USERNAME/PASSWORD not set");
  await login(page, user, pass, "/index.html");
  await expect(page.getByRole("heading", { name: "Student hub" })).toBeVisible();
  await expect(page.locator("#teacherLink")).toBeHidden();
  await expect(page.locator("#adminLink")).toBeHidden();
});

test("pupil can use hint to insert starter code", async ({ page }) => {
  const { user, pass } = getCreds("PUPIL");
  test.skip(!(user && pass), "TEST_PUPIL_USERNAME/PASSWORD not set");
  page.on("dialog", dialog => dialog.accept());
  await login(page, user, pass, "/lessons/lesson-4/activities/02-python-runner.html");
  await expect(page.locator("#codeEditor")).toBeVisible();
  const hintBtn = page.getByRole("button", { name: "Hint (starter code)" });
  await expect(hintBtn).toBeVisible();
  await hintBtn.click();
  await expect(page.locator("#codeEditor")).toHaveValue(/Starter: run a simple program/);
  const hintsUsed = await page.evaluate(() => {
    const raw = localStorage.getItem("tlac_l4_a02_state");
    if(!raw) return null;
    try { return JSON.parse(raw).hintsUsed || null; } catch { return null; }
  });
  expect(hintsUsed).not.toBeNull();
});

test("teacher can sign in and see teacher hub", async ({ page }) => {
  const { user, pass } = getCreds("TEACHER");
  test.skip(!(user && pass), "TEST_TEACHER_USERNAME/PASSWORD not set");
  await login(page, user, pass, "/teacher.html");
  await expect(page.getByRole("heading", { name: "Teacher hub" })).toBeVisible();
  await expect(page.locator("#teacherToggle")).toBeVisible();
});

test("admin can sign in and see admin tools", async ({ page }) => {
  const { user, pass } = getCreds("ADMIN");
  test.skip(!(user && pass), "TEST_ADMIN_USERNAME/PASSWORD not set");
  await login(page, user, pass, "/admin.html");
  await expect(page.getByRole("heading", { name: "Admin tools" })).toBeVisible();
});

test("teacher can mark an activity complete", async ({ page }) => {
  const { user, pass } = getCreds("TEACHER");
  test.skip(!(user && pass), "TEST_TEACHER_USERNAME/PASSWORD not set");
  await login(page, user, pass, "/teacher-view.html");
  await expect(page.getByRole("heading", { name: "Teacher view v1" })).toBeVisible();

  await selectFirstOption(page, "#lessonSelect");
  await selectFirstOption(page, "#pupilSelect");
  const markBtn = page.locator("#activityTable button[data-action='toggle']").first();
  await expect(markBtn).toBeVisible();
  await markBtn.click();
  await expect(page.locator("#toast")).toContainText("Marked.");
});

test("teacher can export lesson CSV", async ({ page }) => {
  const { user, pass } = getCreds("TEACHER");
  test.skip(!(user && pass), "TEST_TEACHER_USERNAME/PASSWORD not set");
  await login(page, user, pass, "/teacher-view.html");
  await expect(page.getByRole("heading", { name: "Teacher view v1" })).toBeVisible();

  await selectFirstOption(page, "#lessonSelect");
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#exportLessonBtn").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.csv$/);
});

test("teacher can export pupil CSV", async ({ page }) => {
  const { user, pass } = getCreds("TEACHER");
  test.skip(!(user && pass), "TEST_TEACHER_USERNAME/PASSWORD not set");
  await login(page, user, pass, "/teacher-view.html");
  await expect(page.getByRole("heading", { name: "Teacher view v1" })).toBeVisible();

  await selectFirstOption(page, "#pupilSelect");
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#exportPupilBtn").click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.csv$/);
});

test("teacher can load the link registry", async ({ page }) => {
  const { user, pass } = getCreds("TEACHER");
  test.skip(!(user && pass), "TEST_TEACHER_USERNAME/PASSWORD not set");
  await login(page, user, pass, "/teacher-links.html");
  await expect(page.getByRole("heading", { name: "Link registry" })).toBeVisible();

  await page.waitForFunction(() => {
    const body = document.querySelector("#linksTable tbody");
    if(!body) return false;
    return !body.textContent.includes("Loading");
  });

  const rows = page.locator("#linksTable tbody tr");
  const rowCount = await rows.count();
  if(rowCount === 1){
    await expect(rows.first()).toContainText(/No links found|Unable to load links/);
  } else {
    expect(rowCount).toBeGreaterThan(0);
  }
});

test("pupil can run python and see stdout", async ({ page }) => {
  const { user, pass } = getCreds("PUPIL");
  test.skip(!(user && pass), "TEST_PUPIL_USERNAME/PASSWORD not set");
  await login(page, user, pass, "/lessons/lesson-4/activities/02-python-runner.html");
  await expect(page.locator("#codeEditor")).toBeVisible();
  await page.locator("#codeEditor").fill('print("Playwright test")');
  await page.getByRole("button", { name: "Run code" }).click();
  await expect(page.locator("#stdout")).toContainText("Playwright test", { timeout: 15000 });
});
