import assert from "node:assert/strict";
import {
  closeSetup,
  openChat,
  openDetails,
  openJourney,
  reportFailure,
  sendMessage,
  startConversation,
} from "./personal_conversation.mjs";

const { axe, browser, context, page, token, url } = await openJourney(process.argv[2], process.argv[3], process.argv[4]);
try {
  await page.goto(url.href);
  await closeSetup(page);
  await startConversation(page);
  await sendMessage(page, "Inspect my selected source.");
  await page.getByText("Source inspected.").waitFor({ timeout: 30000 });
  await openDetails(page);
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
  await sendMessage(page, "Inspect now.");
  await page.getByText("Source inspected.").nth(1).waitFor({ timeout: 30000 });
  await page.getByText(/Tool activity for this reply/).nth(1).click();
  await page.getByText(/connected_read · completed/).first().waitFor();
  await panel.getByRole("button", { name: "Revoke this grant" }).click();
  await panel.getByText(/Recorded state: revoked/).waitFor();
  assert.equal(await panel.evaluate(node => node.scrollWidth > node.clientWidth), false);
  console.log(JSON.stringify({ accepted: true }));
} catch (error) {
  await reportFailure(page, token, error);
} finally {
  await context.close();
  await browser.close();
}
