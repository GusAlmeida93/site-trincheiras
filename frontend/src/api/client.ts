import type {
  AnswerCreate,
  AnswerRead,
  LessonBundle,
  PlayerCreate,
  PlayerRead,
} from './types';

// In production CloudFront signs every request to the Lambda origin (SigV4),
// and Lambda rejects a POST/PUT whose body hash is missing from the signature.
// CloudFront cannot hash the body itself, so the browser sends it here.
export const BODY_HASH_HEADER = 'x-amz-content-sha256';

export async function sha256Hex(text: string): Promise<string | null> {
  // crypto.subtle only exists in secure contexts (https or localhost).
  if (!globalThis.crypto?.subtle) return null;
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

// Fire-and-forget semantics: API failures log to the console and resolve to
// null so the classroom experience never blocks on the network.
async function apiFetch<T>(
  path: string,
  init?: { method: 'POST' | 'PUT'; body: string },
): Promise<T | null> {
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (init) {
      const hash = await sha256Hex(init.body);
      if (hash) headers[BODY_HASH_HEADER] = hash;
    }
    const response = await fetch(`/api/v1/${path}`, { ...init, headers });
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
