import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { expect, type APIRequestContext, type Page, type Response } from '@playwright/test';

// --- the public bundle: what students' browsers get (no answers) -----------

export interface BundleOption {
  id: number;
  label: string;
  position: number;
}

export interface BundleQuestion {
  id: number;
  slug: string;
  kind: string;
  position: number;
  title: string | null;
  prompt: string;
  options: BundleOption[];
}

export interface BundleDocument {
  id: number;
  body: string;
  position: number;
}

export interface BundleActivity {
  id: number;
  slug: string;
  kind: string;
  title: string;
  questions: BundleQuestion[];
  documents: BundleDocument[];
}

export interface Bundle {
  lesson: { slug: string; title: string };
  map_regions: Array<{ slug: string; name: string; note: string; features: unknown[] }>;
  activities: BundleActivity[];
}

// --- the answer key --------------------------------------------------------
//
// The right answers come from the seed fixtures the stack was seeded with,
// joined to the bundle's ids by the texts students see (option label,
// document body). The bundle itself must not be able to provide them.

interface FixtureActivity {
  slug: string;
  questions: Array<{
    slug: string;
    feedback_correct?: string | null;
    options?: Array<{ slug: string; label: string; is_correct: boolean }>;
  }>;
  documents?: Array<{ slug: string; body: string; correct_question_slug: string }>;
}

export interface KeyOption {
  id: number;
  slug: string;
  label: string;
  isCorrect: boolean;
}

export interface KeyQuestion {
  id: number;
  slug: string;
  title: string | null;
  feedbackCorrect: string | null;
  options: KeyOption[];
  correct: KeyOption | undefined;
  wrong: KeyOption[];
}

export interface KeyDocument {
  id: number;
  slug: string;
  /** Id of the drawer (question) this document belongs in. */
  drawerId: number;
}

export interface AnswerKey {
  trench: { questions: KeyQuestion[] };
  war: { drawerIds: number[]; documents: Map<string, KeyDocument> };
}

function loadFixtureActivities(): FixtureActivity[] {
  const path = fileURLToPath(
    new URL('../../backend/app/seed/fixtures/activities.json', import.meta.url)
  );
  return JSON.parse(readFileSync(path, 'utf-8')) as FixtureActivity[];
}

function required<T>(value: T | undefined, what: string): T {
  if (value === undefined) throw new Error(`answer key: ${what} not found`);
  return value;
}

export async function loadAnswerKey(request: APIRequestContext): Promise<AnswerKey> {
  const bundle = await fetchBundle(request);
  const fixtures = loadFixtureActivities();
  const activity = (slug: string) => ({
    fixture: required(
      fixtures.find((a) => a.slug === slug),
      `fixture ${slug}`
    ),
    bundle: required(
      bundle.activities.find((a) => a.slug === slug),
      `activity ${slug}`
    ),
  });

  const trench = activity('trench-mission');
  const questions = trench.fixture.questions.map((fixtureQuestion): KeyQuestion => {
    const question = required(
      trench.bundle.questions.find((q) => q.slug === fixtureQuestion.slug),
      `question ${fixtureQuestion.slug}`
    );
    const options = (fixtureQuestion.options ?? []).map((fixtureOption): KeyOption => {
      const option = required(
        question.options.find((o) => o.label === fixtureOption.label),
        `option ${fixtureOption.slug}`
      );
      return {
        id: option.id,
        slug: fixtureOption.slug,
        label: option.label,
        isCorrect: fixtureOption.is_correct,
      };
    });
    return {
      id: question.id,
      slug: question.slug,
      title: question.title,
      feedbackCorrect: fixtureQuestion.feedback_correct ?? null,
      options,
      correct: options.find((o) => o.isCorrect),
      wrong: options.filter((o) => !o.isCorrect),
    };
  });

  const war = activity('war-room');
  const drawerIdBySlug = new Map(war.bundle.questions.map((q) => [q.slug, q.id]));
  const documents = new Map<string, KeyDocument>();
  for (const fixtureDocument of war.fixture.documents ?? []) {
    const document = required(
      war.bundle.documents.find((d) => d.body === fixtureDocument.body),
      `document ${fixtureDocument.slug}`
    );
    documents.set(fixtureDocument.slug, {
      id: document.id,
      slug: fixtureDocument.slug,
      drawerId: required(
        drawerIdBySlug.get(fixtureDocument.correct_question_slug),
        `drawer ${fixtureDocument.correct_question_slug}`
      ),
    });
  }

  return {
    trench: { questions },
    war: { drawerIds: war.bundle.questions.map((q) => q.id), documents },
  };
}

// --- the answers API as the page uses it -----------------------------------

export interface AnswerRequestBody {
  player_id: number | null;
  question_id: number;
  choice_id: number;
  prior_errors: number;
  retry?: { elapsed_ms: number; after_answer_id: number | null } | null;
}

export interface AnswerResponseBody {
  id: number | null;
  player_id: number | null;
  question_id: number;
  choice_id: number;
  is_correct: boolean;
  score_delta: number;
  feedback: string | null;
}

export function isAnswerPost(response: Response): boolean {
  return response.url().includes('/api/v1/answers') && response.request().method() === 'POST';
}

/** Runs `action` (a click or drop) and returns the answer POST it causes. */
export async function answerPost(
  page: Page,
  action: () => Promise<unknown>
): Promise<{ status: number; request: AnswerRequestBody; response: AnswerResponseBody }> {
  const [response] = await Promise.all([page.waitForResponse(isAnswerPost), action()]);
  return {
    status: response.status(),
    request: response.request().postDataJSON() as AnswerRequestBody,
    response: (await response.json()) as AnswerResponseBody,
  };
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
