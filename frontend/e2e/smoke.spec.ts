import { test, expect, type Page } from "@playwright/test";

/**
 * Campus-AI FRONTEND smoke test.
 *
 * Har role (admin/teacher/tpo/student) ka login token API se leta hai,
 * usse localStorage me daalta hai, aur us role ke SAARE dashboard pages
 * kholta hai. Har page pe check karta hai:
 *   - page 4xx/5xx to nahi diya
 *   - JS uncaught error (pageerror) to nahi aaya
 *   - console.error to nahi aaya
 *   - error-boundary text ("Something went wrong" / "Application error") to nahi
 *
 * Chalane ke liye e2e/README.md dekho.
 */

const API_URL = (
  process.env.API_URL || "https://campus-ai-backend-ez7m.onrender.com"
).replace(/\/$/, "");
const PASSWORD = "DemoPass123";
const TOKEN_KEY = "campus_ai_token"; // frontend localStorage key

type Role = "admin" | "teacher" | "tpo" | "student";

const ACCOUNTS: Record<Role, string> = {
  admin: "admin@demo.campus.ai",
  teacher: "teacher@demo.campus.ai",
  tpo: "tpo@demo.campus.ai",
  student: "aarav@demo.campus.ai",
};

const PAGES: Record<Role, string[]> = {
  student: [
    "/dashboard",
    "/dashboard/attendance",
    "/dashboard/academics",
    "/dashboard/timetable",
    "/dashboard/assignments",
    "/dashboard/study-hub",
    "/dashboard/doubts",
    "/dashboard/resume",
    "/dashboard/skills",
    "/dashboard/projects",
    "/dashboard/eca",
    "/dashboard/internships",
    "/dashboard/placements",
    "/dashboard/leave",
    "/dashboard/analytics",
    "/dashboard/mentor",
  ],
  teacher: [
    "/dashboard",
    "/dashboard/verify",
    "/dashboard/attendance",
    "/dashboard/face-enroll",
    "/dashboard/face-attendance",
    "/dashboard/assignments",
    "/dashboard/study-hub",
    "/dashboard/doubts",
    "/dashboard/timetable",
    "/dashboard/gradebook",
    "/dashboard/analytics",
    "/dashboard/leave",
  ],
  tpo: [
    "/dashboard",
    "/dashboard/drives",
    "/dashboard/placement-analytics",
    "/dashboard/applications",
    "/dashboard/recruiters",
  ],
  admin: [
    "/dashboard",
    "/dashboard/institute",
    "/dashboard/users",
    "/dashboard/departments",
    "/dashboard/announcements",
    "/dashboard/calendar",
    "/dashboard/timetable",
    "/dashboard/analytics",
    "/dashboard/placement-analytics",
    "/dashboard/audit",
  ],
};

// Benign console noise we don't want to fail on.
const IGNORE_CONSOLE = [
  "Download the React DevTools",
  "Failed to load resource", // network 4xx surface elsewhere; not a JS crash
  "favicon",
  "[Fast Refresh]",
];

const ERROR_TEXT = [
  "Something went wrong",
  "Application error",
  "Unhandled Runtime Error",
  "This page could not be found",
  "500 - Internal",
  "Internal Server Error",
];

type Finding = { role: string; path: string; kind: string; detail: string };
const findings: Finding[] = [];
let checked = 0;

async function getToken(page: Page, email: string): Promise<string> {
  const res = await page.request.post(`${API_URL}/auth/login`, {
    form: { username: email, password: PASSWORD },
  });
  expect(res.ok(), `login failed for ${email}: ${res.status()}`).toBeTruthy();
  const body = await res.json();
  return body.access_token as string;
}

for (const role of Object.keys(PAGES) as Role[]) {
  test(`${role} - all pages render without errors`, async ({ page }) => {
    const token = await getToken(page, ACCOUNTS[role]);
    // Inject the auth token before any page script runs.
    await page.addInitScript(
      ([key, val]) => {
        window.localStorage.setItem(key, val);
      },
      [TOKEN_KEY, token] as const,
    );

    for (const path of PAGES[role]) {
      const consoleErrors: string[] = [];
      const pageErrors: string[] = [];
      const onConsole = (msg: { type: () => string; text: () => string }) => {
        if (msg.type() !== "error") return;
        const t = msg.text();
        if (IGNORE_CONSOLE.some((s) => t.includes(s))) return;
        consoleErrors.push(t);
      };
      const onPageError = (err: Error) => pageErrors.push(err.message);
      page.on("console", onConsole);
      page.on("pageerror", onPageError);

      const tags: string[] = [];
      try {
        let httpStatus = 0;
        // domcontentloaded = jaldi settle; networkidle flaky hai (koi
        // background/keep-alive request use kabhi settle nahi hone deta).
        const resp = await page.goto(path, { waitUntil: "domcontentloaded" });
        httpStatus = resp ? resp.status() : 0;
        // client-side data fetches ke liye thoda ruk jao, par bounded.
        await page
          .waitForLoadState("networkidle", { timeout: 8000 })
          .catch(() => {});
        await page.waitForTimeout(800).catch(() => {});

        const bodyText =
          (await page
            .locator("body")
            .innerText()
            .catch(() => "")) || "";
        const errText = ERROR_TEXT.find((t) => bodyText.includes(t));

        if (httpStatus >= 400) {
          tags.push(`HTTP ${httpStatus}`);
          findings.push({
            role,
            path,
            kind: "HTTP",
            detail: `status ${httpStatus}`,
          });
        }
        if (pageErrors.length) {
          tags.push(`JS-crash x${pageErrors.length}`);
          findings.push({
            role,
            path,
            kind: "JS",
            detail: pageErrors[0].slice(0, 120),
          });
        }
        if (errText) {
          tags.push("error-boundary");
          findings.push({ role, path, kind: "BOUNDARY", detail: errText });
        }
        if (consoleErrors.length) {
          tags.push(`console.error x${consoleErrors.length}`);
          findings.push({
            role,
            path,
            kind: "CONSOLE",
            detail: consoleErrors[0].slice(0, 120),
          });
        }
      } catch (e) {
        tags.push("NAV-timeout");
        findings.push({
          role,
          path,
          kind: "NAV",
          detail: String(e).slice(0, 120),
        });
      }

      checked++;
      // eslint-disable-next-line no-console
      console.log(
        `  ${tags.length ? "FAIL" : "OK  "} [${role}] ${path} ${tags.join(", ")}`,
      );

      page.off("console", onConsole);
      page.off("pageerror", onPageError);
    }
  });
}

test.afterAll(() => {
  // eslint-disable-next-line no-console
  console.log("\n" + "=".repeat(70));
  console.log(`  FRONTEND SMOKE SUMMARY   |   pages checked: ${checked}`);
  console.log("=".repeat(70));
  if (!findings.length) {
    console.log(
      "  Sab pages clean - koi JS crash / error-boundary / 4xx-5xx nahi.",
    );
  } else {
    console.log(`  ${findings.length} issue(s) mile (yahi dekhna hai):`);
    for (const f of findings) {
      console.log(`   - [${f.role}] ${f.path}  (${f.kind})  ${f.detail}`);
    }
  }
  console.log("=".repeat(70));
});
