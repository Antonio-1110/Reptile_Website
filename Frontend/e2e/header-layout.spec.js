import { expect, test } from '@playwright/test';
import { signInWithApi } from './helpers';

// Unit tests run without a layout engine, so this is where a header that wraps, overlaps or scrolls
// sideways gets caught. It checks the geometry itself, in both languages, signed out and in.

async function useLanguage(page, language) {
  await page.addInitScript((lng) => localStorage.setItem('i18nextLng', lng), language);
}

// Where the header's parts sit, in CSS pixels.
async function measureHeader(page) {
  return page.evaluate(() => {
    const box = (selector) => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      if (!rect.width && !rect.height) return null; // display: none
      return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, height: rect.height, width: rect.width };
    };
    return {
      header: box('.header'),
      logo: box('.logo'),
      brand: box('.leftSection'),
      search: box('.searchForm'),
      nav: box('.rightSection'),
      menuButton: box('.headerMenuToggle'),
      pageWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
    };
  });
}

const overlaps = (a, b) => a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
const sameRow = (a, b) => Math.abs((a.top + a.bottom) / 2 - (b.top + b.bottom) / 2) < 8;

async function openAt(page, width, path = '/marketplace') {
  await page.setViewportSize({ width, height: 900 });
  await page.goto(path);
  await expect(page.locator('.header .searchBar')).toBeVisible();
}

function expectNoCollisions(m) {
  expect(m.pageWidth, 'the page scrolls sideways').toBeLessThanOrEqual(m.viewportWidth);
  for (const [name, part] of Object.entries({ brand: m.brand, search: m.search, nav: m.nav, menuButton: m.menuButton })) {
    if (!part) continue;
    expect(part.right, `${name} runs past the header`).toBeLessThanOrEqual(m.header.right + 1);
    expect(part.left, `${name} runs past the header`).toBeGreaterThanOrEqual(m.header.left - 1);
  }
  if (m.nav) {
    expect(overlaps(m.nav, m.search), 'the links overlap the search bar').toBe(false);
    expect(overlaps(m.nav, m.brand), 'the links overlap the logo').toBe(false);
  }
  expect(overlaps(m.brand, m.search), 'the logo overlaps the search bar').toBe(false);
}

for (const language of ['en', 'zh']) {
  test.describe(`header layout (${language})`, () => {
    test.beforeEach(async ({ page }) => { await useLanguage(page, language); });

    // A 1440px laptop is the most common desktop; signed out, everything fits on one row there.
    test('signed out, a laptop-width header is one row', async ({ page }) => {
      for (const width of [1280, 1440, 1920]) {
        await openAt(page, width);
        const m = await measureHeader(page);
        expectNoCollisions(m);
        expect(m.nav, `links hidden at ${width}px`).not.toBeNull();
        expect(sameRow(m.search, m.logo), `search bar wrapped under the logo at ${width}px`).toBe(true);
        expect(sameRow(m.nav, m.logo), `links wrapped at ${width}px`).toBe(true);
        expect(m.header.height, `header too tall at ${width}px`).toBeLessThan(100);
      }
    });

    test('signed in, the header never collides and is one row on a wide screen', async ({ page, request }) => {
      await signInWithApi(page, request, 'apex_exotics');
      for (const width of [1180, 1280, 1440, 1600, 1920]) {
        await openAt(page, width);
        await expect(page.locator('.rightSection .headerLink').first()).toBeVisible();
        const m = await measureHeader(page);
        expectNoCollisions(m);
        expect(sameRow(m.nav, m.logo), `links wrapped at ${width}px`).toBe(true);
        if (width >= 1600) expect(sameRow(m.search, m.logo), `search bar wrapped at ${width}px`).toBe(true);
      }
    });

    test('on narrow screens the links move into the menu and nothing overflows', async ({ page }) => {
      for (const width of [375, 768, 1024]) {
        await openAt(page, width);
        const m = await measureHeader(page);
        expectNoCollisions(m);
        expect(m.nav, `links showing outside the menu at ${width}px`).toBeNull();
        expect(m.menuButton, `no menu button at ${width}px`).not.toBeNull();
        expect(sameRow(m.menuButton, m.logo), `menu button wrapped at ${width}px`).toBe(true);
        await page.locator('.headerMenuToggle').click();
        await expect(page.locator('#header-menu .headerLink').first()).toBeVisible();
      }
    });
  });
}
