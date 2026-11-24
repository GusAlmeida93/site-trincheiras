import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';

import { expect, test, type APIRequestContext, type Page, type Request } from '@playwright/test';

import { resetVolatileData } from './helpers';

const EMAIL = 'prof@escola.test';
// Throwaway: the account lives in the tmpfs database of the e2e stack.
const PASSWORD = 'senha-de-teste-e2e-123';
const ADMIN_TOKEN = { 'X-Admin-Token': 'e2e-admin-token' };

interface SamplePlayers {
  ana: number;
  bruno: number;
  carla: number;
}

/** Ana and Bruno in 9º A, Carla in 9º B, with recorded answers. */
async function sampleResults(request: APIRequestContext): Promise<SamplePlayers> {
  const response = await request.post('/api/v1/test/sample-results');
  expect(response.status()).toBe(200);
  return ((await response.json()) as { players: SamplePlayers }).players;
}

/** What the invite-admin ops task hands out in production. */
async function inviteLink(request: APIRequestContext): Promise<string> {
  const response = await request.post('/api/v1/test/admin-invite', { data: { email: EMAIL } });
  expect(response.status()).toBe(200);
  return ((await response.json()) as { setup_path: string }).setup_path;
}

/**
 * CloudFront signs requests to the Lambda origin, and Lambda refuses one whose
 * body does not match the hash in that signature. Every change the admin area
 * makes must therefore carry the SHA-256 of its exact body, plus the custom
 * header the server demands before it honours a session cookie.
 */
function expectSignableChange(request: Request): void {
  const body = request.postDataBuffer() ?? Buffer.alloc(0);
  const headers = request.headers();
  expect(headers['x-amz-content-sha256']).toBe(createHash('sha256').update(body).digest('hex'));
  expect(headers['x-requested-with']).toBe('trincheiras-admin');
}

function apiRequest(page: Page, method: string, path: string): Promise<Request> {
  return page.waitForRequest((r) => r.method() === method && new URL(r.url()).pathname === path);
}

async function choosePassword(page: Page, link: string): Promise<void> {
  await page.goto(link);
  await page.locator('#new-password').fill(PASSWORD);
  await page.locator('#new-password-repeat').fill(PASSWORD);
  await page.getByRole('button', { name: 'Salvar senha' }).click();
  await expect(page).toHaveURL(/\/admin\/entrar$/);
}

async function signIn(page: Page, password = PASSWORD): Promise<void> {
  await page.goto('/admin/entrar');
  await page.locator('#sign-in-email').fill(EMAIL);
  await page.locator('#sign-in-password').fill(password);
  await page.getByRole('button', { name: 'Entrar' }).click();
}

/** An invited teacher, signed in through the real pages. */
async function signedInTeacher(page: Page, request: APIRequestContext): Promise<void> {
  await choosePassword(page, await inviteLink(request));
  await signIn(page);
  await expect(page).toHaveURL(/\/admin$/);
}

