// A valid theme can use a light decorative accent; normal text must keep foreground contrast.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFile } from "node:fs/promises";
const require = createRequire(new URL("../../web/package.json", import.meta.url));
const { chromium } = require("playwright-core");
const [url] = process.argv.slice(2);
assert.ok(url);
const browser = await chromium.launch().catch(() => chromium.launch({ channel: "chrome" }));
const page = await browser.newPage({ viewport: { width: 320, height: 844 }, isMobile: true, hasTouch: true });
await page.addInitScript(() => localStorage.setItem("hz.onboarding", JSON.stringify({ step: "you", visited: [], closed: true })));
try {
  await page.goto(url);
  const open = page.getByRole("button", { name: /^World clock(?: \(\d+\))?$/ });
  await open.waitFor();
  await page.evaluate(() => {
    const style = document.documentElement.style;
    for (const key of ["--primary", "--color-primary"]) style.setProperty(key, "#ffcc00");
    for (const key of ["--primary-foreground", "--color-primary-foreground"]) style.setProperty(key, "#111111");
  });
  await open.click();
  const panel = page.getByRole("region", { name: "World clock", exact: true });
  await panel.getByText("Primary", { exact: true }).waitFor();
  await page.evaluate(await readFile(require.resolve("axe-core/axe.min.js"), "utf8"));
  const violations = await panel.evaluate(async (element) => {
    const result = await window.axe.run(element, { runOnly: { type: "rule", values: ["color-contrast"] } });
    return result.violations.map(({ id, nodes }) => ({ id, nodes: nodes.map(({ html, failureSummary }) => ({ html, failureSummary })) }));
  });
  assert.deepEqual(violations, [], "Clock text must remain readable at 320px with a light theme accent");
} finally {
  await browser.close();
}
