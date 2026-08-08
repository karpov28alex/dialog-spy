(() => {
  'use strict';
  const nativeFetch = window.fetch.bind(window);
  const app = document.getElementById('app');
  const FOCUS_KEY = 'phantom:focus-dialog';
  let focusPending = false;

  function consumeFocusedDialog() {
    if (focusPending || !app) return;
    const raw = sessionStorage.getItem(FOCUS_KEY);
    if (!raw) return;
    const id = String(raw).replace(/[^0-9]/g, '');
    if (!id) { sessionStorage.removeItem(FOCUS_KEY); return; }
    const button = app.querySelector(`.dialog[data-dialog="${id}"]`);
    if (!button) return;
    focusPending = true;
    sessionStorage.removeItem(FOCUS_KEY);
    requestAnimationFrame(() => {
      button.scrollIntoView({block: 'center', behavior: 'smooth'});
      button.classList.add('phantom-focus-dialog');
      setTimeout(() => {
        button.click();
        focusPending = false;
      }, 180);
    });
  }

  window.fetch = async (input, init) => {
    const response = await nativeFetch(input, init);
    try {
      const raw = typeof input === 'string' ? input : input?.url || '';
      const url = new URL(raw, location.href);
      const method = String(init?.method || 'GET').toUpperCase();
      if (method === 'GET' && /^\/api\/dialogs\/\d+$/.test(url.pathname) && response.ok) {
        response.clone().json().then(payload => {
          if (!payload?.dialog || !Array.isArray(payload?.messages)) return;
          window.__phantomDialogDetail = payload;
          document.dispatchEvent(new CustomEvent('phantom:dialog-detail', {detail: payload}));
        }).catch(() => {});
      }
      if (method === 'GET' && url.pathname === '/api/dialogs' && response.ok) {
        setTimeout(consumeFocusedDialog, 0);
      }
    } catch {}
    return response;
  };

  if (app) new MutationObserver(consumeFocusedDialog).observe(app, {childList: true, subtree: true});
})();
