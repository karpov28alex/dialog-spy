(() => {
  'use strict';

  const nativeSetTimeout = window.setTimeout.bind(window);
  const nativeFetch = window.fetch.bind(window);
  const responseCache = new Map();
  const CACHE_TTL = 15000;
  const ACTION_SELECTOR = '[data-go],[data-dialog],[data-back],[data-retry],[data-stats-days],[data-export],[data-theme],[data-copy],[data-pdu-filter],button,a';
  let pressedAction = null;
  let syntheticClick = false;
  let navigationLockedUntil = 0;

  // The dialog list used to replace its entire DOM every five seconds. A tap
  // landing during that replacement could be lost or delivered to the row that
  // moved under the finger. Keep background refreshes useful, but not disruptive.
  window.setTimeout = function phantomStableTimeout(callback, delay, ...args) {
    const source = typeof callback === 'function' ? Function.prototype.toString.call(callback) : '';
    const isDialogRefresh = delay === 5000 && source.includes('render(true)');
    return nativeSetTimeout(callback, isDialogRefresh ? 60000 : delay, ...args);
  };

  function cacheKey(input, options) {
    const method = String(options?.method || 'GET').toUpperCase();
    if (method !== 'GET') return null;
    const url = typeof input === 'string' ? input : input?.url || '';
    if (!/^\/api\/(me|dialogs(?:\?|$)|settings(?:\?|$)|subscription(?:\?|$))/.test(url)) return null;
    const auth = options?.headers?.Authorization || options?.headers?.authorization || '';
    return `${url}|${auth}`;
  }

  window.fetch = async function phantomFastFetch(input, options = {}) {
    const key = cacheKey(input, options);
    const now = Date.now();
    if (key) {
      const cached = responseCache.get(key);
      if (cached && now - cached.savedAt < CACHE_TTL) {
        return new Response(cached.body, cached.init);
      }
    }

    const response = await nativeFetch(input, options);
    if (key && response.ok) {
      try {
        const clone = response.clone();
        const body = await clone.text();
        responseCache.set(key, {
          savedAt: Date.now(),
          body,
          init: {
            status: response.status,
            statusText: response.statusText,
            headers: [...response.headers.entries()],
          },
        });
      } catch {}
    }
    return response;
  };

  function closestAction(target) {
    return target instanceof Element ? target.closest(ACTION_SELECTOR) : null;
  }

  document.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    pressedAction = closestAction(event.target);
    if (!pressedAction) return;
    pressedAction.classList.add('phantom-pressed');
  }, true);

  document.addEventListener('pointercancel', () => {
    pressedAction?.classList.remove('phantom-pressed');
    pressedAction = null;
  }, true);

  document.addEventListener('pointerup', event => {
    const original = pressedAction;
    pressedAction?.classList.remove('phantom-pressed');
    pressedAction = null;
    if (!original || !original.isConnected) return;

    const released = closestAction(event.target);
    if (released !== original) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }

    const isNavigation = original.matches('[data-go],[data-dialog],[data-back],[data-retry],[data-stats-days]');
    if (isNavigation) {
      const now = performance.now();
      if (now < navigationLockedUntil) {
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }
      navigationLockedUntil = now + 450;
      original.classList.add('phantom-activating');
      nativeSetTimeout(() => original.classList.remove('phantom-activating'), 500);
    }
  }, true);

  // Suppress the delayed compatibility click after a handled touch. This avoids
  // a second route firing on iOS WebView without changing normal mouse clicks.
  document.addEventListener('click', event => {
    if (syntheticClick) return;
    const action = closestAction(event.target);
    if (!action || action.disabled) return;
    if (performance.now() < navigationLockedUntil - 400 && action.matches('[data-go],[data-dialog],[data-back],[data-retry],[data-stats-days]')) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);

  const style = document.createElement('style');
  style.textContent = `
    button,a,[data-dialog],[data-go],[data-pdu-filter]{touch-action:manipulation;-webkit-tap-highlight-color:transparent}
    .pdu-chevron,.pdu-chip,.pdu-meta,.dialog .avatar,.dialog .time,.dialog .name,.dialog .preview{pointer-events:none}
    .phantom-pressed{transform:scale(.985)!important;opacity:.9}
    .phantom-activating{pointer-events:none;filter:brightness(1.12)}
  `;
  document.head.appendChild(style);
})();
