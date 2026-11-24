export interface TabsOptions {
  onActivate?: (targetId: string) => void;
}

// Follows the WAI-ARIA tabs pattern with automatic activation: the tab list
// is a single Tab stop, and the arrow keys, Home and End move between tabs.
export function initTabs(options: TabsOptions = {}): void {
  const tabs = Array.from(document.querySelectorAll<HTMLElement>('.block-tab'));
  const panels = document.querySelectorAll<HTMLElement>('.block-panel');
  if (!tabs.length || !panels.length) return;

  // Tie each tab to its panel for assistive technology.
  tabs.forEach((tab) => {
    const targetId = tab.dataset.target;
    const panel = targetId ? document.getElementById(targetId) : null;
    if (!targetId || !panel) return;
    if (!tab.id) tab.id = `tab-${targetId}`;
    tab.setAttribute('aria-controls', targetId);
    panel.setAttribute('aria-labelledby', tab.id);
  });

  const activate = (targetId: string | undefined): void => {
    if (!targetId) return;

    tabs.forEach((tab) => {
      const isActive = tab.dataset.target === targetId;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', String(isActive));
      // Roving tabindex: only the selected tab is reachable with Tab.
      tab.tabIndex = isActive ? 0 : -1;
    });

    panels.forEach((panel) => {
      const isActive = panel.id === targetId;
      panel.classList.toggle('active', isActive);
      panel.hidden = !isActive;
    });

    options.onActivate?.(targetId);
  };

  const moveTo = (index: number): void => {
    const tab = tabs[(index + tabs.length) % tabs.length];
    if (!tab) return;
    tab.focus();
    activate(tab.dataset.target);
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activate(tab.dataset.target));

    tab.addEventListener('keydown', (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      switch (event.key) {
        case 'ArrowRight':
          moveTo(index + 1);
          break;
        case 'ArrowLeft':
          moveTo(index - 1);
          break;
        case 'Home':
          moveTo(0);
          break;
        case 'End':
          moveTo(tabs.length - 1);
          break;
        default:
          return;
      }
      event.preventDefault();
    });
  });

  const initialTab =
    document.querySelector<HTMLElement>('.block-tab.active') ?? tabs[0];
  activate(initialTab?.dataset.target);
}
