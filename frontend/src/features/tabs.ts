export interface TabsOptions {
  onActivate?: (targetId: string) => void;
}

export function initTabs(options: TabsOptions = {}): void {
  const tabs = document.querySelectorAll<HTMLElement>('.block-tab');
  const panels = document.querySelectorAll<HTMLElement>('.block-panel');
  if (!tabs.length || !panels.length) return;

  const activate = (targetId: string | undefined): void => {
    if (!targetId) return;

    tabs.forEach((tab) => {
      const isActive = tab.dataset.target === targetId;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', String(isActive));
    });

    panels.forEach((panel) => {
      const isActive = panel.id === targetId;
      panel.classList.toggle('active', isActive);
      panel.hidden = !isActive;
    });

    options.onActivate?.(targetId);
  };

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => activate(tab.dataset.target));
  });

  const initialTab =
    document.querySelector<HTMLElement>('.block-tab.active') ?? tabs[0];
  activate(initialTab?.dataset.target);
}
