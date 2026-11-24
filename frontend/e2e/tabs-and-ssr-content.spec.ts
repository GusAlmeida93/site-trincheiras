import { expect, test } from '@playwright/test';

test.describe('tabs and server-rendered content', () => {
  test('page shell, tabs, and initial panel', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle('O Tratado de Versalhes: Paz ou Pausa?');
    await expect(page.locator('h1')).toContainText('O Tratado de Versalhes');

    const tabs = page.getByRole('tab').and(page.locator('.block-tab'));
    await expect(tabs).toHaveCount(7);
    await expect(page.locator('#alistamento')).toBeVisible();
    await expect(page.locator('#contexto2')).toBeHidden();
  });

  test('tab switching flips aria-selected and panel visibility', async ({ page }) => {
    await page.goto('/');
    const contextTab = page.locator('.block-tab[data-target="contexto2"]');
    await contextTab.click();
    await expect(contextTab).toHaveAttribute('aria-selected', 'true');
    await expect(
      page.locator('.block-tab[data-target="alistamento"]')
    ).toHaveAttribute('aria-selected', 'false');
    await expect(page.locator('#contexto2')).toBeVisible();
    await expect(page.locator('#alistamento')).toBeHidden();
  });

  test('flip cards render from the database and toggle', async ({ page }) => {
    await page.goto('/');
    await page.locator('.block-tab[data-target="contexto2"]').click();

    const cards = page.locator('.intel-photo-card');
    await expect(cards).toHaveCount(4);
    const causes = page.locator('.intel-photo-card[data-intel="causas"]');
    await expect(causes).toHaveAttribute('aria-pressed', 'false');
    await causes.click();
    await expect(causes).toHaveAttribute('aria-pressed', 'true');
    await expect(causes.locator('.intel-back-text')).toContainText(
      'França e Reino Unido queriam punir a Alemanha'
    );
    await causes.click();
    await expect(causes).toHaveAttribute('aria-pressed', 'false');
  });

  test('participant reveal shows database content', async ({ page }) => {
    await page.goto('/');
    await page.locator('.block-tab[data-target="participantes"]').click();

    await expect(page.locator('.interest-result[data-participant="franca"]')).toBeHidden();
    await page.locator('.flag-card[data-participant="franca"]').click();

    const france = page.locator('.interest-result[data-participant="franca"]');
    await expect(france).toBeVisible();
    await expect(france.locator('.interest-leader')).toHaveText('Georges Clemenceau');
    await expect(france.locator('li')).toHaveCount(4);

    await page.locator('.flag-card[data-participant="alemanha"]').click();
    await expect(france).toBeHidden();
    await expect(
      page.locator('.interest-result[data-participant="alemanha"]')
    ).toContainText('A Nação Derrotada');
  });

  test('clause index swaps the visible document', async ({ page }) => {
    await page.goto('/');
    await page.locator('.block-tab[data-target="clausulas"]').click();

    await expect(page.locator('.clause-document[data-article="51"]')).toBeVisible();
    await page.locator('.clause-item[data-article="231"]').click();
    const doc231 = page.locator('.clause-document[data-article="231"]');
    await expect(doc231).toBeVisible();
    await expect(doc231.locator('.clause-document-title')).toHaveText('A Cláusula de Culpa');
    await expect(page.locator('.clause-document[data-article="51"]')).toBeHidden();
    await expect(page.locator('.clause-document:visible')).toHaveCount(1);
  });

  test('content is server-rendered (readable without JavaScript)', async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false });
    const page = await context.newPage();
    await page.goto('/');

    const html = await page.content();
    expect(html).toContain('Georges Clemenceau');
    expect(html).toContain('A Cláusula de Culpa');
    expect(html).toContain('GAVETA 05');
    expect(html).toContain('Trincheira 1: A Nova Fronteira');
    await context.close();
  });
});
