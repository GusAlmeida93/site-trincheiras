import type {
  AnswerCreate,
  AnswerRead,
  LessonBundle,
  PlayerCreate,
  PlayerRead,
} from './types';

// Fire-and-forget semantics: API failures log to the console and resolve to
// null so the classroom experience never blocks on the network.
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const response = await fetch(`/api/v1/${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return (await response.json()) as T;
  } catch (error) {
    console.error(`API error (${path}):`, error);
    return null;
  }
}

export function getLessonBundle(slug: string): Promise<LessonBundle | null> {
  return apiFetch<LessonBundle>(`lessons/${encodeURIComponent(slug)}/bundle`);
}

export function createPlayer(body: PlayerCreate): Promise<PlayerRead | null> {
  return apiFetch<PlayerRead>('players', { method: 'POST', body: JSON.stringify(body) });
}

export function submitAnswer(body: AnswerCreate): Promise<AnswerRead | null> {
  return apiFetch<AnswerRead>('answers', { method: 'POST', body: JSON.stringify(body) });
}
