(() => {
  'use strict';

  const app = document.getElementById('app');
  const tg = window.Telegram?.WebApp;
  if (!app || !tg?.initData) return;

  let token = null;
  let loading = false;
  let mounted = false;
  let lastSignature = '';

  async function auth() {
    if (token) return token;
    const response = await fetch('/api/auth/telegram', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({init_data: tg.initData}),
      cache: 'no-store',
    });
    if (!response.ok) throw new Error('auth');
    token = (await response.json()).access_token;
    return token;
  }

  async function api(path) {
    const bearer = await auth();
    const response = await fetch(path, {
      headers: {Authorization: `Bearer ${bearer}`},
      cache: 'no-store',
    });
    if (!response.ok) throw new Error(String(response.status));
    return response.json();
  }

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));

  function isHome() {
    return Boolean(app.querySelector('.brand') && app.querySelector('.navcard[data-go="dialogs"]'));
  }

  function insightLine(data) {
    const t = data?.totals || {};
    const leaders = data?.leaders || {};
    if (leaders.deleted?.value) return `🗑 ${esc(leaders.deleted.name)} чаще остальных удаляет сообщения`;
    if (leaders.active?.value) return `🔥 Больше всего общения — ${esc(leaders.active.name)}`;
    if (Number(t.protected || 0) > 0) return `👻 В архиве уже ${Number(t.protected || 0).toLocaleString('ru-RU')} скрытых медиа`;
    return '✨ Phantom продолжает собирать события вашего архива';
  }

  function renderPulse(data) {
    const totals = data?.totals || {};
    const activity = Array.isArray(data?.activity) ? data.activity : [];
    const recent = activity.length ? activity[activity.length - 1] : {};
    const values = {
      messages: Number(recent.messages || 0),
      edited: Number(recent.edited || 0),
      deleted: Number(recent.deleted || 0),
      media: Number(recent.media || 0),
    };
    const signature = JSON.stringify(values) + insightLine(data);
    if (mounted && signature === lastSignature) return;
    lastSignature = signature;

    let section = app.querySelector('.engagement-pulse');
    if (!section) {
      section = document.createElement('section');
      section.className = 'engagement-pulse';
      const grid = app.querySelector('.grid');
      grid?.before(section);
    }
    section.innerHTML = `
      <div class="pulse-head">
        <div><span class="pulse-kicker">PHANTOM PULSE</span><h2>Сегодня в архиве</h2></div>
        <span class="pulse-live"><i></i> live</span>
      </div>
      <div class="pulse-metrics">
        <button type="button" data-go="dialogs"><b data-count="${values.messages}">0</b><span>сообщений</span></button>
        <button type="button" data-go="dialogs"><b data-count="${values.edited}">0</b><span>изменено</span></button>
        <button type="button" data-go="dialogs"><b data-count="${values.deleted}">0</b><span>удалено</span></button>
        <button type="button" data-go="stats"><b data-count="${values.media}">0</b><span>медиа</span></button>
      </div>
      <button type="button" class="pulse-insight" data-go="stats">
        <span>${insightLine(data)}</span><strong>→</strong>
      </button>`;
    mounted = true;
    animateCounts(section);
  }

  function animateCounts(root) {
    root.querySelectorAll('[data-count]').forEach(node => {
      const target = Number(node.dataset.count || 0);
      const start = performance.now();
      const duration = Math.min(850, 320 + target * 2);
      const frame = now => {
        const p = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - p, 3);
        node.textContent = Math.round(target * eased).toLocaleString('ru-RU');
        if (p < 1) requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    });
  }

  async function mount() {
    if (loading || !isHome()) return;
    loading = true;
    try {
      renderPulse(await api('/api/intelligence?days=7'));
    } catch {
      // Product stays usable even when intelligence is temporarily unavailable.
    } finally {
      loading = false;
    }
  }

  let queued = false;
  const observer = new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      if (isHome()) mount();
      else mounted = false;
    });
  });
  observer.observe(app, {childList: true, subtree: true});

  let ticking = false;
  addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      ticking = false;
      const section = app.querySelector('.engagement-pulse');
      if (!section) return;
      const rect = section.getBoundingClientRect();
      const progress = Math.max(-1, Math.min(1, (innerHeight * 0.5 - rect.top) / innerHeight));
      section.style.setProperty('--pulse-shift', `${progress * 12}px`);
    });
  }, {passive: true});

  mount();
})();