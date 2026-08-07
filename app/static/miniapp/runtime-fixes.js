(() => {
  'use strict';
  const app = document.getElementById('app');
  if (!app) return;

  const FILTER_MAP = {
    all: () => true,
    edited: card => Number(card.dataset.archiveEdited || 0) > 0,
    deleted: card => Number(card.dataset.archiveDeleted || 0) > 0,
    media: card => Number(card.dataset.archiveMedia || 0) > 0,
  };

  function activeFilter() {
    return app.querySelector('.p2-filters [data-p2-filter].active')?.dataset.p2Filter || 'all';
  }

  function applyPrimaryFilter(filter = activeFilter()) {
    const list = app.querySelector('.list');
    if (!list) return;
    const search = app.querySelector('#search');
    const query = (search?.value || '').trim().toLowerCase();
    const predicate = FILTER_MAP[filter] || FILTER_MAP.all;
    const cards = [...list.querySelectorAll('.dialog[data-dialog]')];
    let visible = 0;
    for (const card of cards) {
      const matchesText = !query || (card.textContent || '').toLowerCase().includes(query);
      const show = matchesText && predicate(card);
      card.hidden = !show;
      if (show) visible += 1;
    }
    let empty = list.querySelector('.p2-empty');
    if (!empty) {
      empty = document.createElement('div');
      empty.className = 'p2-empty';
      empty.textContent = 'Ничего не найдено';
      list.appendChild(empty);
    }
    empty.hidden = visible > 0;
  }

  document.addEventListener('click', event => {
    const button = event.target.closest?.('.p2-filters [data-p2-filter]');
    if (!button || !app.contains(button)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const filters = button.closest('.p2-filters');
    filters.querySelectorAll('[data-p2-filter]').forEach(item => item.classList.toggle('active', item === button));
    applyPrimaryFilter(button.dataset.p2Filter || 'all');
    try { window.Telegram?.WebApp?.HapticFeedback?.selectionChanged?.(); } catch {}
  }, true);

  document.addEventListener('archive:metrics-ready', () => applyPrimaryFilter());
  document.addEventListener('input', event => {
    if (event.target?.id === 'search') requestAnimationFrame(() => applyPrimaryFilter());
  }, true);

  const observer = new MutationObserver(() => {
    if (app.querySelector('.p2-filters')) requestAnimationFrame(() => applyPrimaryFilter());
  });
  observer.observe(app, {childList: true, subtree: true});
})();
