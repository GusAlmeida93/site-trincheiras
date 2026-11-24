import { expect, test } from '@playwright/test';

import { answerPost, loadAnswerKey, resetVolatileData } from './helpers';

const ADMIN_TOKEN = process.env.E2E_ADMIN_TOKEN ?? 'e2e-admin-token';

test.describe('anonymous play', () => {
  test.beforeEach(async ({ request }) => {
    await resetVolatileData(request);
  });

  test('games are fully playable without enlisting, and nothing is recorded', async ({
    page,
    request,
  }) => {
    const key = await loadAnswerKey(request);
    const doc1 = key.war.documents.get('doc-1')!;
    const wrongDrawerId = key.war.documents.get('doc-2')!.drawerId;
    const firstQuestion = key.trench.questions[0]!;

    await page.goto('/'); // no enlistment, no localStorage id

    // War room: the server judges the placement for a visitor it does not know.
    await page.locator('.block-tab[data-target="questoes"]').click();
    await page.locator(`.war-intel-card[data-doc-id="${doc1.id}"]`).click();
    const placed = await answerPost(page, () =>
      page.locator(`.war-drawer[data-drawer-id="${doc1.drawerId}"]`).click()
    );
    expect(placed.request).toEqual({
      player_id: null,
      question_id: doc1.drawerId,
      choice_id: doc1.id,
      prior_errors: 0,
    });
    // 200 with no id: judged, not stored.
    expect(placed.status).toBe(200);
    expect(placed.response).toMatchObject({
      id: null,
      player_id: null,
      is_correct: true,
      score_delta: 10,
    });
    await expect(page.locator('#war-score')).toHaveText('10');

    // The error cap still applies: two penalized errors per drawer, then none.
    const doc3 = key.war.documents.get('doc-3')!;
    await page.locator(`.war-intel-card[data-doc-id="${doc3.id}"]`).click();
    const deltas: number[] = [];
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const post = await answerPost(page, () =>
        page.locator(`.war-drawer[data-drawer-id="${wrongDrawerId}"]`).click()
      );
      expect(post.request.prior_errors).toBe(attempt);
      deltas.push(post.response.score_delta);
    }
    expect(deltas).toEqual([-5, -5, 0]);
    await expect(page.locator('#war-score')).toHaveText('0');

    // Trench still plays and scores.
    await page.locator('.block-tab[data-target="desafio"]').click();
    const answered = await answerPost(page, () =>
      page.locator('.trench-option-btn', { hasText: firstQuestion.correct!.label }).click()
    );
    expect(answered.status).toBe(200);
    expect(answered.response).toMatchObject({ id: null, is_correct: true, score_delta: 10 });
    await expect(page.locator('#trench-score')).toHaveText('10');
    await expect(page.locator('#trench-feedback')).toHaveText(firstQuestion.feedbackCorrect!);

    const stored = await page.evaluate(() => localStorage.getItem('trincheiras_jogador_id'));
    expect(stored).toBeNull();

    // Parity with the legacy site: nothing is recorded for anonymous players.
    const report = await request.get('/api/v1/reports/answers', {
      headers: { 'X-Admin-Token': ADMIN_TOKEN },
    });
    expect(report.ok()).toBe(true);
    expect(((await report.json()) as { total: number }).total).toBe(0);
  });
});
