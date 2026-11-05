import assert from "node:assert/strict";
import { test } from "node:test";
import { instrumentLaunch } from "./diagnostic-adapter.mjs";

function fixture(failure) {
  const calls = [], reports = [];
  let onPage;
  const page = {
    locator() { return new Locator(); },
    async evaluate() { calls.push("failure geometry"); return { entries: [{ width: 390, height: 844 }] }; },
  };
  class Locator {
    page() { return page; }
    async press(...args) { calls.push({ receiver: this, args }); if (failure) throw failure; return "native result"; }
  }
  const context = { async addInitScript(script) { calls.push({ script }); }, on(type, handler) { assert.equal(type, "page"); onPage = handler; } };
  const browser = { async newContext(...args) { calls.push({ contextArgs: args }); return context; } };
  const chromium = { async launch(...args) { calls.push({ launchArgs: args }); return browser; } };
  const monitor = instrumentLaunch(chromium, (report) => reports.push(report));
  return { chromium, calls, reports, monitor, page, attach: () => onPage(page) };
}

test("passes native input/launch/context arguments and results through without geometry reads", async () => {
  const f = fixture();
  const launchOptions = { channel: "chrome" }, contextOptions = { isMobile: true }, pressOptions = { timeout: 30000 };
  const browser = await f.chromium.launch(launchOptions);
  await browser.newContext(contextOptions);
  f.attach();
  const locator = f.page.locator("unused");
  assert.equal(await locator.press("Enter", pressOptions), "native result");
  assert.equal(f.calls[0].launchArgs[0], launchOptions);
  assert.equal(f.calls[1].contextArgs[0], contextOptions);
  assert.equal(f.calls.at(-1).receiver, locator);
  assert.deepEqual(f.calls.at(-1).args, ["Enter", pressOptions]);
  assert.equal(f.calls.includes("failure geometry"), false);
  assert.equal(f.reports.length, 0);
});

test("captures the real press failure before cleanup and rethrows the same original error", async () => {
  const original = new Error("original native failure");
  const f = fixture(original);
  const browser = await f.chromium.launch();
  await browser.newContext();
  f.attach();
  await assert.rejects(f.page.locator("unused").press("Enter"), (error) => error === original);
  assert.equal(f.calls.at(-1), "failure geometry");
  assert.equal(f.reports[0].entries[0].width, 390);
  f.monitor();
  assert.equal(f.reports.length, 1, "uncaught monitor must not duplicate collected evidence");
});

test("a diagnostic failure cannot replace the original exception", async () => {
  const original = new Error("original native failure");
  const f = fixture(original);
  f.page.evaluate = () => { throw new Error("diagnostics unavailable"); };
  await (await f.chromium.launch()).newContext();
  f.attach();
  await assert.rejects(f.page.locator("unused").press("Enter"), (error) => error === original);
  f.monitor();
  assert.deepEqual(f.reports, [{ unavailable: true, boundary: "uncaughtExceptionMonitor" }]);
});

test("preload and original ESM driver share the exact owning pinned Playwright instance", async () => {
  const { createRequire } = await import("node:module");
  const { readFileSync } = await import("node:fs");
  const { pathToFileURL } = await import("node:url");
  const owningPackage = new URL("../../web/package.json", import.meta.url);
  const require = createRequire(owningPackage);
  const original = await import(pathToFileURL(require.resolve("playwright-core").replace(/index\.js$/, "index.mjs")));
  assert.equal(require("playwright-core").chromium, original.chromium);
  assert.equal(require("playwright-core/package.json").version, JSON.parse(readFileSync(owningPackage)).devDependencies["playwright-core"]);
});

test("the monitor leaves an uncaught original error and nonzero process exit intact", async () => {
  const { spawnSync } = await import("node:child_process");
  const result = spawnSync(process.execPath, ["--input-type=module", "-e", `
    import { instrumentLaunch } from ${JSON.stringify(new URL("./diagnostic-adapter.mjs", import.meta.url).href)};
    class Locator {
      page() { return page; }
      async press() { throw new Error("fixture original failure"); }
    }
    const page = { locator: () => new Locator(), evaluate: async () => ({ entries: [{ width: 390 }] }) };
    const context = { addInitScript: async () => {}, on: (_, handler) => handler(page) };
    const chromium = { launch: async () => ({ newContext: async () => context }) };
    process.on("uncaughtExceptionMonitor", instrumentLaunch(chromium));
    await (await chromium.launch()).newContext();
    await page.locator().press("Enter");
  `], { encoding: "utf8", timeout: 2000 });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Error: fixture original failure/);
  assert.match(result.stderr, /Tailscale failure lifecycle:.*"width":390/);
});
