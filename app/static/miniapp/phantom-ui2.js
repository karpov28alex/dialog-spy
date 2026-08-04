(() => {
  'use strict';

  const app = document.getElementById('app');
  if (!app) return;

  const dayLabel = value => {
    const date = new Date(value || 0);
    if (Number.isNaN(date.getTime())) return '';
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const diff = Math.round((today - target) / 86400000);
    if (diff === 0) return 'Сегодня';
    if (diff === 1) return 'Вчера';
    return new Intl.DateTimeFormat('ru-RU', {day:'numeric', month:'long', year: target.getFullYear() === today.getFullYear() ? undefined : 'numeric'}).format(date);
  };

  const classifyDialog = card => {
    const text = (card.textContent || '').toLowerCase();
    return {
      edited: text.includes('изменено'),
      deleted: text.includes('удалено'),
      media: /фото|видео|голос|кружок|документ|медиа|стикер/.test(text),
    };
  };

  function decorateDialogs() {
    const list = app.querySelector('.list');
    const cards = list ? [...list.querySelectorAll('.dialog[data-dialog]')] : [];
    if (!list || !cards.length) return;

    cards.forEach(card => {
      if (card.dataset.p2Ready === '1') return;
      card.dataset.p2Ready = '1';
      card.classList.add('p2-card');
      const flags = classifyDialog(card);
      card.dataset.p2Edited = flags.edited ? '1' : '0';
      card.dataset.p2Deleted = flags.deleted ? '1' : '0';
      card.dataset.p2Media = flags.media ? '1' : '0';
      const count = card.querySelector('.dialog-count');
      const badges = document.createElement('div');
      badges.className = 'p2-badges';
      const rawCount = (count?.textContent || '').match(/\d+/)?.[0] || '0';
      badges.innerHTML = `<span class="p2-badge">💬 ${rawCount}</span>`
        + (flags.edited ? '<span class="p2-badge">✎ изменено</span>' : '')
        + (flags.deleted ? '<span class="p2-badge deleted">⌫ удалено</span>' : '')
        + (flags.media ? '<span class="p2-badge media">▧ медиа</span>' : '');
      count?.replaceWith(badges);
    });

    if (list.dataset.p2Shell === '1') return;
    list.dataset.p2Shell = '1';
    const summary = document.createElement('section');
    const edited = cards.filter(c => c.dataset.p2Edited === '1').length;
    const deleted = cards.filter(c => c.dataset.p2Deleted === '1').length;
    const media = cards.filter(c => c.dataset.p2Media === '1').length;
    summary.className = 'p2-dialog-summary';
    summary.innerHTML = `<div class="p2-stat"><b>${cards.length}</b><span>диалогов</span></div><div class="p2-stat"><b>${edited + deleted}</b><span>изменений</span></div><div class="p2-stat"><b>${media}</b><span>с медиа</span></div>`;
    const filters = document.createElement('div');
    filters.className = 'p2-filters';
    filters.innerHTML = '<button class="p2-filter active" data-p2-filter="all">Все</button><button class="p2-filter" data-p2-filter="edited">Изменённые</button><button class="p2-filter" data-p2-filter="deleted">Удалённые</button><button class="p2-filter" data-p2-filter="media">Медиа</button>';
    list.before(summary, filters);

    let activeFilter = 'all';
    const search = app.querySelector('#search');
    const apply = () => {
      const query = (search?.value || '').trim().toLowerCase();
      let visible = 0;
      cards.forEach(card => {
        const matchesText = !query || (card.textContent || '').toLowerCase().includes(query);
        const matchesFilter = activeFilter === 'all'
          || (activeFilter === 'edited' && card.dataset.p2Edited === '1')
          || (activeFilter === 'deleted' && card.dataset.p2Deleted === '1')
          || (activeFilter === 'media' && card.dataset.p2Media === '1');
        card.hidden = !(matchesText && matchesFilter);
        if (!card.hidden) visible += 1;
      });
      let empty = list.querySelector('.p2-empty');
      if (!empty) {
        empty = document.createElement('div');
        empty.className = 'p2-empty';
        empty.textContent = 'Ничего не найдено';
        list.appendChild(empty);
      }
      empty.hidden = visible !== 0;
    };
    filters.addEventListener('click', event => {
      const button = event.target.closest('[data-p2-filter]');
      if (!button) return;
      activeFilter = button.dataset.p2Filter;
      filters.querySelectorAll('.p2-filter').forEach(item => item.classList.toggle('active', item === button));
      apply();
    });
    search?.addEventListener('input', apply, {passive:true});
  }

  function messageKind(message) {
    const text = (message.textContent || '').toLowerCase();
    return {
      media: Boolean(message.querySelector('img,video,audio,.media-file,.media-wait')),
      edited: text.includes('изменено') || Boolean(message.querySelector('.history')),
      deleted: message.classList.contains('deleted') || text.includes('удалено'),
    };
  }

  function decorateThread() {
    const page = app.querySelector('.dialog-page');
    const thread = page?.querySelector('.messages');
    if (!page || !thread) return;
    page.classList.add('p2-page');
    thread.classList.add('p2-thread');
    const messages = [...thread.querySelectorAll('.msg')];
    if (!messages.length) return;

    let lastDay = '';
    messages.forEach(message => {
      message.classList.add('p2-message');
      if (message.dataset.p2Day === '1') return;
      message.dataset.p2Day = '1';
      const meta = message.querySelector('.meta')?.textContent || '';
      const match = meta.match(/(\d{2}\.\d{2}\.\d{4})/);
      const label = match ? match[1] : '';
      if (label && label !== lastDay) {
        lastDay = label;
        const [d,m,y] = label.split('.');
        const day = document.createElement('div');
        day.className = 'p2-day';
        day.textContent = dayLabel(`${y}-${m}-${d}T00:00:00`);
        message.before(day);
      }
    });

    if (page.dataset.p2Tools !== '1') {
      page.dataset.p2Tools = '1';
      const tools = document.createElement('div');
      tools.className = 'p2-dialog-tools';
      tools.innerHTML = '<button class="p2-tool active" data-p2-kind="all">Все</button><button class="p2-tool" data-p2-kind="media">Медиа</button><button class="p2-tool" data-p2-kind="edited">Изменённые</button><button class="p2-tool" data-p2-kind="deleted">Удалённые</button>';
      thread.before(tools);
      tools.addEventListener('click', event => {
        const button = event.target.closest('[data-p2-kind]');
        if (!button) return;
        const kind = button.dataset.p2Kind;
        tools.querySelectorAll('.p2-tool').forEach(item => item.classList.toggle('active', item === button));
        messages.forEach(message => {
          const flags = messageKind(message);
          const show = kind === 'all' || flags[kind];
          message.classList.toggle('p2-hidden', !show);
        });
      });
    }

    if (!page.querySelector('.p2-jump')) {
      const jump = document.createElement('button');
      jump.className = 'p2-jump';
      jump.type = 'button';
      jump.textContent = '↓';
      jump.setAttribute('aria-label', 'К новым сообщениям');
      page.appendChild(jump);
      const update = () => {
        const distance = document.documentElement.scrollHeight - (window.scrollY + window.innerHeight);
        jump.classList.toggle('visible', distance > 420);
      };
      jump.addEventListener('click', () => window.scrollTo({top:document.documentElement.scrollHeight,behavior:'smooth'}));
      window.addEventListener('scroll', update, {passive:true});
      update();
    }
  }

  function refresh() {
    decorateDialogs();
    decorateThread();
  }

  const observer = new MutationObserver(() => requestAnimationFrame(refresh));
  observer.observe(app, {childList:true, subtree:true});
  document.addEventListener('DOMContentLoaded', refresh, {once:true});
  refresh();
})();