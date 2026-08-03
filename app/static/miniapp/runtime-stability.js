(() => {
  const nativeFetch = window.fetch.bind(window);
  const nativeSetTimeout = window.setTimeout.bind(window);
  const avatarCache = new Map();
  const AVATAR_TTL = 14 * 60 * 1000;

  window.setTimeout = function phantomStableTimeout(callback, delay, ...args) {
    const source = typeof callback === 'function' ? String(callback) : '';
    const isDialogRefresh = delay === 5000 && source.includes('render(true)');
    return nativeSetTimeout(callback, isDialogRefresh ? 60000 : delay, ...args);
  };

  window.fetch = async function phantomStableFetch(input, options = {}) {
    const response = await nativeFetch(input, options);
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!response.ok || !/\/api\/dialogs(?:\?|$)/.test(url)) return response;

    try {
      const payload = await response.clone().json();
      const now = Date.now();
      for (const item of payload.items || []) {
        const key = String(item.id);
        const cached = avatarCache.get(key);
        if (item.avatar) {
          if (!cached || now - cached.savedAt >= AVATAR_TTL) {
            avatarCache.set(key, {url: item.avatar, savedAt: now});
          } else {
            item.avatar = cached.url;
          }
        } else if (cached && now - cached.savedAt < AVATAR_TTL) {
          item.avatar = cached.url;
        }
      }
      return new Response(JSON.stringify(payload), {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      });
    } catch {
      return response;
    }
  };

  document.addEventListener('error', event => {
    const image = event.target;
    if (!(image instanceof HTMLImageElement) || !image.closest('.avatar')) return;
    const dialog = image.closest('[data-dialog]');
    if (!dialog) return;
    const cached = avatarCache.get(String(dialog.dataset.dialog));
    if (cached && image.src !== cached.url) image.src = cached.url;
  }, true);
})();
