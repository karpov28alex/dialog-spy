(() => {
  'use strict';

  const app = document.getElementById('app');
  if (!app) return;

  function navigate(screen, id = null) {
    const url = new URL(window.location.href);
    url.searchParams.set('screen', screen);
    if (id !== null && id !== undefined && id !== '') url.searchParams.set('id', String(id));
    else url.searchParams.delete('id');
    window.location.assign(url.toString());
  }

  document.addEventListener('click', event => {
    const target = event.target.closest?.('[data-go],[data-dialog],[data-stats-days],[data-back]');
    if (!target || !app.contains(target)) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    if (target.matches('[data-go]')) return navigate(target.dataset.go);
    if (target.matches('[data-dialog]')) return navigate('dialog', target.dataset.dialog);
    if (target.matches('[data-stats-days]')) return navigate('stats', target.dataset.statsDays);

    const current = new URL(window.location.href).searchParams.get('screen') || 'home';
    if (current === 'dialog') return navigate('dialogs');
    if (current !== 'home') return navigate('home');
    window.Telegram?.WebApp?.close?.();
  }, true);
})();
