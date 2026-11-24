import './admin.css';

import { byId } from '../lib/dom';
import { send } from './api';

const SIGN_IN_PATH = '/admin/entrar';
const HOME_PATH = '/admin';
const FLASH_KEY = 'trincheiras_admin_flash';
const OFFLINE = 'Não foi possível falar com o servidor. Verifique a conexão e tente de novo.';

/** A message for the next page, e.g. "Aluno apagado" after the redirect. */
function setFlash(message: string): void {
  try {
    sessionStorage.setItem(FLASH_KEY, message);
  } catch {
    // Storage blocked: the action still happened, only the notice is lost.
  }
}

function showFlash(): void {
  const region = byId('flash');
  if (!region) return;
  try {
    const message = sessionStorage.getItem(FLASH_KEY);
    if (!message) return;
    sessionStorage.removeItem(FLASH_KEY);
    region.textContent = message;
    region.hidden = false;
  } catch {
    // Nothing to show.
  }
}

function showError(region: HTMLElement | null, message: string): void {
  if (!region) return;
  region.textContent = message;
  region.hidden = false;
}

/** Runs `work` with the button disabled and relabelled; restores it if we stay on the page. */
async function busy(button: HTMLButtonElement, label: string, work: () => Promise<boolean>): Promise<void> {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = label;
  let leaving = false;
  try {
    leaving = await work();
  } finally {
    if (!leaving) {
      button.disabled = false;
      button.textContent = original;
    }
  }
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

function initSignIn(): void {
  const form = byId<HTMLFormElement>('sign-in-form');
  if (!form) return;
  const email = byId<HTMLInputElement>('sign-in-email');
  const password = byId<HTMLInputElement>('sign-in-password');
  const submit = form.querySelector<HTMLButtonElement>('button[type="submit"]');
  const error = byId('form-error');
  if (!email || !password || !submit) return;
  submit.disabled = false;

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (error) error.hidden = true;
    // After an idle spell the database takes a while to wake up.
    void busy(submit, 'Entrando… (pode levar até 30 s)', async () => {
      let response: Response;
      try {
        response = await send('POST', '/api/v1/auth/login', {
          email: email.value,
          password: password.value,
        });
      } catch {
        showError(error, OFFLINE);
        return false;
      }
      if (response.ok) {
        location.assign(HOME_PATH);
        return true;
      }
      if (response.status === 401 || response.status === 422) {
        showError(error, 'E-mail ou senha incorretos.');
        password.value = '';
        password.focus();
      } else if (response.status === 429) {
        const seconds = Number.parseInt(response.headers.get('Retry-After') ?? '', 10);
        const minutes = Number.isFinite(seconds) ? Math.max(1, Math.ceil(seconds / 60)) : 15;
        showError(
          error,
          `Muitas tentativas sem sucesso. Tente de novo em ${plural(minutes, 'minuto', 'minutos')}.`,
        );
      } else {
        showError(error, 'Não foi possível entrar agora. Tente de novo em instantes.');
      }
      return false;
    });
  });
}

function initSetPassword(): void {
  const form = byId<HTMLFormElement>('set-password-form');
  if (!form) return;
  const password = byId<HTMLInputElement>('new-password');
  const repeat = byId<HTMLInputElement>('new-password-repeat');
  const submit = form.querySelector<HTMLButtonElement>('button[type="submit"]');
  const error = byId('form-error');
  if (!password || !repeat || !submit) return;

  const invalidLink = 'Este link é inválido, já foi usado ou expirou. Peça um novo link de acesso.';
  // The token travels after "#", which the browser never sends to the server.
  const token = location.hash.slice(1);
  if (!token) {
    showError(error, invalidLink);
    return; // the button stays disabled
  }
  submit.disabled = false;

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (error) error.hidden = true;
    if (password.value !== repeat.value) {
      showError(error, 'As duas senhas não são iguais.');
      repeat.focus();
      return;
    }
    void busy(submit, 'Salvando…', async () => {
      let response: Response;
      try {
        response = await send('POST', '/api/v1/auth/password', {
          token,
          password: password.value,
        });
      } catch {
        showError(error, OFFLINE);
        return false;
      }
      if (response.ok) {
        setFlash('Senha definida. Entre com seu e-mail e a nova senha.');
        location.assign(SIGN_IN_PATH);
        return true;
      }
      if (response.status === 400) {
        showError(error, invalidLink);
      } else if (response.status === 422) {
        showError(error, `A senha precisa ter pelo menos ${password.minLength} caracteres.`);
      } else {
        showError(error, 'Não foi possível salvar a senha agora. Tente de novo em instantes.');
      }
      return false;
    });
  });
}

function initSignOut(): void {
  const button = byId<HTMLButtonElement>('sign-out');
  if (!button) return;
  button.addEventListener('click', () => {
    void busy(button, 'Saindo…', async () => {
      try {
        await send('POST', '/api/v1/auth/logout', {});
      } catch {
        return false;
      }
      location.assign(SIGN_IN_PATH);
      return true;
    });
  });
}

interface DeletionResult {
  players_deleted: number;
  answers_deleted: number;
}

function deletedMessage(kind: string | undefined, result: DeletionResult): string {
  const answers = plural(result.answers_deleted, 'resposta removida', 'respostas removidas');
  if (kind === 'class') {
    const players = plural(result.players_deleted, 'aluno', 'alunos');
    return `Turma apagada: ${players} e ${answers}.`;
  }
  return `Aluno apagado (${answers}).`;
}

/** Any button with data-delete-url asks for confirmation in the shared dialog first. */
function initDeletes(): void {
  const dialog = byId<HTMLDialogElement>('confirm-dialog');
  const title = byId('confirm-title');
  const text = byId('confirm-text');
  const error = byId('confirm-error');
  const cancel = byId<HTMLButtonElement>('confirm-cancel');
  const accept = byId<HTMLButtonElement>('confirm-accept');
  if (!dialog || !title || !text || !cancel || !accept) return;

  let pending: HTMLElement | null = null;

  document.querySelectorAll<HTMLElement>('[data-delete-url]').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      pending = trigger;
      title.textContent = trigger.dataset.confirmTitle ?? 'Apagar?';
      text.textContent = trigger.dataset.confirmText ?? '';
      if (error) error.hidden = true;
      dialog.showModal();
      cancel.focus(); // the safe choice is the default
    });
  });

  cancel.addEventListener('click', () => dialog.close());

  accept.addEventListener('click', () => {
    const trigger = pending;
    const url = trigger?.dataset.deleteUrl;
    if (!trigger || !url) return;
    void busy(accept, 'Apagando…', async () => {
      let response: Response;
      try {
        response = await send('DELETE', url);
      } catch {
        showError(error, OFFLINE);
        return false;
      }
      if (response.status === 401) {
        location.assign(SIGN_IN_PATH); // the session ended meanwhile
        return true;
      }
      if (!response.ok && response.status !== 404) {
        showError(error, 'Não foi possível apagar agora. Tente de novo em instantes.');
        return false;
      }
      if (response.ok) {
        setFlash(deletedMessage(trigger.dataset.deleteKind, (await response.json()) as DeletionResult));
      }
      // 404 means someone else already deleted it: the list is stale either way.
      location.assign(trigger.dataset.after ?? HOME_PATH);
      return true;
    });
  });
}

showFlash();
initSignIn();
initSetPassword();
initSignOut();
initDeletes();
