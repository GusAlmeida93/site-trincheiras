import { createPlayer } from '../api/client';
import { byId } from '../lib/dom';
import { setPlayerId } from '../state/player';

function normalizeInput(value: string | null | undefined): string {
  return String(value ?? '')
    .trim()
    .replace(/\s+/g, ' ');
}

function generateRecruitNumber(issueDate: Date): string {
  const yearShort = String(issueDate.getFullYear()).slice(-2);
  const month = String(issueDate.getMonth() + 1).padStart(2, '0');
  const day = String(issueDate.getDate()).padStart(2, '0');
  const randomSuffix = String(Math.floor(Math.random() * 10000)).padStart(4, '0');
  return `TRN-${yearShort}${month}${day}-${randomSuffix}`;
}

function formatIssueDate(issueDate: Date): string {
  return issueDate.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function initEnlistment(): void {
  const form = byId<HTMLFormElement>('enlist-form');
  const nameInput = byId<HTMLInputElement>('enlist-name');
  const classInput = byId<HTMLInputElement>('enlist-class');
  if (!form || !nameInput || !classInput) return;

  const avatarToggle = byId<HTMLButtonElement>('enlist-avatar-toggle');
  const avatarPanel = byId('enlist-avatar-panel');
  const avatarGrid = byId('enlist-avatar-grid');
  const feedback = byId('enlist-feedback');
  const card = byId('enlist-card');
  const cardAvatar = byId<HTMLImageElement>('enlist-card-avatar');
  const cardName = byId('enlist-card-name');
  const cardClass = byId('enlist-card-class');
  const cardId = byId('enlist-card-id');
  const cardIssued = byId('enlist-card-issued');
  const heroBanner = byId('hero-banner');
  const heroRecruit = byId('hero-recruit');
  const heroRecruitAvatar = byId<HTMLImageElement>('hero-recruit-avatar');
  const heroRecruitName = byId('hero-recruit-name');
  const heroRecruitClass = byId('hero-recruit-class');

  let selectedAvatarUrl = '';
  let selectedAvatarLabel = '';
  let isAvatarPanelOpen = true;

  const setFeedback = (message: string, status: '' | 'is-error' | 'is-success'): void => {
    if (!feedback) return;
    feedback.textContent = message;
    feedback.classList.remove('is-error', 'is-success');
    if (status) {
      feedback.classList.add(status);
    }
  };

  const setAvatarGuideOpen = (isOpen: boolean): void => {
    if (!avatarToggle || !avatarPanel) return;
    isAvatarPanelOpen = isOpen;
    avatarToggle.setAttribute('aria-expanded', String(isAvatarPanelOpen));
    avatarPanel.classList.toggle('is-collapsed', !isAvatarPanelOpen);
  };

  const selectAvatar = (optionButton: HTMLElement): void => {
    if (!avatarGrid) return;
    avatarGrid
      .querySelectorAll<HTMLElement>('.enlist-avatar-option')
      .forEach((button) => {
        const isSelected = button === optionButton;
        button.classList.toggle('is-selected', isSelected);
        button.setAttribute('aria-pressed', String(isSelected));
      });
    selectedAvatarUrl = optionButton.dataset.avatarUrl ?? '';
    selectedAvatarLabel = optionButton.dataset.avatarLabel ?? '';
  };

  // Avatar options are server-rendered; one delegated listener covers all 20.
  avatarGrid?.addEventListener('click', (event) => {
    const target = event.target as HTMLElement | null;
    const option = target?.closest<HTMLElement>('.enlist-avatar-option');
    if (!option) return;
    selectAvatar(option);
    if (feedback?.classList.contains('is-error')) {
      setFeedback('', '');
    }
  });

  if (avatarToggle && avatarPanel) {
    setAvatarGuideOpen(true);
    avatarToggle.addEventListener('click', () => {
      setAvatarGuideOpen(!isAvatarPanelOpen);
    });
  }

  const renderCard = (fullName: string, classroom: string): void => {
    if (!card || !cardAvatar || !cardName || !cardClass) return;
    const issueDate = new Date();
    cardAvatar.src = selectedAvatarUrl;
    cardAvatar.alt = selectedAvatarLabel || 'Avatar selecionado';
    cardName.textContent = fullName;
    cardClass.textContent = classroom;
    if (cardId) {
      cardId.textContent = generateRecruitNumber(issueDate);
    }
    if (cardIssued) {
      cardIssued.textContent = formatIssueDate(issueDate);
    }
    card.hidden = false;
  };

  const renderHeroBadge = (fullName: string, classroom: string): void => {
    if (
      !heroBanner ||
      !heroRecruit ||
      !heroRecruitAvatar ||
      !heroRecruitName ||
      !heroRecruitClass
    ) {
      return;
    }
    heroRecruitAvatar.src = selectedAvatarUrl;
    heroRecruitAvatar.alt = selectedAvatarLabel || 'Avatar do aluno';
    heroRecruitName.textContent = fullName;
    heroRecruitClass.textContent = classroom;
    heroRecruit.hidden = false;
    heroBanner.classList.add('has-recruit');
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const fullName = normalizeInput(nameInput.value);
    const classroom = normalizeInput(classInput.value);

    if (fullName.split(' ').length < 2) {
      setFeedback('Informe o nome completo (nome e sobrenome).', 'is-error');
      nameInput.focus();
      return;
    }

    if (classroom.length < 2) {
      setFeedback('Informe a turma corretamente (ex.: 9º A).', 'is-error');
      classInput.focus();
      return;
    }

    if (!selectedAvatarUrl) {
      setAvatarGuideOpen(true);
      setFeedback('Selecione um avatar para concluir o alistamento.', 'is-error');
      return;
    }

    nameInput.value = fullName;
    classInput.value = classroom;
    renderCard(fullName, classroom);
    renderHeroBadge(fullName, classroom);

    const recruitNumber = cardId?.textContent || null;
    const player = await createPlayer({
      name: fullName,
      class_group: classroom,
      recruit_number: recruitNumber,
    });
    if (player) {
      setPlayerId(player.id);
    }

    setFeedback('Credencial emitida com sucesso.', 'is-success');
  });
}
