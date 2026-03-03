/**
 * End-to-end smoke coverage for the current LaunchPad demo loop.
 * Validates login, opening build directly, generating recommendations,
 * saving a named variant, running compare simulations, and requesting best-variant advice.
 */
import { expect, test } from "@playwright/test";

test("happy path smoke", async ({ page }) => {
  test.setTimeout(240000);
  await page.goto("/");
  await expect(page.getByText("LaunchPad Conversion Lab")).toBeVisible();

  await page.locator("input").first().fill("demo@launchpad.ai");
  await page.locator("input[type='password']").fill("demo1234");
  await page.getByRole("button", { name: "Sign In" }).click();
  await page.waitForURL("**/campaigns", { timeout: 60000 });

  const openCampaign = page.getByRole("link", { name: "Open Campaign" });
  if ((await openCampaign.count()) > 0) {
    const href = await openCampaign.first().getAttribute("href");
    if (!href) throw new Error("Open Campaign link did not include target href.");
    await page.goto(href);
    await page.waitForURL("**/campaigns/*/build**", { timeout: 60000 });
  } else {
    await page.getByRole("button", { name: "Create New Campaign" }).click();
    await page.getByPlaceholder("Campaign name").fill("Urban Accessories Sprint");
    await page.getByPlaceholder("Product title").fill("Everyday Sling");
    await page.getByPlaceholder("Category (e.g. Bags)").fill("Accessories");
    await page.getByPlaceholder("Audience segment (e.g. Mobile first shoppers)").fill("Mobile first shoppers");
    await page.getByPlaceholder("Brief product description for the landing page").fill("A compact sling bag for daily carry.");
    await page.getByRole("button", { name: "Create", exact: true }).click();
    const href = await page.getByRole("link", { name: "Open Campaign" }).first().getAttribute("href");
    if (!href) throw new Error("Open Campaign link did not include target href after create.");
    await page.goto(href);
    await page.waitForURL("**/campaigns/*/build**", { timeout: 60000 });
  }

  await expect(page.getByRole("button", { name: "Ask Codex For Recommendations" })).toBeVisible({ timeout: 120000 });
  await page.getByRole("button", { name: "Ask Codex For Recommendations" }).click();
  const proposal = page.getByTestId(/proposal-/).first();
  await expect(proposal).toBeVisible({ timeout: 120000 });
  await proposal.click();
  await page.getByPlaceholder("Name this variant (required)").fill("E2E Variant");
  const saveButton = page.getByRole("button", { name: "Mark This Change and Save Variant" });
  if (!(await saveButton.isEnabled())) {
    await proposal.click();
  }
  await expect(saveButton).toBeEnabled({ timeout: 15000 });
  await saveButton.click();

  await page.getByRole("link", { name: "Go To Compare" }).click();
  await page.getByRole("button", { name: "Run Simulation" }).click();
  await page.getByRole("button", { name: "Ask Codex Which Variant Is Best" }).click();
  const revealButton = page.getByRole("button", { name: "Reveal Recommendation" });
  await expect(revealButton).toBeVisible({ timeout: 180000 });
  await revealButton.click();
  await expect(page.getByText("Recommended Variant:")).toBeVisible({ timeout: 120000 });
});
