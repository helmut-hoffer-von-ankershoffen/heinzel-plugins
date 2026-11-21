import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

// Core 0.9.53 personal conversation controls shared by the mounted Google journeys, as Core's own chat journeys
// (web/e2e/chat-ready.mjs) drive them: the first start names the Heinzel, its page holds the reviews beside its chat.

/** The composer of the Heinzel's chat: "Message <name>". */
export const heinzelComposer = (page) =>
  page.getByRole("complementary", { name: "Chat" }).getByRole("textbox", { name: /^Message / });

/** Neither the splash nor a dialog holds the app inert. */
export async function appTakesInput(page) {
  await page.waitForFunction(
    () => {
      const root = document.getElementById("root");
      return root !== null && !root.hasAttribute("inert") && document.getElementById("splash")?.hidden !== false;
    },
    null,
    { timeout: 15000 },
  );
}

/** Close the first-run setup when it opens, and wait until the app takes input. */
export async function closeSetup(page) {
  await page.locator("#splash").waitFor({ state: "hidden", timeout: 30000 });
  const setup = page.getByRole("dialog", { name: "Set up hz" });
  await setup.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
  if (await setup.isVisible().catch(() => false)) {
    await setup.getByRole("button", { name: "Close setup" }).click();
    await setup.waitFor({ state: "hidden", timeout: 15000 });
  }
  await appTakesInput(page);
}

/** With no Heinzel yet the chat is the first start: press Start with the suggested name and look, then wait for the composer. */
export async function startConversation(page) {
  const chat = page.getByRole("complementary", { name: "Chat" });
  const name = chat.getByLabel("What do you call it?");
  if (!(await name.isVisible())) await page.getByRole("tab", { name: "Chat", exact: true }).click();
  await name.waitFor({ timeout: 30000 });
  await appTakesInput(page);
  await chat.getByRole("button", { name: "Start", exact: true }).click();
  await heinzelComposer(page).waitFor({ timeout: 30000 });
}

/** Open the chat tab again after a reload: wait for startup to end, then press the tab. */
export async function openChat(page) {
  await page.locator("#splash").waitFor({ state: "hidden" });
  await appTakesInput(page);
  const tab = page.getByRole("tab", { name: "Chat", exact: true });
  if (await tab.count()) {
    await tab.press("Enter");
    await page.getByRole("tab", { name: "Chat", exact: true, selected: true }).waitFor();
  }
  await heinzelComposer(page).waitFor({ timeout: 30000 });
}

/** Send a message from the Heinzel's chat. */
export async function sendMessage(page, text) {
  const composer = heinzelComposer(page);
  await composer.fill(text);
  await page.getByRole("complementary", { name: "Chat" }).getByRole("button", { name: "Send" }).click();
}

/**
 * Open the Heinzel's page (reviews, terms, recurring turns) beside its chat: the chat's More, About. On a phone, where
 * Page and Chat are tabs, the chat is shown again with the page above it, so both are in reach.
 */
export async function openDetails(page) {
  const chat = page.getByRole("complementary", { name: "Chat" });
  await heinzelComposer(page).waitFor({ timeout: 30000 });
  const heading = page.getByRole("heading", { level: 1, name: /, your Heinzel$/ });
  const opened = !(await heading.isVisible());
  if (opened) {
    await chat.getByRole("button", { name: "More: search, about" }).click();
    await page
      .getByRole("dialog", { name: "More" })
      .getByRole("button", { name: /^About / })
      .click();
  }
  await heading.waitFor({ timeout: 30000 });
  const chatTab = page.getByRole("tab", { name: "Chat", exact: true });
  const pageTab = page.getByRole("tab", { name: "Page", exact: true });
  if (opened && (await pageTab.count()))
    await page.getByRole("tab", { name: "Page", exact: true, selected: true }).waitFor({ timeout: 30000 });
  if ((await chatTab.count()) && !(await heinzelComposer(page).isVisible())) {
    await chatTab.press("Enter");
    await page.getByRole("tab", { name: "Chat", exact: true, selected: true }).waitFor();
  }
  await heinzelComposer(page).waitFor();
  // WebKit sometimes leaves a <select> of an open disclosure with checkVisibility() false although it is painted; one
  // restyle clears it (the same step as Core's journeys).
  const selects = await page.locator("main").locator("select").all();
  await Promise.all(selects.map((select) => select.evaluate(quirkRestyled)));
}

// Runs in the page, so it stands alone.
const quirkRestyled = (node) => {
  if (node.checkVisibility()) return false;
  for (let element = node; element; element = element.parentElement) {
    const style = getComputedStyle(element);
    if (element.nodeName === "DETAILS" && !element.open) return false;
    if (element.hidden || style.display === "none" || style.visibility !== "visible") return false;
  }
  const rect = node.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return false;
  const color = node.style.color;
  node.style.color = "rgb(1, 2, 3)";
  void getComputedStyle(node).color;
  node.style.color = color;
  void getComputedStyle(node).color;
  return true;
};

/** The phone-sized browser a journey runs in, at /doctor: `urlArgument` and `engine` are the app's URL and the engine. */
export async function openJourney(urlArgument, engine, corePackage) {
  const require = createRequire(corePackage);
  const { chromium, webkit } = require("playwright-core");
  const axe = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
  const url = new URL(urlArgument);
  const token = url.hash.match(/(?:^#|&)token=([^&]+)/)?.[1] ?? "";
  url.pathname = "/doctor";
  const browser = await (engine === "webkit" ? webkit : chromium).launch({ headless: true });
  const context = await browser.newContext({ serviceWorkers: "block", viewport: { width: 390, height: 844 } });
  return { axe, browser, context, page: await context.newPage(), token, url };
}

/** Say what failed and what the page showed, without the session token. */
export async function reportFailure(page, token, error) {
  const message = error instanceof Error ? (error.stack ?? error.message) : String(error);
  const visible = await page
    .locator("body")
    .innerText()
    .catch(() => "");
  process.stderr.write(`${`${message}\n${visible}`.replaceAll(decodeURIComponent(token), "<redacted-session>")}\n`);
  process.exitCode = 1;
}
