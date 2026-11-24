import { expect, type APIRequestContext, type Page } from '@playwright/test';

export interface BundleOption {
  id: number;
  slug: string;
  label: string;
  is_correct: boolean;
  position: number;
}

export interface BundleQuestion {
  id: number;
  slug: string;
  kind: string;
  position: number;
  title: string | null;
  prompt: string;
  feedback_correct: string | null;
  options: BundleOption[];
}

export interface BundleDocument {
  id: number;
  slug: string;
  body: string;
  position: number;
  correct_question_slug: string;
}

export interface BundleActivity {
  id: number;
  slug: string;
  kind: string;
  title: string;
  config: Record<string, number>;
  questions: BundleQuestion[];
  documents: BundleDocument[];
}

export interface Bundle {
  lesson: { slug: string; title: string };
  map_regions: Array<{ slug: string; name: string; note: string; features: unknown[] }>;
  activities: BundleActivity[];
}

export async function resetVolatileData(request: APIRequestContext): Promise<void> {
  const response = await request.post('/api/v1/test/reset');
  expect(response.status(), 'test reset endpoint must be enabled (APP_ENV=test)').toBe(200);
}

export async function fetchBundle(request: APIRequestContext): Promise<Bundle> {
  const response = await request.get('/api/v1/lessons/tratado-de-versalhes/bundle');
  expect(response.ok()).toBe(true);
  return (await response.json()) as Bundle;
}

/** Fills the enlistment form, picks an avatar, submits, waits for the POST. */
export async function enlist(
  page: Page,
  name = 'Ana Carolina Souza',
  classGroup = '9º A'
): Promise<number> {
  await page.goto('/');
  await page.locator('#enlist-name').fill(name);
  await page.locator('#enlist-class').fill(classGroup);
  await page.locator('.enlist-avatar-option').first().click();

  const [response] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes('/api/v1/players') && r.request().method() === 'POST'
    ),
    page.locator('.enlist-submit').click(),
  ]);
  expect(response.status()).toBe(201);
  const body = (await response.json()) as { id: number };
  return body.id;
}
