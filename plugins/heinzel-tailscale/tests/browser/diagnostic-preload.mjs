import { createRequire } from "node:module";
import { instrumentLaunch } from "./diagnostic-adapter.mjs";

// Resolve the exact same owning, locked Playwright package as the unchanged original driver.
const require = createRequire(new URL("../../web/package.json", import.meta.url));
const { chromium } = require("playwright-core");
process.on("uncaughtExceptionMonitor", instrumentLaunch(chromium));
