import assert from "node:assert/strict";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import {
  closeSetup,
  openChat,
  openDetails,
  openJourney,
  reportFailure,
  sendMessage,
  startConversation,
} from "./personal_conversation.mjs";

const { axe, browser, context, page, token, url } = await openJourney(process.argv[2], process.argv[3], process.argv[6]);
try {
  await page.goto(url.href);
  await closeSetup(page);
  await startConversation(page);
  await sendMessage(page, "Read my selected source.");
  await page.getByText("Source inspected.").waitFor({ timeout: 30000 });
  await openDetails(page);
  const terms = page.getByRole("region", { name: "Proposed Heinzel terms" });
  await terms.getByRole("button", { name: "Review these terms" }).click();
  await terms.getByRole("button", { name: "Confirm" }).click();
  await terms.getByText("These exact terms were accepted.").waitFor();
  const panel = page.getByRole("region", { name: "Connected read review" });
  await panel.getByLabel("Read operation").selectOption("calendar.events");
  if (process.argv[5] === "rolling") {
    await panel.getByRole("checkbox", { name: /Use a rolling window/ }).check();
    await panel.getByLabel("Lookback seconds").fill("60");
    await panel.getByLabel("Lookahead seconds").fill("600");
    await panel.getByLabel("Display timezone (IANA)").fill("Europe/Berlin");
    await panel.getByLabel("Fixed arguments (JSON)").fill("{}");
  } else {
    await panel
      .getByLabel("Fixed arguments (JSON)")
      .fill(JSON.stringify({ window: { since: "2026-01-01T00:00:00Z", until: "2026-01-02T00:00:00Z" } }));
  }
  await panel.getByRole("button", { name: "Prepare review" }).click();
  await panel.getByText("Account: fixture-account").waitFor();
  await panel.getByRole("button", { name: "Review access" }).click();
  await panel.getByRole("heading", { name: "Review connected read" }).waitFor();
  await page.evaluate(axe);
  const violations = await panel.evaluate(async (node) => (await window.axe.run(node)).violations.map(({ id }) => id));
  assert.deepEqual(violations, []);
  await panel.getByRole("button", { name: "Confirm" }).click();
  await panel.getByText(/Recorded state: approved/).waitFor();
  const schedule = page.locator('xpath=//details[summary[normalize-space()="Recurring Heinzel turns"]]');
  await schedule.getByText("Recurring Heinzel turns", { exact: true }).click();
  const consent = await schedule.getByRole("checkbox", { name: /Allow the separately approved calendar.events/ });
  assert.equal(await consent.isChecked(), false);
  await consent.check();
  await schedule.getByLabel("Requests per turn").fill("4");
  await schedule.getByRole("button", { name: "Propose recurring turns" }).click();
  await schedule.getByRole("button", { name: "Review this schedule" }).click();
  const card = schedule.getByRole("heading", { name: "Review Heinzel schedule" }).locator("../..");
  assert.match(await card.innerText(), /fixture-account/);
  assert.match(await card.innerText(), /calendar.readonly/);
  if (process.argv[5] === "rolling") assert.match(await card.innerText(), /rolling-window/);
  assert.doesNotMatch(await card.innerText(), /approval_proof/);
  await page.evaluate(axe);
  const scheduleViolations = await schedule.evaluate(async (node) =>
    (await window.axe.run(node)).violations.map(({ id }) => id),
  );
  assert.deepEqual(scheduleViolations, []);
  await schedule.getByRole("button", { name: "Confirm" }).click();
  await schedule.getByText(/approved; the daemon must be running/i).waitFor();
  const session = new URLSearchParams(page.url().split("?")[1]).get("chat");
  assert.ok(session);
  const directory = process.argv[4];
  writeFileSync(join(directory, "daemon-start.json"), JSON.stringify({ session }));
  for (let i = 0; i < 1800 && !existsSync(join(directory, "daemon-finished.json")); i++)
    await new Promise((resolve) => setTimeout(resolve, 50));
  const finished = JSON.parse(readFileSync(join(directory, "daemon-finished.json"), "utf8"));
  assert.equal(finished.ok, true, `daemon failed: ${finished.failure}`);
  assert.equal(finished.deduplicated, true);
  await page.reload();
  await openChat(page);
  await openDetails(page);
  await page
    .getByText(/Tool activity for this reply/)
    .nth(1)
    .click();
  await page
    .getByText(/connected_read · completed/)
    .first()
    .waitFor({ timeout: 30000 });
  await sendMessage(page, "Read my source and prepare a notification for my review.");
  const drafts = page.getByRole("region", { name: "Notification drafts" });
  await drafts.getByText("The source was read; please review.", { exact: true }).waitFor({timeout: 30000});
  assert.match(await drafts.innerText(), /queued does not mean shown/i);
  await drafts.getByRole("button", { name: "Review notification" }).click();
  const review = drafts.getByRole("heading", { name: "Review notification" }).locator("../..");
  assert.match(await review.innerText(), /Review requested/);
  assert.doesNotMatch(await review.innerText(), /approval_proof/);
  await page.evaluate(axe);
  assert.deepEqual(await drafts.evaluate(async (node) => (await window.axe.run(node)).violations.map(({id}) => id)), []);
  await drafts.getByRole("button", { name: "Confirm" }).click();
  await drafts.getByText("Queued under local policy; display is not confirmed.").waitFor();
  await panel.getByRole("button", { name: "Revoke this grant" }).click();
  await panel.getByText(/Recorded state: revoked/).waitFor();
  await page.reload();
  await openChat(page);
  await openDetails(page);
  await schedule.getByText("Recurring Heinzel turns", { exact: true }).click();
  await schedule.getByText(/stale · contract revision/).waitFor();
  assert.equal(await panel.evaluate((node) => node.scrollWidth > node.clientWidth), false);
  console.log(JSON.stringify({ accepted: true }));
} catch (error) {
  await reportFailure(page, token, error);
} finally {
  await context.close();
  await browser.close();
}
