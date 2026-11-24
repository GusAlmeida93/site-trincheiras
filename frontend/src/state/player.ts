import { submitAnswer } from '../api/client';
import type { AnswerCreate } from '../api/types';

// Kept from the legacy site so existing student sessions survive the rewrite.
const STORAGE_KEY = 'trincheiras_jogador_id';

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
  try {
    localStorage.setItem(STORAGE_KEY, String(id));
  } catch {
    // Non-fatal: the session just won't persist.
  }
}

/** Answers are only recorded for enlisted players (parity with the old site). */
export function postAnswerIfEnlisted(payload: Omit<AnswerCreate, 'player_id'>): void {
  const playerId = getPlayerId();
  if (playerId === null) return;
  void submitAnswer({ ...payload, player_id: playerId });
}
