export function initFlipCards(): void {
  const cards = document.querySelectorAll<HTMLElement>('.intel-photo-card');
  if (!cards.length) return;

  cards.forEach((card) => {
    card.classList.remove('is-flipped');
    card.setAttribute('aria-pressed', 'false');
  });

  cards.forEach((card) => {
    card.addEventListener('click', () => {
      const isAlreadyFlipped = card.classList.contains('is-flipped');
      cards.forEach((item) => {
        item.classList.remove('is-flipped');
        item.setAttribute('aria-pressed', 'false');
      });

      if (!isAlreadyFlipped) {
        card.classList.add('is-flipped');
        card.setAttribute('aria-pressed', 'true');
      }
    });
  });
}
