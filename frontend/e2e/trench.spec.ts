import { expect, test } from '@playwright/test';

import { answerPost, enlist, loadAnswerKey, resetVolatileData } from './helpers';

test.describe('trench challenge', () => {
  test.beforeEach(async ({ request }) => {
    await resetVolatileData(request);
  });

  test('wrong then correct answer: scoring, feedback, auto-advance', async ({
    page,
    request,
  }) => {
    const key = await loadAnswerKey(request);
    const first = key.trench.questions[0]!;
    const wrongOption = first.wrong[0]!;
    const correctOption = first.correct!;

    const playerId = await enlist(page);
    await page.locator('.block-tab[data-target="desafio"]').click();

    await expect(page.locator('#trench-order')).toHaveText('ORDEM 1/7');
    await expect(page.locator('#trench-title')).toHaveText(first.title!);
    await expect(page.locator('.trench-option-btn')).toHaveCount(3);

    const wrong = await answerPost(page, () =>
      page.locator('.trench-option-btn', { hasText: wrongOption.label }).click()
    );
    // The browser says what was chosen and nothing about its worth...
    expect(wrong.request).toEqual({
      player_id: playerId,
      question_id: first.id,
      choice_id: wrongOption.id,
      prior_errors: 0,
    });
    // ...and the server answers with the verdict and the score.
    expect(wrong.status).toBe(201);
    expect(wrong.response).toMatchObject({
      player_id: playerId,
      is_correct: false,
      score_delta: -5,
      feedback: null,
    });
    await expect(page.locator('#trench-score')).toHaveText('-5');
    await expect(page.locator('#trench-feedback')).toHaveText(
      'Resposta incorreta. Reavalie os documentos e tente novamente.'
    );

    const correct = await answerPost(page, () =>
      page.locator('.trench-option-btn', { hasText: correctOption.label }).click()
    );
    expect(correct.request).toEqual({
      player_id: playerId,
      question_id: first.id,
      choice_id: correctOption.id,
      prior_errors: 1,
    });
    expect(correct.response).toMatchObject({
      is_correct: true,
      score_delta: 10,
      feedback: first.feedbackCorrect,
    });
    await expect(page.locator('#trench-score')).toHaveText('5');
    await expect(page.locator('#trench-feedback')).toHaveText(first.feedbackCorrect!);

    // 900 ms auto-advance — auto-waiting expect, no fixed sleeps.
    await expect(page.locator('#trench-order')).toHaveText('ORDEM 2/7');
    await expect(page.locator('.trench-step.is-complete')).toHaveCount(1);
  });

  test('error cap: the third wrong answer to a question costs nothing', async ({
    page,
    request,
  }) => {
    const key = await loadAnswerKey(request);
    const first = key.trench.questions[0]!;

    await enlist(page);
    await page.locator('.block-tab[data-target="desafio"]').click();

    const deltas: number[] = [];
    for (const option of [first.wrong[0]!, first.wrong[1]!, first.wrong[0]!]) {
      const post = await answerPost(page, () =>
        page.locator('.trench-option-btn', { hasText: option.label }).click()
      );
      deltas.push(post.response.score_delta);
    }
    expect(deltas).toEqual([-5, -5, 0]);
    await expect(page.locator('#trench-score')).toHaveText('-10');
  });

  test('full run to completion and reset', async ({ page, request }) => {
    const key = await loadAnswerKey(request);
    const questions = key.trench.questions;

    await enlist(page);
    await page.locator('.block-tab[data-target="desafio"]').click();

    for (const [index, question] of questions.entries()) {
      await expect(page.locator('#trench-order')).toHaveText(
        `ORDEM ${index + 1}/${questions.length}`
      );
      await answerPost(page, () =>
        page.locator('.trench-option-btn', { hasText: question.correct!.label }).click()
      );
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
