import type {
  AnswerCreate,
  AnswerResult,
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

async function jsonHeaders(body?: string): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (body !== undefined) {
    const hash = await sha256Hex(body);
    if (hash) headers[BODY_HASH_HEADER] = hash;
  }
  return headers;
}

// Fire-and-forget semantics: API failures log to the console and resolve to
// null so the classroom experience never blocks on the network.
async function apiFetch<T>(
  path: string,
  init?: { method: 'POST' | 'PUT'; body: string },
): Promise<T | null> {
  try {
    const headers = await jsonHeaders(init?.body);
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

/**
 * Answers are not fire-and-forget: only the server knows whether an answer is
 * right, so the caller must be able to tell a verdict from a failure.
 */
export type AnswerOutcome =
  | { status: 'judged'; result: AnswerResult }
  // The server refused the request itself (unknown question, choice or
  // player): sending it again cannot succeed.
  | { status: 'rejected'; httpStatus: number }
  // Network error, timeout or server error: nothing is known about the
  // attempt, and it can be sent again.
  | { status: 'failed' };

// A backstop only. In production CloudFront gives up on the origin after 60 s
// and answers 504 itself; this is slightly longer so that answer wins.
const ANSWER_TIMEOUT_MS = 65_000;
const REJECTED_STATUSES = new Set([404, 422]);

export async function submitAnswer(body: AnswerCreate): Promise<AnswerOutcome> {
  const payload = JSON.stringify(body);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ANSWER_TIMEOUT_MS);
  try {
    const response = await fetch('/api/v1/answers', {
      method: 'POST',
      body: payload,
      headers: await jsonHeaders(payload),
      signal: controller.signal,
    });
    if (response.ok) {
      return { status: 'judged', result: (await response.json()) as AnswerResult };
    }
    console.error(`API error (answers): HTTP ${response.status}`);
    if (REJECTED_STATUSES.has(response.status)) {
      return { status: 'rejected', httpStatus: response.status };
    }
    return { status: 'failed' };
  } catch (error) {
    console.error('API error (answers):', error);
    return { status: 'failed' };
  } finally {
    clearTimeout(timer);
  }
}
