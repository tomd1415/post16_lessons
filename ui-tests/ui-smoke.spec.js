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
  await expect(page.locator("#codeEditor")).toHaveValue(/# Starter skeleton/);
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
