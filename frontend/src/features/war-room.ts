import type { ActivityRead } from '../api/types';
import { readScoringConfig } from '../api/types';
import { byId } from '../lib/dom';
import { postAnswerIfEnlisted } from '../state/player';
import { pulseHit, triggerBombExplosion } from './effects/explosion-visual';

export function initWarRoom(activity: ActivityRead): void {
  const drawers = document.querySelectorAll<HTMLElement>('.war-drawer');
  const cards = document.querySelectorAll<HTMLElement>('.war-intel-card');
  if (!drawers.length || !cards.length) return;

  const statusEl = byId('war-status');
  const scoreEl = byId('war-score');
  const grid = document.querySelector<HTMLElement>('.war-room-grid');

  const scoring = readScoringConfig(activity.config);
  const questionIdBySlug = new Map(activity.questions.map((q) => [q.slug, q.id]));
  // docId → its correct drawer id; the pairing never touches the DOM, so the
  // right answers are not readable from the markup.
  const correctDrawerByDoc = new Map<number, number>();
  const docSlugById = new Map<number, string>();
  for (const doc of activity.documents) {
    const drawerId = questionIdBySlug.get(doc.correct_question_slug);
    if (drawerId !== undefined) {
      correctDrawerByDoc.set(doc.id, drawerId);
    }
    docSlugById.set(doc.id, doc.slug);
  }

  let score = 0;
  let selectedCard: HTMLElement | null = null;
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

  const completeArchive = (docId: number, drawerId: number): void => {
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

    const isCorrect = correctDrawerByDoc.get(docId) === drawerId;
    const selectedValue = docSlugById.get(docId) ?? String(docId);
    const answerBox = drawer.querySelector<HTMLElement>('.war-drawer-answer');
    let pointsVariation = 0;

    if (!isCorrect) {
      const errors = drawerErrors.get(drawerId) ?? 0;
      if (errors < scoring.maxPenalizedErrors) {
        score += scoring.pointsWrong;
        pointsVariation = scoring.pointsWrong;
        updateScore();
      }
      drawerErrors.set(drawerId, errors + 1);

      drawer.classList.add('is-wrong');
      card.classList.add('is-selected');
      triggerBombExplosion(drawer);
      pulseHit(grid);
      setTimeout(() => drawer.classList.remove('is-wrong'), 420);
      updateStatus('Documento incorreto para essa gaveta. Tente novamente.');

      postAnswerIfEnlisted({
        question_id: drawerId,
        selected_value: selectedValue,
        is_correct: false,
        score_delta: pointsVariation,
      });
      return;
    }

    pointsVariation = scoring.pointsCorrect;
    drawer.dataset.filled = 'true';
    drawer.classList.add('is-correct');
    if (answerBox) {
      answerBox.textContent = getCardText(card);
    }
    score += pointsVariation;
    updateScore();
    finalizeCard(card);
    resetCardSelection();

    postAnswerIfEnlisted({
      question_id: drawerId,
      selected_value: selectedValue,
      is_correct: true,
      score_delta: pointsVariation,
    });

    const completed = document.querySelectorAll('.war-drawer[data-filled="true"]').length;
    const total = drawers.length;
    if (completed === total) {
      updateStatus('Excelente. Todos os relatórios foram arquivados corretamente.');
    } else {
      updateStatus(`Relatório arquivado com sucesso. ${completed}/${total} gavetas concluídas.`);
    }
  };

  const parseId = (value: string | undefined): number | null => {
    const id = Number.parseInt(value ?? '', 10);
    return Number.isFinite(id) ? id : null;
  };

  cards.forEach((card) => {
    card.addEventListener('click', () => {
      if (card.classList.contains('is-used')) return;

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
      if (card.classList.contains('is-used')) {
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
