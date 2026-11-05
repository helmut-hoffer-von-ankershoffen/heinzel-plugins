import { installDiagnostics } from "./diagnostics.mjs";

// Observe the failed Playwright API boundary while the original driver's finally block still owns the browser.
// The original press receives unchanged arguments/receiver, and its original error is rethrown unchanged.
export function instrumentLaunch(chromium, emit = (value) => console.error("Tailscale failure lifecycle:", JSON.stringify(value))) {
  const launch = chromium.launch;
  const prototypes = new WeakSet();
  let reported = false;
  chromium.launch = async function (...args) {
    const browser = await Reflect.apply(launch, this, args);
    const newContext = browser.newContext;
    browser.newContext = async function (...contextArgs) {
      const context = await Reflect.apply(newContext, this, contextArgs);
      await context.addInitScript(installDiagnostics);
      context.on("page", (page) => {
        const prototype = Object.getPrototypeOf(page.locator("html"));
        if (prototypes.has(prototype)) return;
        prototypes.add(prototype);
        const press = prototype.press;
        prototype.press = async function (...pressArgs) {
          try {
            return await Reflect.apply(press, this, pressArgs);
          } catch (error) {
            let timer;
            try {
              const evidence = await Promise.race([
              this.page().evaluate(() => window.__tailscaleDiagnostics?.()).catch(() => null),
              new Promise((resolve) => { timer = setTimeout(() => resolve(null), 1000); }),
              ]).finally(() => clearTimeout(timer));
              reported = true;
              emit(evidence ?? { unavailable: true, boundary: "Locator.press" });
            } catch {
              // Evidence collection must never replace or consume the original browser failure.
            }
            throw error;
          }
        };
      });
      return context;
    };
    return browser;
  };
  return () => {
    if (!reported) emit({ unavailable: true, boundary: "uncaughtExceptionMonitor" });
  };
}
