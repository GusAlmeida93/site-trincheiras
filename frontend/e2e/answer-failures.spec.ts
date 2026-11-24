import { expect, test, type Page, type Route } from '@playwright/test';

import {
  answerPost,
  enlist,
  loadAnswerKey,
  resetVolatileData,
  type AnswerRequestBody,
  type AnswerResponseBody,
} from './helpers';

const ANSWERS = '**/api/v1/answers';
const FAILED = 'Não foi possível conferir sua resposta. Sua pontuação não mudou.';

/** Lets `handler` deal with the next answer request only; later ones go through. */
async function interceptNextAnswer(
  page: Page,
  handler: (route: Route) => Promise<void>
): Promise<void> {
  await page.route(ANSWERS, handler, { times: 1 });
}

test.describe('answers when the server is slow or unreachable', () => {
  test.beforeEach(async ({ request }) => {
    await resetVolatileData(request);
  });

  test('trench: a failed request shows no verdict and can be retried', async ({
    page,
    request,
  }) => {
    const first = (await loadAnswerKey(request)).trench.questions[0]!;
    const options = page.locator('.trench-option-btn');
    const feedback = page.locator('#trench-feedback');
    const retry = feedback.locator('.answer-retry');

    await enlist(page);
    await page.locator('.block-tab[data-target="desafio"]').click();

    await interceptNextAnswer(page, (route) => route.abort('connectionfailed'));
    await options.filter({ hasText: first.correct!.label }).click();

    // No verdict either way, the score untouched, and a way forward.
    await expect(feedback).toContainText(FAILED);
    await expect(retry).toHaveText('Tentar novamente');
    await expect(page.locator('#trench-score')).toHaveText('0');
    await expect(options.filter({ hasText: first.correct!.label })).not.toHaveClass(
      /is-correct|is-wrong/
    );
    await expect(page.locator('#trench-order')).toHaveText('ORDEM 1/7');
    // No other answer can be sent while this one is unsettled.
    for (const option of await options.all()) {
      await expect(option).toBeDisabled();
    }

    const retried = await answerPost(page, () => retry.click());
    expect(retried.request).toMatchObject({
      question_id: first.id,
      choice_id: first.correct!.id,
      retry: { after_answer_id: null },
    });
    expect(retried.status).toBe(201);
    await expect(page.locator('#trench-score')).toHaveText('10');
    await expect(feedback).toHaveText(first.feedbackCorrect!);
    await expect(page.locator('#trench-order')).toHaveText('ORDEM 2/7');
  });

  test('trench: a retry of an answer the server did record is not counted twice', async ({
    page,
    request,
  }) => {
    const first = (await loadAnswerKey(request)).trench.questions[0]!;
    const wrongOption = page.locator('.trench-option-btn', { hasText: first.wrong[0]!.label });
    const feedback = page.locator('#trench-feedback');

    await enlist(page);
    await page.locator('.block-tab[data-target="desafio"]').click();

    // The request reaches the server and is recorded; only the response is lost.
    let recorded: AnswerResponseBody | undefined;
    await interceptNextAnswer(page, async (route) => {
      const response = await route.fetch();
      recorded = (await response.json()) as AnswerResponseBody;
      await route.abort('connectionreset');
    });
    await wrongOption.click();
    await expect(feedback).toContainText(FAILED);
    await expect(page.locator('#trench-score')).toHaveText('0');
    expect(recorded).toMatchObject({ is_correct: false, score_delta: -5 });

    const retried = await answerPost(page, () => feedback.locator('.answer-retry').click());
    // The server recognises the attempt: same answer, nothing new recorded.
    expect(retried.status).toBe(200);
    expect(retried.response).toEqual(recorded);
    await expect(page.locator('#trench-score')).toHaveText('-5');
    await expect(feedback).toHaveText(
      'Resposta incorreta. Reavalie os documentos e tente novamente.'
    );

    // The retry did not use up the error cap: this is only the second error.
    const second = await answerPost(page, () => wrongOption.click());
    expect(second.status).toBe(201);
    expect(second.response.score_delta).toBe(-5);
    const third = await answerPost(page, () => wrongOption.click());
    expect(third.response.score_delta).toBe(0);
    await expect(page.locator('#trench-score')).toHaveText('-10');
  });

  test('trench: a slow answer says it is being checked and blocks a second click', async ({
    page,
    request,
  }) => {
    const first = (await loadAnswerKey(request)).trench.questions[0]!;
    const options = page.locator('.trench-option-btn');
    const feedback = page.locator('#trench-feedback');

    await enlist(page);
    await page.locator('.block-tab[data-target="desafio"]').click();

    const sent: AnswerRequestBody[] = [];
    page.on('request', (r) => {
      if (r.url().includes('/api/v1/answers')) sent.push(r.postDataJSON() as AnswerRequestBody);
    });
    let release!: () => void;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    await interceptNextAnswer(page, async (route) => {
      await held;
      await route.continue();
    });

    await options.filter({ hasText: first.wrong[0]!.label }).click();
    await expect(feedback).toHaveText('Conferindo sua resposta…');
    await expect(page.locator('#trench-score')).toHaveText('0');

    // Clicking the right answer meanwhile does nothing.
    await options.filter({ hasText: first.correct!.label }).click();
    await expect(feedback).toHaveText('Conferindo sua resposta…');

    release();
    await expect(feedback).toHaveText(
      'Resposta incorreta. Reavalie os documentos e tente novamente.'
    );
    await expect(page.locator('#trench-score')).toHaveText('-5');
    expect(sent.map((body) => body.choice_id)).toEqual([first.wrong[0]!.id]);
  });

  test('trench: a request the server refuses asks for a reload instead of a retry', async ({
    page,
    request,
  }) => {
    const first = (await loadAnswerKey(request)).trench.questions[0]!;
    const feedback = page.locator('#trench-feedback');

    await page.goto('/');
    await page.locator('.block-tab[data-target="desafio"]').click();

    await interceptNextAnswer(page, (route) =>
      route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'The choice does not belong to this question.' }),
      })
    );
    await page.locator('.trench-option-btn', { hasText: first.correct!.label }).click();

    await expect(feedback).toHaveText(
      'Esta atividade foi atualizada. Recarregue a página para continuar.'
    );
    await expect(feedback.locator('.answer-retry')).toHaveCount(0);
    await expect(page.locator('#trench-score')).toHaveText('0');
  });

  test('war room: a server error keeps the card in hand until the retry', async ({
    page,
    request,
  }) => {
    const doc1 = (await loadAnswerKey(request)).war.documents.get('doc-1')!;
    const card = page.locator(`.war-intel-card[data-doc-id="${doc1.id}"]`);
    const drawer = page.locator(`.war-drawer[data-drawer-id="${doc1.drawerId}"]`);
    const status = page.locator('#war-status');

    await enlist(page);
    await page.locator('.block-tab[data-target="questoes"]').click();

    await interceptNextAnswer(page, (route) => route.fulfill({ status: 503, body: 'busy' }));
    await card.click();
    await drawer.click();

    await expect(status).toContainText(FAILED);
    await expect(page.locator('#war-score')).toHaveText('0');
    await expect(drawer).not.toHaveClass(/is-correct|is-wrong/);
    await expect(card).toHaveClass(/is-selected/);
    await expect(card).not.toHaveClass(/is-used/);

    const retried = await answerPost(page, () => status.locator('.answer-retry').click());
    expect(retried.status).toBe(201);
    expect(retried.response).toMatchObject({ is_correct: true, score_delta: 10 });
    await expect(page.locator('#war-score')).toHaveText('10');
    await expect(drawer).toHaveClass(/is-correct/);
    await expect(card).toHaveClass(/is-used/);
    await expect(status).toHaveText('Relatório arquivado com sucesso. 1/5 gavetas concluídas.');
  });

  test('a stored player the server no longer knows plays on as a visitor', async ({
    page,
    request,
  }) => {
    const first = (await loadAnswerKey(request)).trench.questions[0]!;

    await page.goto('/');
    await page.evaluate(() => localStorage.setItem('trincheiras_jogador_id', '987654'));
    await page.reload();
    await page.locator('.block-tab[data-target="desafio"]').click();

    const statuses: number[] = [];
    page.on('response', (r) => {
      if (r.url().includes('/api/v1/answers')) statuses.push(r.status());
    });
    await page.locator('.trench-option-btn', { hasText: first.correct!.label }).click();

    await expect(page.locator('#trench-score')).toHaveText('10');
    await expect(page.locator('#trench-feedback')).toHaveText(first.feedbackCorrect!);
    expect(statuses).toEqual([404, 200]);
    expect(await page.evaluate(() => localStorage.getItem('trincheiras_jogador_id'))).toBeNull();
  });
});
