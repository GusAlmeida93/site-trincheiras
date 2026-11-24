// What the two games share while an answer is with the server. A fast verdict
// (the usual case) shows none of this; the messages only appear when the
// request is slow, for instance while the database resumes from a pause.

export const ANSWER_MESSAGES = {
  checking: 'Conferindo sua resposta…',
  slow: 'O servidor está demorando para responder. Aguarde, sua resposta está sendo conferida.',
  failed: 'Não foi possível conferir sua resposta. Sua pontuação não mudou.',
  rejected: 'Esta atividade foi atualizada. Recarregue a página para continuar.',
  retry: 'Tentar novamente',
} as const;

const CHECKING_AFTER_MS = 400;
const SLOW_AFTER_MS = 5000;

/**
 * Calls `onChecking` once the wait becomes noticeable and `onSlow` when it
 * becomes long. Returns a function that cancels whatever has not fired yet.
 */
export function watchPending(onChecking: () => void, onSlow: () => void): () => void {
  const timers = [
    setTimeout(onChecking, CHECKING_AFTER_MS),
    setTimeout(onSlow, SLOW_AFTER_MS),
  ];
  return () => timers.forEach((timer) => clearTimeout(timer));
}

export function createRetryButton(onRetry: () => void): HTMLButtonElement {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'answer-retry';
  button.textContent = ANSWER_MESSAGES.retry;
  button.addEventListener('click', onRetry, { once: true });
  return button;
}
