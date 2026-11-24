import type { PublicActivity, PublicQuestion, PublicQuestionOption } from '../api/types';
import { byId } from '../lib/dom';
import { judgeAttempt, type Attempt } from '../state/player';
import { ANSWER_MESSAGES, createRetryButton, watchPending } from './answer-flow';
import { primeExplosionAudio } from './effects/explosion-audio';
import { pulseHit, triggerBombExplosion } from './effects/explosion-visual';

export function initTrench(activity: PublicActivity): void {
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

  const questions: PublicQuestion[] = activity.questions;

  let stepIndex = 0;
  // True from the click until the server's verdict has been shown.
  let locked = false;
  let score = 0;
  // Wrong attempts per question in this run: the error cap for anonymous play.
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

  const setOptionsDisabled = (disabled: boolean): void => {
    optionsEl.querySelectorAll('button').forEach((button) => {
      button.disabled = disabled;
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

  // The server decides whether the option is right and what it scores; the
  // page only shows the verdict it gets back.
  const submitAttempt = async (button: HTMLButtonElement, attempt: Attempt): Promise<void> => {
    locked = true;
    const stopWatching = watchPending(
      () => {
        button.classList.add('is-pending');
        optionsEl.classList.add('is-waiting');
        setFeedback(ANSWER_MESSAGES.checking, '');
      },
      () => setFeedback(ANSWER_MESSAGES.slow, '')
    );
    const outcome = await judgeAttempt(attempt);
    stopWatching();
    button.classList.remove('is-pending');
    optionsEl.classList.remove('is-waiting');

    if (outcome.status !== 'judged') {
      // No verdict: the score stays as it is, and no other answer can be sent
      // until this one is settled, so the page never drifts from the server.
      setOptionsDisabled(true);
      if (outcome.status === 'rejected') {
        setFeedback(ANSWER_MESSAGES.rejected, 'is-error');
        return;
      }
      setFeedback(ANSWER_MESSAGES.failed, 'is-error');
      const retryButton = createRetryButton(() => {
        setFeedback('', '');
        void submitAttempt(button, attempt);
      });
      feedbackEl?.append(' ', retryButton);
      retryButton.focus();
      return;
    }

    const { is_correct: isCorrect, score_delta: scoreDelta, feedback } = outcome.result;
    score += scoreDelta;
    updateScore();

    if (isCorrect) {
      setOptionsDisabled(true);
      button.classList.add('is-correct');
      setFeedback(feedback ?? '', 'is-success');
      setTimeout(advanceMission, 900);
      return;
    }

    errors.set(stepIndex, (errors.get(stepIndex) ?? 0) + 1);
    locked = false;
    if (button.disabled) {
      // Coming back from a failed request: the options were disabled.
      setOptionsDisabled(false);
      button.focus();
    }

    button.classList.add('is-wrong');
    triggerBombExplosion(button);
    pulseHit(trenchCard);
    setFeedback('Resposta incorreta. Reavalie os documentos e tente novamente.', 'is-error');

    setTimeout(() => {
      button.classList.remove('is-wrong');
    }, 420);
  };

  const handleOptionClick = (
    button: HTMLButtonElement,
    question: PublicQuestion,
    option: PublicQuestionOption
  ): void => {
    if (locked) return;
    // The verdict arrives after an await; the sound must be unlocked now,
    // while the click still counts as a user gesture.
    primeExplosionAudio();
    void submitAttempt(button, {
      questionId: question.id,
      choiceId: option.id,
      priorErrors: errors.get(stepIndex) ?? 0,
    });
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
