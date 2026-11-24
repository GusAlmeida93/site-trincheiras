import type { ActivityRead, QuestionOptionRead, QuestionRead } from '../api/types';
import { readScoringConfig } from '../api/types';
import { byId } from '../lib/dom';
import { postAnswerIfEnlisted } from '../state/player';
import { pulseHit, triggerBombExplosion } from './effects/explosion-visual';

export function initTrench(activity: ActivityRead): void {
  const orderEl = byId('trench-order');
  const titleEl = byId('trench-title');
  const questionEl = byId('trench-question');
  const optionsEl = byId('trench-options');
  if (!orderEl || !titleEl || !questionEl || !optionsEl) return;

  const feedbackEl = byId('trench-feedback');
  const resetButton = byId<HTMLButtonElement>('trench-reset');
  const scoreEl = byId('trench-score');
  const progressFill = byId('trench-progress-fill');
  const steps = document.querySelectorAll<HTMLElement>('.trench-step');
  const trenchCard = document.querySelector<HTMLElement>('.trench-card');

  const questions: QuestionRead[] = activity.questions;
  const scoring = readScoringConfig(activity.config);

  let stepIndex = 0;
  let locked = false;
  let score = 0;
  let errors = new Map<number, number>();

  const updateScore = (): void => {
    if (scoreEl) scoreEl.textContent = String(score);
  };

  const setFeedback = (message: string, status: '' | 'is-error' | 'is-success'): void => {
    if (!feedbackEl) return;
    feedbackEl.textContent = message;
    feedbackEl.classList.remove('is-error', 'is-success');
    if (status) {
      feedbackEl.classList.add(status);
    }
  };

  const updateProgress = (): void => {
    if (!steps.length) return;

    const total = questions.length;
    const progressIndex = Math.min(stepIndex, total - 1);
    const percentage =
      stepIndex >= total ? 100 : total <= 1 ? 100 : (progressIndex / (total - 1)) * 100;

    if (progressFill) {
      progressFill.style.width = `${percentage}%`;
    }

    steps.forEach((step, index) => {
      step.classList.toggle('is-complete', index < stepIndex);
      step.classList.toggle('is-active', stepIndex < total && index === stepIndex);
    });
  };

  const disableOptionButtons = (): void => {
    optionsEl.querySelectorAll('button').forEach((button) => {
      button.disabled = true;
    });
  };

  const renderCompletion = (): void => {
    orderEl.textContent = 'MISSÃO CONCLUÍDA';
    titleEl.textContent = 'Operação Encerrada';
    questionEl.textContent =
      'Você sobreviveu ao campo de batalha diplomático e concluiu todas as trincheiras! ' +
      `Sua pontuação final foi de ${score} pontos.`;

    optionsEl.innerHTML = '';

    if (resetButton) {
      resetButton.hidden = false;
    }
    setFeedback('Missão concluída com sucesso.', 'is-success');
    updateProgress();
  };

  const advanceMission = (): void => {
    stepIndex += 1;
    locked = false;
    if (stepIndex >= questions.length) {
      renderCompletion();
      return;
    }
    renderQuestion();
  };

  const handleOptionClick = (
    button: HTMLButtonElement,
    question: QuestionRead,
    option: QuestionOptionRead
  ): void => {
    if (locked) return;

    let pointsVariation = 0;

    if (option.is_correct) {
      locked = true;
      disableOptionButtons();
      pointsVariation = scoring.pointsCorrect;
      score += pointsVariation;
      updateScore();
      button.classList.add('is-correct');
      setFeedback(question.feedback_correct ?? '', 'is-success');

      postAnswerIfEnlisted({
        question_id: question.id,
        selected_value: option.slug,
        is_correct: true,
        score_delta: pointsVariation,
      });

      setTimeout(advanceMission, 900);
      return;
    }

    const errorCount = errors.get(stepIndex) ?? 0;
    if (errorCount < scoring.maxPenalizedErrors) {
      pointsVariation = scoring.pointsWrong;
      score += pointsVariation;
      updateScore();
    }
    errors.set(stepIndex, errorCount + 1);

    button.classList.add('is-wrong');
    triggerBombExplosion(button);
    pulseHit(trenchCard);
    setFeedback('Resposta incorreta. Reavalie os documentos e tente novamente.', 'is-error');

    postAnswerIfEnlisted({
      question_id: question.id,
      selected_value: option.slug,
      is_correct: false,
      score_delta: pointsVariation,
    });

    setTimeout(() => {
      button.classList.remove('is-wrong');
    }, 420);
  };

  function renderQuestion(): void {
    const question = questions[stepIndex];
    if (!question) {
      renderCompletion();
      return;
    }

    orderEl!.textContent = `ORDEM ${stepIndex + 1}/${questions.length}`;
    titleEl!.textContent = question.title ?? '';
    questionEl!.textContent = question.prompt;
    optionsEl!.innerHTML = '';

    for (const option of question.options) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'trench-option-btn';
      button.textContent = option.label;
      button.addEventListener('click', () => {
        handleOptionClick(button, question, option);
      });
      optionsEl!.appendChild(button);
    }

    if (resetButton) {
      resetButton.hidden = true;
    }

    setFeedback('', '');
    updateProgress();
  }

  const resetMission = (): void => {
    stepIndex = 0;
    locked = false;
    score = 0;
    errors = new Map();
    updateScore();
    renderQuestion();
  };

  resetButton?.addEventListener('click', resetMission);

  resetMission();
}
