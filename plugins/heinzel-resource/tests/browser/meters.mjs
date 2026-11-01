import assert from "node:assert/strict";
import {createRequire} from "node:module";
const require = createRequire(new URL("../../web/package.json", import.meta.url));
const {chromium} = require("playwright-core");
const [url] = process.argv.slice(2);
const browser = await chromium.launch().catch(() => chromium.launch({channel:"chrome"}));
try {
  const page = await browser.newPage({viewport:{width:1280,height:900}});
  await page.addInitScript(() => localStorage.setItem("hz.onboarding", JSON.stringify({step:"you", visited:[], closed:true})));
  await page.goto(url);
  await page.locator("#splash").waitFor({state:"hidden"});
  // Not scoped to the footer: when the meter doesn't fit, "More status items" shows it in a popover outside it.
  const control = page.locator('[data-footer-content="resource:machine"] button').first();
  for (const width of [1280,360,390]) {
    await page.setViewportSize({width,height:900});
    await page.evaluate(async () => {await document.fonts.ready; await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));});
    const more = page.getByRole("button",{name:"More status items",exact:true});
    if (!await control.isVisible()) await more.click();
    await control.waitFor({state:"visible"});
    assert.match(await control.getAttribute("aria-label"), /CPU.*Memory.*Load/);
    assert.equal(await control.locator('span[aria-hidden] > span').count(),3);
    await control.click();
    const detail = page.getByRole("region",{name:/^Computer resources/});
    await detail.waitFor();
    assert.match(await detail.innerText(),/Host:.*CPU:.*Memory:.*Load \(1 min\):/s);
    const box = await detail.boundingBox();
    assert.ok(box && box.x >= 0 && box.x + box.width <= width + 1);
    await page.keyboard.press("Escape");
    const popup = page.getByRole("region",{name:"More status items",exact:true});
    if (await popup.isVisible()) await page.keyboard.press("Escape");
  }
} finally {await browser.close();}
