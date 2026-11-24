// Clause documents are server-rendered; this module only swaps which one shows.
export function initClauses(): void {
  const items = document.querySelectorAll<HTMLElement>('.clause-item');
  const documents = document.querySelectorAll<HTMLElement>('.clause-document');
  if (!items.length || !documents.length) return;

  items.forEach((item) => {
    item.addEventListener('click', () => {
      const articleKey = item.dataset.article;
      if (!articleKey) return;

      items.forEach((button) => {
        const isActive = button === item;
        button.classList.toggle('active', isActive);
        button.setAttribute('aria-selected', String(isActive));
      });

      documents.forEach((doc) => {
        doc.hidden = doc.dataset.article !== articleKey;
      });
    });
  });
}
