import { expect, test, type Page } from '@playwright/test';

import { answerPost, enlist, loadAnswerKey, resetVolatileData } from './helpers';

function card(page: Page, docId: number) {
  return page.locator(`.war-intel-card[data-doc-id="${docId}"]`);
}

function drawer(page: Page, drawerId: number) {
  return page.locator(`.war-drawer[data-drawer-id="${drawerId}"]`);
}

test.describe('war room (click-to-place, all browsers)', () => {
  test.beforeEach(async ({ request }) => {
    await resetVolatileData(request);
  });

  test('correct and wrong placements are scored by the server', async ({ page, request }) => {
    const { war } = await loadAnswerKey(request);
    const doc1 = war.documents.get('doc-1')!;
    const doc2 = war.documents.get('doc-2')!;

    const playerId = await enlist(page);
    await page.locator('.block-tab[data-target="questoes"]').click();

    // Wrong: doc-1 into doc-2's drawer.
    await card(page, doc1.id).click();
    await expect(page.locator('#war-status')).toHaveText(
      'Documento selecionado. Clique em uma gaveta para arquivar.'
    );
    const wrong = await answerPost(page, () => drawer(page, doc2.drawerId).click());
    expect(wrong.request).toEqual({
      player_id: playerId,
      question_id: doc2.drawerId,
      choice_id: doc1.id,
      prior_errors: 0,
    });
    expect(wrong.status).toBe(201);
    expect(wrong.response).toMatchObject({ is_correct: false, score_delta: -5 });
    await expect(page.locator('#war-score')).toHaveText('-5');
    await expect(page.locator('#war-status')).toHaveText(
      'Documento incorreto para essa gaveta. Tente novamente.'
    );

    // The card stays selected after a wrong drop; drop it on the right drawer.
    const correct = await answerPost(page, () => drawer(page, doc1.drawerId).click());
    expect(correct.request).toEqual({
      player_id: playerId,
      question_id: doc1.drawerId,
      choice_id: doc1.id,
      prior_errors: 0,
    });
    expect(correct.response).toMatchObject({ is_correct: true, score_delta: 10 });
    await expect(page.locator('#war-score')).toHaveText('5');
    const filledDrawer = drawer(page, doc1.drawerId);
    await expect(filledDrawer).toHaveClass(/is-correct/);
    await expect(filledDrawer.locator('.war-drawer-answer')).toContainText(
      'Wilson defendia paz negociada'
    );
    await expect(card(page, doc1.id)).toHaveClass(/is-used/);
    await expect(page.locator('#war-status')).toHaveText(
      'Relatório arquivado com sucesso. 1/5 gavetas concluídas.'
    );
  });

  test('error cap: the third wrong attempt on a drawer costs nothing', async ({
    page,
    request,
  }) => {
    const { war } = await loadAnswerKey(request);
    const doc1 = war.documents.get('doc-1')!;
    const wrongDrawerId = war.documents.get('doc-2')!.drawerId;

    await enlist(page);
    await page.locator('.block-tab[data-target="questoes"]').click();

    const deltas: number[] = [];
    for (let attempt = 0; attempt < 3; attempt += 1) {
      if (attempt === 0) {
        await card(page, doc1.id).click(); // stays selected after wrong drops
      }
      const post = await answerPost(page, () => drawer(page, wrongDrawerId).click());
      deltas.push(post.response.score_delta);
    }
    expect(deltas).toEqual([-5, -5, 0]);
    await expect(page.locator('#war-score')).toHaveText('-10');
  });

  test('completing all five drawers shows the final status', async ({ page, request }) => {
    const { war } = await loadAnswerKey(request);

    await enlist(page);
    await page.locator('.block-tab[data-target="questoes"]').click();

    for (const { id, drawerId } of war.documents.values()) {
      await card(page, id).click();
      await answerPost(page, () => drawer(page, drawerId).click());
    }

    await expect(page.locator('#war-score')).toHaveText('50');
    await expect(page.locator('#war-status')).toHaveText(
      'Excelente. Todos os relatórios foram arquivados corretamente.'
    );
  });
});

test.describe('war room (native drag and drop)', () => {
  // The cabinet + board must fit on screen: with the default 720px viewport
  // the target drawer sits half-clipped and the synthetic drop can land on a
  // neighbouring drawer. (Verified: real browser drag works fine.)
  test.use({ viewport: { width: 1280, height: 1200 } });

  test.beforeEach(async ({ request }) => {
    await resetVolatileData(request);
  });

  // HTML5 drag simulation is only reliable in Chromium; the click-to-place
  // suite above carries the cross-browser coverage.
  test('drag a document into its drawer', async ({ page, request, browserName }) => {
    test.skip(browserName !== 'chromium', 'HTML5 DnD simulation is Chromium-only');

    const { war } = await loadAnswerKey(request);
    const doc1 = war.documents.get('doc-1')!;

    await enlist(page);
    await page.locator('.block-tab[data-target="questoes"]').click();

    await page.dragAndDrop(
      `.war-intel-card[data-doc-id="${doc1.id}"]`,
      `.war-drawer[data-drawer-id="${doc1.drawerId}"]`
    );

    await expect(page.locator('#war-score')).toHaveText('10');
    await expect(drawer(page, doc1.drawerId)).toHaveClass(/is-correct/);
  });
});
