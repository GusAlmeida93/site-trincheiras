import { submitAnswer, type AnswerOutcome } from '../api/client';
import type { AnswerCreate } from '../api/types';

// Kept from the legacy site so existing student sessions survive the rewrite.
const STORAGE_KEY = 'trincheiras_jogador_id';

// Last answer id the server returned to this page for the current player.
// Sent with retries so an older identical answer is never taken for the one
// whose response was lost.
let lastAnswerId: number | null = null;

export function getPlayerId(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const id = Number.parseInt(raw, 10);
    return Number.isFinite(id) && id > 0 ? id : null;
  } catch {
    return null; // Safari private mode throws on access.
  }
}

export function setPlayerId(id: number): void {
  lastAnswerId = null;
  try {
    localStorage.setItem(STORAGE_KEY, String(id));
  } catch {
    // Non-fatal: the session just won't persist.
  }
}

function clearPlayerId(): void {
  lastAnswerId = null;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing stored, nothing to clear.
  }
}

export interface Attempt {
  questionId: number;
  /** Id of the chosen option (quiz) or document (war room). */
  choiceId: number;
  /**
   * Wrong attempts already made at this question on this page. The server
   * uses it for the error cap in anonymous play only; for enlisted players it
   * counts the recorded answers itself.
   */
  priorErrors: number;
  /** Set on the first send; a later send of the same object is a retry. */
  firstSentAt?: number;
}

/**
 * Asks the server to judge an attempt. Enlisted players' answers are recorded;
 * anonymous ones are judged with the same rules and not stored. Pass the same
 * `attempt` object again to retry after a failure.
 */
export async function judgeAttempt(attempt: Attempt): Promise<AnswerOutcome> {
  const playerId = getPlayerId();
  const body: AnswerCreate = {
    player_id: playerId,
    question_id: attempt.questionId,
    choice_id: attempt.choiceId,
    prior_errors: attempt.priorErrors,
  };
  if (attempt.firstSentAt === undefined) {
    attempt.firstSentAt = performance.now();
  } else {
    body.retry = {
      elapsed_ms: Math.round(performance.now() - attempt.firstSentAt),
      after_answer_id: lastAnswerId,
    };
  }

  const outcome = await submitAnswer(body);
  if (outcome.status === 'judged') {
    if (outcome.result.id != null) lastAnswerId = outcome.result.id;
    return outcome;
  }
  if (outcome.status === 'rejected' && outcome.httpStatus === 404 && playerId !== null) {
    // 404 means the question or the player is gone. If the anonymous request
    // goes through, it was the player (removed by the teacher): forget the
    // stored id so the game keeps working, unrecorded, as for any visitor.
    const anonymous = await submitAnswer({ ...body, player_id: null, retry: null });
    if (anonymous.status === 'judged') {
      console.warn('Stored player no longer exists; continuing without recording answers.');
      clearPlayerId();
    }
    return anonymous;
  }
  return outcome;
}
