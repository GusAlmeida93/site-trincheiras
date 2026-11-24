import { expect, test } from '@playwright/test';

import { enlist, fetchBundle, resetVolatileData } from './helpers';

test.describe('trench challenge', () => {
  test.beforeEach(async ({ request }) => {
    await resetVolatileData(request);
  });

  test('wrong then correct answer: scoring, feedback, auto-advance', async ({
    page,
    request,
  }) => {
    const trench = (await fetchBundle(request)).activities.find((a) => a.kind === 'quiz')!;
    const first = trench.questions[0]!;
    const wrongOption = first.options.find((o) => !o.is_correct)!;
    const correctOption = first.options.find((o) => o.is_correct)!;

    const playerId = await enlist(page);
    await page.locator('.block-tab[data-target="desafio"]').click();

    await expect(page.locator('#trench-order')).toHaveText('ORDEM 1/7');
    await expect(page.locator('#trench-title')).toHaveText(first.title!);
    await expect(page.locator('.trench-option-btn')).toHaveCount(3);

    const [wrongPost] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/api/v1/answers') && r.request().method() === 'POST'
      ),
      page.locator('.trench-option-btn', { hasText: wrongOption.label }).click(),
    ]);
    expect(wrongPost.request().postDataJSON()).toMatchObject({
      player_id: playerId,
      question_id: first.id,
      selected_value: wrongOption.slug,
      is_correct: false,
      score_delta: -5,
    });
    await expect(page.locator('#trench-score')).toHaveText('-5');
    await expect(page.locator('#trench-feedback')).toHaveText(
      'Resposta incorreta. Reavalie os documentos e tente novamente.'
    );

    const [correctPost] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/api/v1/answers') && r.request().method() === 'POST'
      ),
      page.locator('.trench-option-btn', { hasText: correctOption.label }).click(),
    ]);
    expect(correctPost.request().postDataJSON()).toMatchObject({
      player_id: playerId,
      question_id: first.id,
      selected_value: correctOption.slug,
      is_correct: true,
      score_delta: 10,
    });
    await expect(page.locator('#trench-score')).toHaveText('5');
    await expect(page.locator('#trench-feedback')).toHaveText(first.feedback_correct!);

    // 900 ms auto-advance — auto-waiting expect, no fixed sleeps.
    await expect(page.locator('#trench-order')).toHaveText('ORDEM 2/7');
    await expect(page.locator('.trench-step.is-complete')).toHaveCount(1);
  });

  test('full run to completion and reset', async ({ page, request }) => {
    const trench = (await fetchBundle(request)).activities.find((a) => a.kind === 'quiz')!;

    await enlist(page);
    await page.locator('.block-tab[data-target="desafio"]').click();

    for (const [index, question] of trench.questions.entries()) {
      await expect(page.locator('#trench-order')).toHaveText(
        `ORDEM ${index + 1}/${trench.questions.length}`
      );
      const correct = question.options.find((o) => o.is_correct)!;
      await Promise.all([
        page.waitForResponse(
          (r) => r.url().includes('/api/v1/answers') && r.request().method() === 'POST'
        ),
        page.locator('.trench-option-btn', { hasText: correct.label }).click(),
      ]);
    }

    await expect(page.locator('#trench-order')).toHaveText('MISSÃO CONCLUÍDA');
    await expect(page.locator('#trench-title')).toHaveText('Operação Encerrada');
    await expect(page.locator('#trench-question')).toContainText(
      'Sua pontuação final foi de 70 pontos.'
    );
    await expect(page.locator('#trench-score')).toHaveText('70');
    await expect(page.locator('.trench-step.is-complete')).toHaveCount(7);

    const reset = page.locator('#trench-reset');
    await expect(reset).toBeVisible();
    await reset.click();
    await expect(page.locator('#trench-order')).toHaveText('ORDEM 1/7');
    await expect(page.locator('#trench-score')).toHaveText('0');
  });
});
