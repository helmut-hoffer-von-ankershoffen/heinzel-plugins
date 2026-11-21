import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { closeSetup } from "./personal_conversation.mjs";

const [url, engine, corePackage, executable] = process.argv.slice(2);
const require = createRequire(corePackage);
const { chromium, webkit } = require("playwright-core");
const axe = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const browser = await (engine === "webkit" ? webkit : chromium).launch({ headless: true });
const context = await browser.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 } });
const page = await context.newPage();
try {
  await page.goto(url);
  await closeSetup(page);
  await page.getByRole("button", { name: "Google source review" }).click();
  const panel = page.getByRole("region", { name: "Google source review", exact: true });
  await panel.waitFor();
  assert.match(await panel.innerText(), /does not authenticate the publisher/);
  assert.match(await panel.innerText(), /does not access your Google account or grant a read/);
  assert.ok((await panel.innerText()).includes(executable));
  assert.match(await panel.innerText(), /SHA-256: [0-9a-f]{64}/);
  await page.evaluate(axe);
  const violations = await panel.evaluate(async (node) => (await window.axe.run(node)).violations.map(({ id }) => id));
  assert.deepEqual(violations, []);
  const onScreen = await panel.evaluate((element) => new Promise((resolve) => {
    const observer = new IntersectionObserver(([entry]) => {
      observer.disconnect();
      resolve(entry.isIntersecting && entry.intersectionRatio > 0);
    });
    observer.observe(element);
  }));
  assert.equal(onScreen, true, "The selected source review must be on screen, not merely present in the DOM.");
  assert.equal(await panel.evaluate((node) => node.scrollWidth > node.clientWidth), false);
} finally {
  await browser.close();
}
