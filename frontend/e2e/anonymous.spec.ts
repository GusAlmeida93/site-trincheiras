import { expect, test } from '@playwright/test';

import { fetchBundle, resetVolatileData } from './helpers';

test.describe('anonymous play', () => {
  test.beforeEach(async ({ request }) => {
    await resetVolatileData(request);
  });

  test('games are fully playable without enlisting and post no answers', async ({
    page,
    request,
  }) => {
    const bundle = await fetchBundle(request);
    const war = bundle.activities.find((a) => a.kind === 'match')!;
    const trench = bundle.activities.find((a) => a.kind === 'quiz')!;
    const drawerIdBySlug = new Map(war.questions.map((q) => [q.slug, q.id]));
    const doc1 = war.documents.find((d) => d.slug === 'doc-1')!;
    const doc1DrawerId = drawerIdBySlug.get(doc1.correct_question_slug)!;

    const answerRequests: string[] = [];
    page.on('request', (r) => {
      if (r.url().includes('/api/v1/answers')) {
        answerRequests.push(r.method());
      }
    });

    await page.goto('/'); // no enlistment, no localStorage id

    // War room still plays and scores.
    await page.locator('.block-tab[data-target="questoes"]').click();
    await page.locator(`.war-intel-card[data-doc-id="${doc1.id}"]`).click();
    await page.locator(`.war-drawer[data-drawer-id="${doc1DrawerId}"]`).click();
    await expect(page.locator('#war-score')).toHaveText('10');

    // Trench still plays and scores.
    await page.locator('.block-tab[data-target="desafio"]').click();
    const correct = trench.questions[0]!.options.find((o) => o.is_correct)!;
    await page.locator('.trench-option-btn', { hasText: correct.label }).click();
    await expect(page.locator('#trench-score')).toHaveText('10');

    // Parity with the legacy site: nothing is recorded for anonymous players.
    expect(answerRequests).toEqual([]);

    const stored = await page.evaluate(() => localStorage.getItem('trincheiras_jogador_id'));
    expect(stored).toBeNull();
  });
});
