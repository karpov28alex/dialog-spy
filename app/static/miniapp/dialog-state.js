(() => {
  'use strict';
  const nativeFetch = window.fetch.bind(window);
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
    } catch {}
    return response;
  };
})();
