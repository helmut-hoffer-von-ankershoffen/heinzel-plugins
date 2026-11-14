// Core 0.9.40 personal conversation controls shared by the mounted Google journeys.

// Send from the conversation's own form; the page chat also has a "Send" button.
export const sendToHeinzel = (page) =>
  page
    .locator("form")
    .filter({ has: page.getByLabel("Message your Heinzel") })
    .getByRole("button", { name: "Send", exact: true })
    .click();

// The terms, connected read, schedule and notification panels sit in the collapsed "Details".
export const openDetails = async (page) => {
  const details = page.locator('xpath=//details[summary[normalize-space()="Details"]]');
  if (!(await details.evaluate((node) => node.open))) await details.locator("summary").first().click();
};
