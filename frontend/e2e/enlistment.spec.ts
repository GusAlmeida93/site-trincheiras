import { expect, test } from '@playwright/test';

import { resetVolatileData } from './helpers';

test.describe('enlistment', () => {
  test.beforeEach(async ({ request }) => {
    await resetVolatileData(request);
  });

  test('rejects a single-word name', async ({ page }) => {
    await page.goto('/');
    await page.locator('#enlist-name').fill('Ana');
    await page.locator('#enlist-class').fill('9º A');
    await page.locator('.enlist-submit').click();
    await expect(page.locator('#enlist-feedback')).toHaveText(
      'Informe o nome completo (nome e sobrenome).'
    );
  });

  test('requires an avatar', async ({ page }) => {
    await page.goto('/');
    await page.locator('#enlist-name').fill('Ana Carolina Souza');
    await page.locator('#enlist-class').fill('9º A');
    await page.locator('.enlist-submit').click();
    await expect(page.locator('#enlist-feedback')).toHaveText(
      'Selecione um avatar para concluir o alistamento.'
    );
  });

  test('happy path posts the player and issues the credential', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.enlist-avatar-option')).toHaveCount(20);

    await page.locator('#enlist-name').fill('  Maria   Clara  Santos ');
    await page.locator('#enlist-class').fill('9º B');
    await page.locator('.enlist-avatar-option[data-avatar-label="Enfermeira militar"]').click();

    const [response] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/api/v1/players') && r.request().method() === 'POST'
      ),
      page.locator('.enlist-submit').click(),
    ]);

    expect(response.status()).toBe(201);
    const posted = response.request().postDataJSON() as {
      name: string;
      class_group: string;
      recruit_number: string;
    };
    expect(posted.name).toBe('Maria Clara Santos'); // whitespace normalized
    expect(posted.class_group).toBe('9º B');
    expect(posted.recruit_number).toMatch(/^TRN-\d{6}-\d{4}$/);

    const created = (await response.json()) as { id: number };

    await expect(page.locator('#enlist-feedback')).toHaveText('Credencial emitida com sucesso.');
    const card = page.locator('#enlist-card');
    await expect(card).toBeVisible();
    await expect(card.locator('#enlist-card-name')).toHaveText('Maria Clara Santos');
    await expect(card.locator('#enlist-card-id')).toHaveText(posted.recruit_number);

    const heroBadge = page.locator('#hero-recruit');
    await expect(heroBadge).toBeVisible();
    await expect(heroBadge.locator('#hero-recruit-name')).toHaveText('Maria Clara Santos');

    const storedId = await page.evaluate(() =>
      localStorage.getItem('trincheiras_jogador_id')
    );
    expect(storedId).toBe(String(created.id));
  });
});