test.describe('teacher admin area', () => {
  let players: SamplePlayers;

  test.beforeEach(async ({ request }) => {
    await resetVolatileData(request);
    players = await sampleResults(request);
  });

  test('strangers are sent to the sign-in page', async ({ page }) => {
    for (const path of ['/admin', '/admin/turma?nome=9%C2%BA%20A', `/admin/alunos/${players.ana}`]) {
      await page.goto(path);
      await expect(page).toHaveURL(/\/admin\/entrar$/);
      await expect(page.getByRole('heading', { name: 'Entrar' })).toBeVisible();
    }
    await expect(page.locator('body')).not.toContainText('Ana Souza');
  });

  test('invite link, password, sign in, sign out', async ({ page, request, context }) => {
    const link = await inviteLink(request);
    expect(link).toMatch(/^\/admin\/definir-senha#.{40,}$/);

    // Choose a password from the link.
    await page.goto(link);
    await page.locator('#new-password').fill(PASSWORD);
    await page.locator('#new-password-repeat').fill(`${PASSWORD}-typo`);
    await page.getByRole('button', { name: 'Salvar senha' }).click();
    await expect(page.locator('#form-error')).toHaveText('As duas senhas não são iguais.');

    await page.locator('#new-password-repeat').fill(PASSWORD);
    const [passwordRequest] = await Promise.all([
      apiRequest(page, 'POST', '/api/v1/auth/password'),
      page.getByRole('button', { name: 'Salvar senha' }).click(),
    ]);
    expectSignableChange(passwordRequest);
    // The token went in the body; it never appears in a URL sent to the server.
    expect(passwordRequest.url()).not.toContain(link.split('#')[1]!);
    await expect(page).toHaveURL(/\/admin\/entrar$/);
    await expect(page.locator('#flash')).toHaveText(
      'Senha definida. Entre com seu e-mail e a nova senha.',
    );

    // A wrong password first.
    await page.locator('#sign-in-email').fill(EMAIL);
    await page.locator('#sign-in-password').fill('senha-errada-123');
    await page.getByRole('button', { name: 'Entrar' }).click();
    await expect(page.locator('#form-error')).toHaveText('E-mail ou senha incorretos.');
    await expect(page).toHaveURL(/\/admin\/entrar$/);

    // Then the right one.
    await page.locator('#sign-in-password').fill(PASSWORD);
    const [loginRequest] = await Promise.all([
      apiRequest(page, 'POST', '/api/v1/auth/login'),
      page.getByRole('button', { name: 'Entrar' }).click(),
    ]);
    expectSignableChange(loginRequest);
    await expect(page).toHaveURL(/\/admin$/);
    await expect(page.locator('.admin-user-email')).toHaveText(EMAIL);

    const cookie = (await context.cookies()).find((c) => c.name === 'trincheiras_admin');
    expect(cookie).toBeDefined();
    expect(cookie!.httpOnly).toBe(true);
    expect(cookie!.sameSite).toBe('Lax');
    // Scripts on the page cannot read it.
    expect(await page.evaluate(() => document.cookie)).not.toContain('trincheiras_admin');

    // The link worked once and is dead now.
    await page.goto(link);
    await page.locator('#new-password').fill(`${PASSWORD}-2`);
    await page.locator('#new-password-repeat').fill(`${PASSWORD}-2`);
    await page.getByRole('button', { name: 'Salvar senha' }).click();
    await expect(page.locator('#form-error')).toContainText('já foi usado ou expirou');

    // Sign out.
    await page.goto('/admin');
    const [logoutRequest] = await Promise.all([
      apiRequest(page, 'POST', '/api/v1/auth/logout'),
      page.getByRole('button', { name: 'Sair' }).click(),
    ]);
    expectSignableChange(logoutRequest);
    await expect(page).toHaveURL(/\/admin\/entrar$/);
    await page.goto('/admin');
    await expect(page).toHaveURL(/\/admin\/entrar$/);
  });

  test('a setup link without a token cannot be submitted', async ({ page }) => {
    await page.goto('/admin/definir-senha');
    await expect(page.locator('#form-error')).toContainText('Este link é inválido');
    await expect(page.getByRole('button', { name: 'Salvar senha' })).toBeDisabled();
  });

  test('results: classes, a class, a student, activities, CSV', async ({ page, request }) => {
    await signedInTeacher(page, request);

    // Classes.
    const classes = page.locator('#classes-table tbody tr');
    await expect(classes).toHaveCount(2);
    await expect(classes.nth(0)).toContainText('9º A');
    await expect(classes.nth(0).locator('td').nth(0)).toHaveText('2'); // students
    await expect(classes.nth(0).locator('td').nth(1)).toHaveText('4'); // answers

    // One class.
    await page.getByRole('link', { name: '9º A', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Turma 9º A' })).toBeVisible();
    const rows = page.locator('#players-table tbody tr');
    await expect(rows).toHaveCount(2);
    await expect(rows.nth(0)).toContainText('Ana Souza');
    await expect(rows.nth(0).locator('td').nth(3)).toHaveText('15'); // score
    await expect(rows.nth(1)).toContainText('Bruno Lima');

    // CSV export of the class.
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.locator('#export-csv').click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/^turma-.*\.csv$/);
    const csv = await readFile(await download.path(), 'utf8');
    expect(csv.charCodeAt(0)).toBe(0xfeff);
    const lines = csv.slice(1).trimEnd().split('\r\n');
    expect(lines).toHaveLength(3);
    expect(lines[0]).toMatch(/^Nome;Turma;Nº de recruta;Alistamento;Respostas;Acertos;/);
    expect(lines[1]).toMatch(/^Ana Souza;9º A;TRN-000001-0001;/);

    // One student.
    await page.getByRole('link', { name: 'Ana Souza' }).click();
    await expect(page).toHaveURL(new RegExp(`/admin/alunos/${players.ana}$`));
    await expect(page.locator('#player-score')).toHaveText('15');
    const answers = page.locator('#answers-table tbody tr');
    await expect(answers).toHaveCount(3);
    await expect(answers.nth(0)).toContainText('Trincheira 1: A Nova Fronteira');
    await expect(answers.nth(0)).toContainText('Errada');
    await expect(answers.nth(1)).toContainText('Certa');

    // Per-activity summary, then filtered by class.
    await page.getByRole('link', { name: 'Atividades' }).click();
    const trench = page.locator('[data-activity="trench-mission"]');
    await expect(trench).toContainText('2 aluno(s) · 4 resposta(s)');
    await page.locator('#filter-class').selectOption('9º B');
    await page.getByRole('button', { name: 'Filtrar' }).click();
    await expect(page).toHaveURL(/\/admin\/atividades\?turma=/);
    await expect(trench).toContainText('0 aluno(s) · 0 resposta(s)');
    await expect(page.locator('[data-activity="war-room"]')).toContainText('1 aluno(s) · 1 resposta(s)');
  });

  test('deleting a student asks first and removes their answers', async ({ page, request }) => {
    await signedInTeacher(page, request);
    await page.goto('/admin/turma?nome=9%C2%BA%20A');

    const bruno = page.locator(`tr[data-player-id="${players.bruno}"]`);
    const dialog = page.locator('#confirm-dialog');

    // Cancel changes nothing.
    await bruno.getByRole('button', { name: 'Apagar Bruno Lima' }).click();
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('Apagar Bruno Lima?');
    await expect(dialog).toContainText('Esta ação não pode ser desfeita.');
    await dialog.getByRole('button', { name: 'Cancelar' }).click();
    await expect(dialog).toBeHidden();
    await expect(bruno).toBeVisible();

    // Confirm deletes.
    await bruno.getByRole('button', { name: 'Apagar Bruno Lima' }).click();
    const [deleteRequest] = await Promise.all([
      apiRequest(page, 'DELETE', `/api/v1/admin/players/${players.bruno}`),
      dialog.getByRole('button', { name: 'Apagar', exact: true }).click(),
    ]);
    expectSignableChange(deleteRequest);
    expect((await deleteRequest.response())?.status()).toBe(200);

    await expect(page.locator('#flash')).toHaveText('Aluno apagado (1 resposta removida).');
    await expect(page.locator('#players-table tbody tr')).toHaveCount(1);
    await expect(page.locator('#players-table')).not.toContainText('Bruno Lima');

    // Gone on the server too, answers included; everyone else is untouched.
    const remaining = await request.get('/api/v1/reports/players', { headers: ADMIN_TOKEN });
    const summary = (await remaining.json()) as Array<{ name: string; answers_count: number }>;
    expect(summary.map((p) => p.name)).toEqual(['Ana Souza', 'Carla Dias']);
    expect(summary[0]!.answers_count).toBe(3);
    const answers = await request.get('/api/v1/reports/answers', { headers: ADMIN_TOKEN });
    expect(((await answers.json()) as { total: number }).total).toBe(4);
  });

  test('deleting a whole class', async ({ page, request }) => {
    await signedInTeacher(page, request);
    await page.goto('/admin/turma?nome=9%C2%BA%20A');

    await page.getByRole('button', { name: 'Apagar turma' }).click();
    const dialog = page.locator('#confirm-dialog');
    await expect(dialog).toContainText('Apagar a turma 9º A?');
    await expect(dialog).toContainText('Serão apagados 2 aluno(s) e 4 resposta(s) desta turma.');
    const [deleteRequest] = await Promise.all([
      apiRequest(page, 'DELETE', '/api/v1/admin/players'),
      dialog.getByRole('button', { name: 'Apagar', exact: true }).click(),
    ]);
    expectSignableChange(deleteRequest);

    await expect(page).toHaveURL(/\/admin$/);
    await expect(page.locator('#flash')).toHaveText(
      'Turma apagada: 2 alunos e 4 respostas removidas.',
    );
    await expect(page.locator('#classes-table tbody tr')).toHaveCount(1);
    await expect(page.locator('#classes-table')).toContainText('9º B');

    const remaining = await request.get('/api/v1/reports/players', { headers: ADMIN_TOKEN });
    expect(((await remaining.json()) as Array<{ name: string }>).map((p) => p.name)).toEqual([
      'Carla Dias',
    ]);
  });
});
