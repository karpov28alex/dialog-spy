(() => {
  'use strict';

  const STYLE_ID = 'phantom-dialog-next-v2-style';
  const AVATAR_PREFIX = 'phantom.avatar.stable.';
  const queued = new WeakSet();
  const queue = [];
  let active = 0;
  const MAX_ACTIVE = 2;
  const MAX_ATTEMPTS = 4;

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .avatar.pdn2-avatar{position:relative;overflow:hidden;background-size:cover;background-position:center;background-repeat:no-repeat}
      .avatar.pdn2-avatar img{width:100%;height:100%;object-fit:cover;display:block;opacity:0;transition:opacity .16s ease}
      .avatar.pdn2-avatar img.pdn2-ready{opacity:1}
      .avatar.pdn2-avatar::after{content:'';position:absolute;inset:0;border-radius:inherit;background:linear-gradient(145deg,rgba(116,55,180,.4),rgba(48,27,78,.5));z-index:-1}
      .pdn2-filterbar{display:flex;gap:7px;overflow-x:auto;margin:12px 0 8px;padding:2px 1px 4px;scrollbar-width:none}
      .pdn2-filterbar::-webkit-scrollbar{display:none}
      .pdn2-filter{flex:0 0 auto;border:1px solid rgba(160,79,247,.22);border-radius:999px;background:rgba(38,25,55,.82);color:#bda9ce;padding:8px 12px;font-size:11px;font-weight:800;white-space:nowrap}
      .pdn2-filter.active{border-color:rgba(181,91,255,.65);background:linear-gradient(135deg,#7131d9,#a947ff);color:#fff;box-shadow:0 7px 20px rgba(118,47,194,.25)}
      .msg.pdn2-hidden,.pdu-day.pdn2-hidden{display:none!important}
      .pdn2-empty{display:none;margin:18px 0;padding:18px;border:1px dashed rgba(176,90,255,.22);border-radius:18px;color:var(--muted);text-align:center;font-size:12px}
      .pdn2-empty.visible{display:block}
    `;
    document.head.appendChild(style);
  }

  function storageGet(key) {
    try { return localStorage.getItem(key) || sessionStorage.getItem(key); } catch { return null; }
  }

  function storageSet(key, value) {
    try { localStorage.setItem(key, value); } catch {}
    try { sessionStorage.setItem(key, value); } catch {}
  }

  function backgroundUrl(url) {
    return `url("${String(url).replace(/"/g, '%22')}")`;
  }

  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function loadImage(url) {
    return new Promise((resolve, reject) => {
      const candidate = new Image();
      candidate.decoding = 'async';
      candidate.fetchPriority = 'high';
      candidate.onload = () => resolve(url);
      candidate.onerror = reject;
      candidate.src = url;
    });
  }

  async function processAvatar(job) {
    const {holder, image, intended, key} = job;
    if (!holder.isConnected || !image.isConnected) return;

    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
      try {
        const separator = intended.includes('?') ? '&' : '?';
        const requestUrl = attempt === 1 ? intended : `${intended}${separator}avatar_retry=${attempt}_${Date.now()}`;
        await loadImage(requestUrl);
        if (!holder.isConnected || !image.isConnected) return;
        holder.style.backgroundImage = backgroundUrl(requestUrl);
        image.src = requestUrl;
        image.classList.add('pdn2-ready');
        storageSet(key, intended);
        return;
      } catch {
        if (attempt < MAX_ATTEMPTS) await delay(350 * attempt);
      }
    }

    const cached = storageGet(key);
    if (cached && holder.isConnected) holder.style.backgroundImage = backgroundUrl(cached);
  }

  function pumpQueue() {
    while (active < MAX_ACTIVE && queue.length) {
      const job = queue.shift();
      active += 1;
      processAvatar(job).finally(() => {
        active -= 1;
        pumpQueue();
      });
    }
  }

  function enqueueAvatar(card) {
    if (queued.has(card)) return;
    const holder = card.querySelector('.avatar');
    const image = holder?.querySelector('img');
    const id = card.dataset.dialog;
    if (!holder || !image || !id) return;

    queued.add(card);
    holder.classList.add('pdn2-avatar');
    image.loading = 'eager';
    image.decoding = 'async';
    image.fetchPriority = 'high';

    const key = AVATAR_PREFIX + id;
    const intended = image.getAttribute('src') || image.currentSrc || image.src;
    const cached = storageGet(key);
    if (cached) holder.style.backgroundImage = backgroundUrl(cached);

    if (!intended) return;
    queue.push({holder, image, intended, key});
    pumpQueue();
  }

  function enqueueAllAvatars() {
    document.querySelectorAll('.dialog[data-dialog]').forEach(enqueueAvatar);
  }

  function flags(message) {
    const text = message.textContent || '';
    return {
      media: Boolean(message.querySelector('img,video,audio,.media-file,.media-wait,.pdu-media-wrap')),
      edited: Boolean(message.querySelector('.history')) || /изменено/i.test(text),
      deleted: message.classList.contains('deleted') || /удалено/i.test(text),
    };
  }

  function syncDays(thread) {
    let currentDay = null;
    let visible = false;
    const flush = () => currentDay?.classList.toggle('pdn2-hidden', !visible);
    [...thread.children].forEach(child => {
      if (child.classList.contains('pdu-day')) {
        flush();
        currentDay = child;
        visible = false;
      } else if (child.matches('.msg') && !child.classList.contains('pdn2-hidden')) {
        visible = true;
      }
    });
    flush();
  }

  function enhanceFilters() {
    const page = document.querySelector('.dialog-page');
    const thread = page?.querySelector('.messages');
    if (!page || !thread || page.dataset.pdn2Filters === '1') return;
    page.dataset.pdn2Filters = '1';

    const messages = [...thread.querySelectorAll('.msg')];
    const counts = messages.reduce((acc, message) => {
      const value = flags(message);
      acc.media += value.media ? 1 : 0;
      acc.edited += value.edited ? 1 : 0;
      acc.deleted += value.deleted ? 1 : 0;
      return acc;
    }, {media: 0, edited: 0, deleted: 0});

    const bar = document.createElement('div');
    bar.className = 'pdn2-filterbar';
    bar.innerHTML = `<button class="pdn2-filter active" data-pdn2="all">Все · ${messages.length}</button><button class="pdn2-filter" data-pdn2="media">Медиа · ${counts.media}</button><button class="pdn2-filter" data-pdn2="edited">Изменённые · ${counts.edited}</button><button class="pdn2-filter" data-pdn2="deleted">Удалённые · ${counts.deleted}</button>`;
    thread.before(bar);

    const empty = document.createElement('div');
    empty.className = 'pdn2-empty';
    empty.textContent = 'В этой категории пока нет сообщений';
    thread.after(empty);

    bar.addEventListener('click', event => {
      const button = event.target.closest('[data-pdn2]');
      if (!button) return;
      bar.querySelectorAll('.pdn2-filter').forEach(item => item.classList.toggle('active', item === button));
      let shown = 0;
      messages.forEach(message => {
        const value = flags(message);
        const filter = button.dataset.pdn2;
        const show = filter === 'all' || value[filter];
        message.classList.toggle('pdn2-hidden', !show);
        if (show) shown += 1;
      });
      syncDays(thread);
      empty.classList.toggle('visible', shown === 0);
    });
  }

  function refresh() {
    injectStyles();
    enqueueAllAvatars();
    enhanceFilters();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');
    if (app) new MutationObserver(refresh).observe(app, {childList: true, subtree: true});
    refresh();
  });
})();
