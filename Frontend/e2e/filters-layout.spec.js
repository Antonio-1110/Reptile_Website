import { expect, test } from '@playwright/test';

// On a phone the filters sit above the results, and used to fill the whole first screen, so people
// scrolled past every filter before seeing a listing (#94). They now start folded there; wider
// screens keep them open beside the results. Unit tests have no layout engine, so it's checked here.

const TEXT = {
  en: { show: 'Show filters', hide: 'Hide filters', male: 'Male' },
  zh: { show: '顯示篩選條件', hide: '收合篩選條件', male: '公' },
};

async function openMarketplace(page, language, viewport) {
  await page.addInitScript((lng) => localStorage.setItem('i18nextLng', lng), language);
  await page.setViewportSize(viewport);
  await page.goto('/marketplace');
  await expect(page.locator('.card-container').first()).toBeVisible();
}

const pageScrollsSideways = (page) => page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);

for (const language of ['en', 'zh']) {
  const text = TEXT[language];
  test.describe(`marketplace filters (${language})`, () => {
    test('on a phone they start folded, so listings show on the first screen', async ({ page }) => {
      await openMarketplace(page, language, { width: 375, height: 800 });
      const male = page.getByRole('button', { name: text.male, exact: true });
      await expect(male).toBeHidden();
      await expect(page.locator('.card-container').first(), 'the first listing is below the fold').toBeInViewport();

      await page.getByRole('button', { name: text.show }).click();
      await expect(male).toBeVisible();
      expect(await pageScrollsSideways(page), 'the page scrolls sideways').toBe(false);

      // The bottom button folds the filters and brings the top of the box back into view.
      await page.getByRole('button', { name: text.hide }).last().click();
      await expect(male).toBeHidden();
      await expect(page.getByRole('button', { name: text.show })).toBeInViewport();
    });

    test('on a laptop they stay open beside the results', async ({ page }) => {
      await openMarketplace(page, language, { width: 1280, height: 800 });
      await expect(page.getByRole('button', { name: text.male, exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: text.show })).toBeHidden();
      const sidebar = await page.locator('.filter-sidebar').boundingBox();
      const firstCard = page.locator('.card-container').first();
      await expect(firstCard).toBeInViewport();
      expect((await firstCard.boundingBox()).x, 'the listings are not beside the filters').toBeGreaterThan(sidebar.x + sidebar.width);
      expect(await pageScrollsSideways(page), 'the page scrolls sideways').toBe(false);
    });
  });
}
