import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(process.argv[4]);
const { chromium, webkit } = require("playwright-core");
const axe = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const url = new URL(process.argv[2]);
const token = url.hash.match(/(?:^#|&)token=([^&]+)/)?.[1] ?? "";
url.pathname = "/doctor";
const browser = await (process.argv[3] === "webkit" ? webkit : chromium).launch({ headless: true });
const context = await browser.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 } });
const page = await context.newPage();
// Core 0.9.40 sends from the personal conversation's own form; the page chat also has a "Send" button.
const sendToHeinzel = () =>
  page
    .locator("form")
    .filter({ has: page.getByLabel("Message your Heinzel") })
    .getByRole("button", { name: "Send", exact: true })
    .click();
// Core 0.9.40 keeps the terms, connected read, schedule and notification panels in the collapsed "Details".
const openDetails = async () => {
  const details = page.locator('xpath=//details[summary[normalize-space()="Details"]]');
  if (!(await details.evaluate((node) => node.open))) await details.locator("summary").first().click();
};
try {
  await page.goto(url.href);
  await page.locator("#splash").waitFor({ state: "hidden", timeout: 30000 });
  const setup = page.getByRole("dialog");
  await setup.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
  if (await setup.isVisible().catch(() => false)) await setup.getByRole("button", { name: "Close setup" }).click();
  if (!(await page.getByLabel("Your message").isVisible())) await page.getByRole("tab", { name: "Chat", exact: true }).click();
  await page.getByLabel("Your message").fill("Inspect my selected source.");
  await page.getByRole("button", { name: "Create a Heinzel and take this message" }).click();
  await sendToHeinzel();
  await page.getByText("Source inspected.").waitFor({ timeout: 30000 });
  await openDetails();
  const panel = page.getByRole("region", { name: "Connected read review" });
  await panel.getByLabel("Read operation").selectOption("mail.messages");
  await panel.getByLabel("Fixed arguments (JSON)").fill(JSON.stringify({query:"",window:{since:"2026-01-01T00:00:00Z",until:"2026-01-02T00:00:00Z"}}));
  await panel.getByRole("button", { name: "Prepare review" }).click();
  await panel.getByText("Account: fixture-account").waitFor();
  await panel.getByText(/Gmail may return candidate metadata outside/).waitFor();
  assert.match(await panel.innerText(), /gmail.readonly/);
  await panel.getByRole("button", { name: "Review access" }).click();
  await panel.getByRole("heading", { name: "Review connected read" }).waitFor();
  await page.evaluate(axe);
  assert.deepEqual(await panel.evaluate(async node => (await window.axe.run(node)).violations.map(({id}) => id)), []);
  await panel.getByRole("button", { name: "Confirm" }).click();
  await panel.getByText(/Recorded state: approved/).waitFor();
  await page.getByLabel("Message your Heinzel").fill("Inspect now.");
  await sendToHeinzel();
  await page.getByText("Source inspected.").nth(1).waitFor({ timeout: 30000 });
  await page.getByText(/Tool activity for this reply/).nth(1).click();
  await page.getByText(/connected_read · completed/).first().waitFor();
  await panel.getByRole("button", { name: "Revoke this grant" }).click();
  await panel.getByText(/Recorded state: revoked/).waitFor();
  assert.equal(await panel.evaluate(node => node.scrollWidth > node.clientWidth), false);
  console.log(JSON.stringify({ accepted: true }));
} catch (error) {
  const message = error instanceof Error ? (error.stack ?? error.message) : String(error);
  const visible = await page.locator("body").innerText().catch(() => "");
  process.stderr.write(`${message}\n${visible}`.replaceAll(decodeURIComponent(token), "<redacted-session>") + "\n");
  process.exitCode = 1;
} finally {
  await context.close();
  await browser.close();
}
