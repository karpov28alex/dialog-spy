(() => {
  'use strict';

  const nativeFetch = window.fetch.bind(window);
  const cache = new Map();
  const inFlight = new Map();
  const avatarPreloads = new Map();

  const TTL = {
    '/api/me': 60000,
    '/api/dialogs': 15000,
    '/api/settings': 30000,
    '/api/subscription': 30000,
  };

  function requestUrl(input) {
    return typeof input === 'string' ? input : input?.url || '';
  }

  function requestMethod(options) {
    return String(options?.method || 'GET').toUpperCase();
  }

  function cacheRule(url, options) {
    if (requestMethod(options) !== 'GET') return null;
    const path = Object.keys(TTL).find(prefix => url === prefix || url.startsWith(`${prefix}?`));
    if (!path) return null;
    const auth = options?.headers?.Authorization || options?.headers?.authorization || '';
    return {key: `${url}|${auth}`, ttl: TTL[path], path};
  }

  function responseFrom(entry) {
    return new Response(entry.body, {
      status: entry.status,
      statusText: entry.statusText,
      headers: entry.headers,
    });
  }

  function preloadAvatar(url) {
    if (!url || avatarPreloads.has(url)) return;
    const image = new Image();
    image.decoding = 'async';
    image.fetchPriority = 'high';
    image.src = url;
    avatarPreloads.set(url, image);
    const cleanup = () => {
      window.setTimeout(() => avatarPreloads.delete(url), 10 * 60 * 1000);
    };
    image.addEventListener('load', cleanup, {once: true});
    image.addEventListener('error', cleanup, {once: true});
  }

  async function inspectDialogs(response, path) {
    if (path !== '/api/dialogs') return;
    try {
      const payload = await response.clone().json();
      for (const item of payload?.items || []) preloadAvatar(item?.avatar);
    } catch {}
  }

  window.fetch = async function phantomInstantFetch(input, options = {}) {
    const url = requestUrl(input);
    const rule = cacheRule(url, options);
    const now = Date.now();

    if (rule) {
      const stored = cache.get(rule.key);
      if (stored && now - stored.savedAt < rule.ttl) {
        return responseFrom(stored);
      }
      const pending = inFlight.get(rule.key);
      if (pending) return responseFrom(await pending);
    }

    const networkPromise = nativeFetch(input, options).then(async response => {
      if (!rule || !response.ok) return {response};
      await inspectDialogs(response, rule.path);
      const body = await response.clone().text();
      const entry = {
        savedAt: Date.now(),
        body,
        status: response.status,
        statusText: response.statusText,
        headers: [...response.headers.entries()],
      };
      cache.set(rule.key, entry);
      return {response, entry};
    });

    if (rule) {
      const shared = networkPromise.then(result => result.entry || null).finally(() => inFlight.delete(rule.key));
      inFlight.set(rule.key, shared);
    }

    const result = await networkPromise;
    return result.response;
  };

  function upgradeAvatars(root = document) {
    root.querySelectorAll?.('.avatar img').forEach(image => {
      if (image.dataset.instantAvatar === '1') return;
      image.dataset.instantAvatar = '1';
      image.loading = 'eager';
      image.decoding = 'async';
      image.fetchPriority = 'high';
      preloadAvatar(image.currentSrc || image.src);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');
    if (app) {
      new MutationObserver(records => {
        for (const record of records) {
          for (const node of record.addedNodes) {
            if (node.nodeType === 1) upgradeAvatars(node);
          }
        }
      }).observe(app, {childList: true, subtree: true});
    }
    upgradeAvatars();
  });
})();
