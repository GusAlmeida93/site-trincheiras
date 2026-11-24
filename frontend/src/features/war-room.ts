import type { PublicActivity } from '../api/types';
import { byId } from '../lib/dom';
import { judgeAttempt, type Attempt } from '../state/player';
import { ANSWER_MESSAGES, createRetryButton, watchPending } from './answer-flow';
import { primeExplosionAudio } from './effects/explosion-audio';
import { pulseHit, triggerBombExplosion } from './effects/explosion-visual';

// The activity itself is server-rendered (drawers and cards carry their ids);
// the page holds no pairing, so every placement is judged by the server.
export function initWarRoom(_activity: PublicActivity): void {
  const drawers = document.querySelectorAll<HTMLElement>('.war-drawer');
  const cards = document.querySelectorAll<HTMLElement>('.war-intel-card');
  if (!drawers.length || !cards.length) return;

  const statusEl = byId('war-status');
  const scoreEl = byId('war-score');
  const grid = document.querySelector<HTMLElement>('.war-room-grid');

  let score = 0;
  let selectedCard: HTMLElement | null = null;
  // True from the placement until the server's verdict has been shown.
  let busy = false;
  // Wrong attempts per drawer on this page: the error cap for anonymous play.
  const drawerErrors = new Map<number, number>();

  const updateScore = (): void => {
    if (scoreEl) scoreEl.textContent = String(score);
  };

  const updateStatus = (message: string): void => {
    if (statusEl) statusEl.textContent = message;
  };

  const getCardText = (card: HTMLElement): string => {
    const body =
      card.querySelector('.war-intel-body') ?? card.querySelectorAll('p')[1];
    return body?.textContent?.trim() ?? '';
  };

  const finalizeCard = (card: HTMLElement): void => {
    card.classList.remove('is-selected');
    card.classList.add('is-used');
    card.setAttribute('aria-hidden', 'true');
    card.setAttribute('draggable', 'false');
  };

  const resetCardSelection = (): void => {
    cards.forEach((card) => card.classList.remove('is-selected'));
    selectedCard = null;
  };

  const submitAttempt = async (
    card: HTMLElement,
    drawer: HTMLElement,
    attempt: Attempt
  ): Promise<void> => {
    busy = true;
    // The card stays highlighted while its placement is being judged.
    selectedCard = card;
    card.classList.add('is-selected');
    const stopWatching = watchPending(
      () => {
        drawer.classList.add('is-pending');
        grid?.classList.add('is-waiting');
        updateStatus(ANSWER_MESSAGES.checking);
      },
      () => updateStatus(ANSWER_MESSAGES.slow)
    );
    const outcome = await judgeAttempt(attempt);
    stopWatching();
    drawer.classList.remove('is-pending');
    grid?.classList.remove('is-waiting');

    if (outcome.status !== 'judged') {
      // No verdict: the score stays as it is, and nothing else can be placed
      // until this one is settled, so the page never drifts from the server.
      if (outcome.status === 'rejected') {
        updateStatus(ANSWER_MESSAGES.rejected);
      } else {
        updateStatus(ANSWER_MESSAGES.failed);
        const retryButton = createRetryButton(() => {
          updateStatus('');
          void submitAttempt(card, drawer, attempt);
        });
        statusEl?.append(' ', retryButton);
      }
      // The status line sits under the board and may be off screen; unlike a
      // verdict, nothing else on the page shows that the placement is stuck.
      statusEl?.scrollIntoView({ block: 'nearest' });
      return;
    }

    busy = false;
    const { is_correct: isCorrect, score_delta: scoreDelta } = outcome.result;
    score += scoreDelta;
    updateScore();

    if (!isCorrect) {
      drawerErrors.set(attempt.questionId, (drawerErrors.get(attempt.questionId) ?? 0) + 1);

      drawer.classList.add('is-wrong');
      triggerBombExplosion(drawer);
      pulseHit(grid);
      setTimeout(() => drawer.classList.remove('is-wrong'), 420);
      updateStatus('Documento incorreto para essa gaveta. Tente novamente.');
      return;
    }

    const answerBox = drawer.querySelector<HTMLElement>('.war-drawer-answer');
    drawer.dataset.filled = 'true';
    drawer.classList.add('is-correct');
    if (answerBox) {
      answerBox.textContent = getCardText(card);
    }
    finalizeCard(card);
    resetCardSelection();

    const completed = document.querySelectorAll('.war-drawer[data-filled="true"]').length;
    const total = drawers.length;
    if (completed === total) {
      updateStatus('Excelente. Todos os relatórios foram arquivados corretamente.');
    } else {
      updateStatus(`Relatório arquivado com sucesso. ${completed}/${total} gavetas concluídas.`);
    }
  };

  const completeArchive = (docId: number, drawerId: number): void => {
    if (busy) return;
    const card = document.querySelector<HTMLElement>(
      `.war-intel-card[data-doc-id="${docId}"]`
    );
    const drawer = document.querySelector<HTMLElement>(
      `.war-drawer[data-drawer-id="${drawerId}"]`
    );
    if (!card || !drawer) return;
    if (card.classList.contains('is-used') || drawer.dataset.filled === 'true') {
      return;
    }

    // The verdict arrives after an await; the sound must be unlocked now,
    // while the click or drop still counts as a user gesture.
    primeExplosionAudio();
    void submitAttempt(card, drawer, {
      questionId: drawerId,
      choiceId: docId,
      priorErrors: drawerErrors.get(drawerId) ?? 0,
    });
  };

  const parseId = (value: string | undefined): number | null => {
    const id = Number.parseInt(value ?? '', 10);
    return Number.isFinite(id) ? id : null;
  };

  cards.forEach((card) => {
    card.addEventListener('click', () => {
      if (busy || card.classList.contains('is-used')) return;

      const wasSelected = card.classList.contains('is-selected');
      resetCardSelection();
      if (!wasSelected) {
        card.classList.add('is-selected');
        selectedCard = card;
        updateStatus('Documento selecionado. Clique em uma gaveta para arquivar.');
      } else {
        updateStatus('Selecione um documento para iniciar o arquivamento.');
      }
    });

    card.addEventListener('dragstart', (event) => {
      if (busy || card.classList.contains('is-used')) {
        event.preventDefault();
        return;
      }
      resetCardSelection();
      selectedCard = card;
      card.classList.add('is-selected');
      if (event.dataTransfer) {
        event.dataTransfer.setData('text/plain', card.dataset.docId ?? '');
        event.dataTransfer.effectAllowed = 'move';
      }
      updateStatus('Arraste o documento até a gaveta correspondente.');
    });

    card.addEventListener('dragend', () => {
      drawers.forEach((drawer) => drawer.classList.remove('is-hover'));
    });
  });

  drawers.forEach((drawer) => {
    drawer.addEventListener('click', () => {
      if (!selectedCard) return;
      const docId = parseId(selectedCard.dataset.docId);
      const drawerId = parseId(drawer.dataset.drawerId);
      if (docId === null || drawerId === null) return;
      completeArchive(docId, drawerId);
    });

    drawer.addEventListener('dragover', (event) => {
      event.preventDefault();
      drawer.classList.add('is-hover');
    });

    drawer.addEventListener('dragleave', () => {
      drawer.classList.remove('is-hover');
    });

    drawer.addEventListener('drop', (event) => {
      event.preventDefault();
      drawer.classList.remove('is-hover');
      const docId = parseId(event.dataTransfer?.getData('text/plain'));
      const drawerId = parseId(drawer.dataset.drawerId);
      if (docId === null || drawerId === null) return;
      completeArchive(docId, drawerId);
    });
  });
}
