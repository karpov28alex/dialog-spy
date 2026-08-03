(() => {
  'use strict';

  const STYLE_ID = 'phantom-dialog-next-style';
  const AVATAR_PREFIX = 'phantom.avatar.stable.';
  const preloaded = new Set();

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .avatar.pdn-avatar{position:relative;background-size:cover;background-position:center;background-repeat:no-repeat;isolation:isolate}
      .avatar.pdn-avatar::after{content:'';position:absolute;inset:0;border-radius:inherit;background:linear-gradient(145deg,rgba(116,55,180,.32),rgba(48,27,78,.45));z-index:-1}
      .avatar.pdn-avatar img{position:relative;z-index:1;transition:opacity .14s ease}
      .avatar.pdn-avatar img.pdn-loading{opacity:0}
      .avatar.pdn-avatar img.pdn-ready{opacity:1}
      .pdn-filterbar{display:flex;gap:7px;overflow-x:auto;margin:12px 0 8px;padding:2px 1px 4px;scrollbar-width:none}
      .pdn-filterbar::-webkit-scrollbar{display:none}
      .pdn-filter{flex:0 0 auto;border:1px solid rgba(160,79,247,.22);border-radius:999px;background:rgba(38,25,55,.82);color:#bda9ce;padding:8px 12px;font-size:11px;font-weight:800;white-space:nowrap}
      .pdn-filter.active{border-color:rgba(181,91,255,.65);background:linear-gradient(135deg,#7131d9,#a947ff);color:#fff;box-shadow:0 7px 20px rgba(118,47,194,.25)}
      .msg.pdn-hidden{display:none!important}
      .pdu-day.pdn-hidden{display:none!important}
      .pdn-empty{display:none;margin:18px 0;padding:18px;border:1px dashed rgba(176,90,255,.22);border-radius:18px;color:var(--muted);text-align:center;font-size:12px}
      .pdn-empty.visible{display:block}
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

  function preloadUrl(url) {
    if (!url || preloaded.has(url)) return;
    preloaded.add(url);
    const image = new Image();
    image.decoding = 'async';
    image.fetchPriority = 'high';
    image.src = url;
  }

  function stabilizeAvatar(card) {
    const holder = card.querySelector('.avatar');
    const image = holder?.querySelector('img');
    const id = card.dataset.dialog;
    if (!holder || !image || !id || image.dataset.pdn === '1') return;

    image.dataset.pdn = '1';
    holder.classList.add('pdn-avatar');
    image.loading = 'eager';
    image.decoding = 'async';
    image.fetchPriority = 'high';

    const key = AVATAR_PREFIX + id;
    const intended = image.currentSrc || image.src;
    const cached = storageGet(key);

    if (cached) holder.style.backgroundImage = `url("${cached.replace(/"/g, '%22')}")`;
    image.classList.add('pdn-loading');
    preloadUrl(intended);

    const candidate = new Image();
    candidate.decoding = 'async';
    candidate.fetchPriority = 'high';
    candidate.onload = () => {
      if (!image.isConnected) return;
      holder.style.backgroundImage = `url("${intended.replace(/"/g, '%22')}")`;
      image.src = intended;
      image.classList.remove('pdn-loading');
      image.classList.add('pdn-ready');
      storageSet(key, intended);
    };
    candidate.onerror = () => {
      image.classList.remove('pdn-loading');
      if (!cached) image.style.opacity = '0';
    };
    candidate.src = intended;
  }

  function eagerLoadAllAvatars() {
    const cards = [...document.querySelectorAll('.dialog[data-dialog]')];
    if (!cards.length) return;
    cards.forEach(stabilizeAvatar);
    for (let i = 0; i < cards.length; i += 6) {
      setTimeout(() => cards.slice(i, i + 6).forEach(card => {
        const image = card.querySelector('.avatar img');
        if (image) preloadUrl(image.currentSrc || image.src);
      }), Math.floor(i / 6) * 20);
    }
  }

  function messageFlags(message) {
    const text = message.textContent || '';
    return {
      media: Boolean(message.querySelector('img,video,audio,.media-file,.media-wait,.pdu-media-wrap')),
      edited: Boolean(message.querySelector('.history')) || /изменено/i.test(text),
      deleted: message.classList.contains('deleted') || /удалено/i.test(text),
    };
  }

  function syncDaySeparators(messages) {
    const thread = document.querySelector('.messages');
    if (!thread) return;
    const children = [...thread.children];
    let currentDay = null;
    let dayHasVisible = false;
    const flush = () => currentDay?.classList.toggle('pdn-hidden', !dayHasVisible);
    for (const child of children) {
      if (child.classList.contains('pdu-day')) {
        flush();
        currentDay = child;
        dayHasVisible = false;
      } else if (child.matches('.msg') && !child.classList.contains('pdn-hidden')) {
        dayHasVisible = true;
      }
    }
    flush();
  }

  function applyMessageFilter(filter) {
    const messages = [...document.querySelectorAll('.messages .msg')];
    let visible = 0;
    messages.forEach(message => {
      const flags = messageFlags(message);
      const show = filter === 'all'
        || (filter === 'media' && flags.media)
        || (filter === 'edited' && flags.edited)
        || (filter === 'deleted' && flags.deleted);
      message.classList.toggle('pdn-hidden', !show);
      if (show) visible += 1;
    });
    syncDaySeparators(messages);
    const empty = document.querySelector('.pdn-empty');
    empty?.classList.toggle('visible', visible === 0);
  }

  function enhanceOpenDialog() {
    const page = document.querySelector('.dialog-page');
    const thread = page?.querySelector('.messages');
    if (!page || !thread || page.dataset.pdnFilters === '1') return;
    page.dataset.pdnFilters = '1';

    const messages = [...thread.querySelectorAll('.msg')];
    const counts = messages.reduce((acc, message) => {
      const flags = messageFlags(message);
      acc.media += flags.media ? 1 : 0;
      acc.edited += flags.edited ? 1 : 0;
      acc.deleted += flags.deleted ? 1 : 0;
      return acc;
    }, {media: 0, edited: 0, deleted: 0});

    const bar = document.createElement('div');
    bar.className = 'pdn-filterbar';
    bar.innerHTML = `
      <button class="pdn-filter active" data-pdn-filter="all">Все · ${messages.length}</button>
      <button class="pdn-filter" data-pdn-filter="media">Медиа · ${counts.media}</button>
      <button class="pdn-filter" data-pdn-filter="edited">Изменённые · ${counts.edited}</button>
      <button class="pdn-filter" data-pdn-filter="deleted">Удалённые · ${counts.deleted}</button>`;
    thread.before(bar);

    const empty = document.createElement('div');
    empty.className = 'pdn-empty';
    empty.textContent = 'В этой категории пока нет сообщений';
    thread.after(empty);

    bar.addEventListener('click', event => {
      const button = event.target.closest('[data-pdn-filter]');
      if (!button) return;
      bar.querySelectorAll('.pdn-filter').forEach(item => item.classList.toggle('active', item === button));
      applyMessageFilter(button.dataset.pdnFilter);
      try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light'); } catch {}
    });
  }

  function refresh() {
    injectStyles();
    eagerLoadAllAvatars();
    enhanceOpenDialog();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');
    if (app) new MutationObserver(refresh).observe(app, {childList: true, subtree: true});
    refresh();
  });
})();
