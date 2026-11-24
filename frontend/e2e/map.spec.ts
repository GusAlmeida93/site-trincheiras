import { expect, test } from '@playwright/test';

// 1x1 transparent PNG — CARTO tiles are stubbed for determinism/offline runs.
const ONE_PIXEL_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64'
);

test.describe('strategic map', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/basemaps.cartocdn.com/**', (route) =>
      route.fulfill({ contentType: 'image/png', body: ONE_PIXEL_PNG })
    );
  });

  test('initializes Leaflet with database regions', async ({ page }) => {
    const bundlePromise = page.waitForResponse('**/api/v1/lessons/*/bundle');
    await page.goto('/');
    expect((await bundlePromise).status()).toBe(200);

    await page.locator('.block-tab[data-target="mapa"]').click();

    await expect(page.locator('#strategic-map .leaflet-pane')).toHaveCount(7);
    // Europa: 5 features on the map and in the legend.
    await expect(page.locator('#strategic-map path.map-feature-layer')).toHaveCount(5);
    await expect(page.locator('.map-legend-item')).toHaveCount(5);
    await expect(page.locator('#map-region-note')).toContainText('Europa:');
  });

  test('legend click opens the feature popup', async ({ page }) => {
    await page.goto('/');
    await page.locator('.block-tab[data-target="mapa"]').click();
    await expect(page.locator('.map-legend-item')).toHaveCount(5);

    await page.locator('.map-legend-item', { hasText: 'Alsácia-Lorena' }).click();
    const popup = page.locator('.leaflet-popup .map-info-card');
    await expect(popup).toBeVisible();
    await expect(popup).toContainText('Devolvida à França.');
    await expect(popup).toContainText('Produz:');
  });

  test('region switch re-renders features, note, and active button', async ({ page }) => {
    await page.goto('/');
    await page.locator('.block-tab[data-target="mapa"]').click();
    await expect(page.locator('.map-legend-item')).toHaveCount(5);

    await page.locator('.map-region-btn[data-map-region="africa"]').click();
    await expect(page.locator('.map-legend-item')).toHaveCount(4);
    await expect(page.locator('#map-region-note')).toContainText('África:');
    await expect(page.locator('.map-region-btn[data-map-region="africa"]')).toHaveAttribute(
      'aria-selected',
      'true'
    );

    await page.locator('.map-region-btn[data-map-region="asia-pacific"]').click();
    await expect(page.locator('.map-legend-item')).toHaveCount(4);
    await expect(page.locator('#map-region-note')).toContainText('Ásia e Pacífico:');
  });
});
