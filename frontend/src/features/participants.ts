// Participant content is server-rendered; this module only toggles visibility.
export function initParticipants(): void {
  const flags = document.querySelectorAll<HTMLElement>('.flag-card');
  const results = document.querySelectorAll<HTMLElement>('.interest-result');
  if (!flags.length || !results.length) return;

  flags.forEach((flag) => {
    flag.addEventListener('click', () => {
      const key = flag.dataset.participant;
      if (!key) return;

      flags.forEach((button) => {
        const isActive = button === flag;
        button.classList.toggle('active', isActive);
        button.setAttribute('aria-selected', String(isActive));
      });

      results.forEach((result) => {
        result.hidden = result.dataset.participant !== key;
      });
    });
  });
}
