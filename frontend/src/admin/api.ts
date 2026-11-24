import { BODY_HASH_HEADER, sha256Hex } from '../api/client';

// The server only honours a session cookie on a request that changes
// something when this header is present. Another site cannot add it without
// a CORS preflight, which the app never answers (see backend/app/security.py).
const CSRF_HEADER = 'X-Requested-With';
const CSRF_VALUE = 'trincheiras-admin';

/**
 * Sends a change to the API. Every one goes through here because a plain HTML
 * form cannot do two things the production stack needs: the CSRF header above
 * and the SHA-256 of the exact body, which CloudFront signs and Lambda checks
 * (see ../api/client.ts). A request without a body carries the hash of the
 * empty string, which is what its signature covers.
 */
export async function send(
  method: 'POST' | 'DELETE',
  path: string,
  body?: unknown,
): Promise<Response> {
  const text = body === undefined ? '' : JSON.stringify(body);
  const headers: Record<string, string> = { [CSRF_HEADER]: CSRF_VALUE };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const hash = await sha256Hex(text);
  if (hash) headers[BODY_HASH_HEADER] = hash;
  return fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : text,
    credentials: 'same-origin',
  });
}
