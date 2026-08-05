(() => {
  if (document.querySelector('[data-phantom-global-tabs]')) return;

  const items = [
    { label: 'Главная', href: '/admin', match: pathname => pathname === '/admin' },
    { label: 'Пользователи', href: '/admin/user360-mobile.html?v=5', match: pathname => pathname.includes('user360') },
    { label: 'Диалоги', href: '/admin/dialogs-media.html?v=5', match: pathname => pathname.includes('dialog') },
    { label: 'Статистика', href: '/admin/platform.html?v=5', match: pathname => pathname.includes('platform') || pathname.includes('analytics') },
    { label: 'Операции', href: '/admin/operations.html?v=5', match: pathname => pathname.includes('operations') },
    { label: 'Платежи', href: '/admin/billing-mobile.html?v=5', match: pathname => pathname.includes('billing') },
    { label: 'Настройки', href: '/admin/funnel.html?v=5', match: pathname => pathname.includes('funnel') || pathname.includes('settings') },
  ];

  const pathname = window.location.pathname;
  if (pathname === '/admin') {
    document.querySelectorAll('.side, .nav, .top #logout').forEach(element => {
      element.hidden = true;
      element.setAttribute('aria-hidden', 'true');
    });
    const shell = document.querySelector('.shell');
    if (shell) shell.style.display = 'block';
    const main = document.querySelector('.main');
    if (main) {
      main.style.maxWidth = '1650px';
      main.style.margin = '0 auto';
    }
  }

  const nav = document.createElement('nav');
  nav.className = 'phantom-global-tabs';
  nav.dataset.phantomGlobalTabs = 'true';
  nav.setAttribute('aria-label', 'Разделы админ-панели');

  const scroller = document.createElement('div');
  scroller.className = 'phantom-global-tabs__scroller';

  for (const item of items) {
    const link = document.createElement('a');
    link.href = item.href;
    link.textContent = item.label;
    link.className = 'phantom-global-tabs__item';
    if (item.match(pathname)) {
      link.classList.add('is-active');
      link.setAttribute('aria-current', 'page');
    }
    scroller.appendChild(link);
  }

  const logout = document.createElement('button');
  logout.type = 'button';
  logout.className = 'phantom-global-tabs__logout';
  logout.textContent = 'Выйти';
  logout.addEventListener('click', () => {
    sessionStorage.removeItem('adminToken');
    localStorage.removeItem('adminToken');
    window.location.assign('/admin');
  });

  nav.append(scroller, logout);
  document.body.prepend(nav);

  const terminology = new Map([
    ['Business активен', 'Активные подключения'],
    ['Business подключён', 'Подключение активно'],
    ['Business отключён', 'Подключение отключено'],
    ['business_connections', 'Подключения'],
    ['active_business', 'Активные подключения'],
  ]);

  const normalizeTerms = root => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const value = node.nodeValue?.trim();
      if (value && terminology.has(value)) node.nodeValue = node.nodeValue.replace(value, terminology.get(value));
    }
  };
  normalizeTerms(document.body);
  new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (node.nodeType === Node.ELEMENT_NODE) normalizeTerms(node);
      }
    }
  }).observe(document.body, { childList: true, subtree: true });

  if (pathname.includes('user360')) {
    const token = () => sessionStorage.getItem('adminToken') || localStorage.getItem('adminToken');
    const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[char]);
    const money = value => new Intl.NumberFormat('ru-RU', {
      style: 'currency', currency: 'RUB', maximumFractionDigits: 0,
    }).format(Number(value || 0));
    const api = async url => {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token()}` }, cache: 'no-store',
      });
      if (!response.ok) throw new Error('Не удалось загрузить расширенную карточку');
      return response.json();
    };
    const renderExtra = async userId => {
      try {
        const data = await api(`/api/admin/user360/users/${userId}`);
        const profile = document.getElementById('profile');
        if (!profile) return;
        profile.querySelector('[data-user360-extra]')?.remove();
        let inviter = 'Прямое подключение';
        if (data.user.referrer_user_id) {
          const referrer = await api(`/api/admin/user360/users/${data.user.referrer_user_id}`);
          const ref = referrer.user;
          const label = ref.username ? `@${ref.username}` : (ref.name || `Telegram ${ref.telegram_id}`);
          inviter = `<button class="in" data-open-referrer="${ref.id}" style="width:100%;text-align:left">Пригласил: <b>${esc(label)}</b></button>`;
        }
        const metrics = [
          ['Защищённые медиа', data.metrics.protected_media],
          ['Оплачено всего', money(data.metrics.paid_total)],
          ['Средний чек', money(data.metrics.average_check)],
          ['Приглашено', data.metrics.referrals],
          ['Подключения', data.metrics.business_connections],
          ['Активные подключения', data.metrics.active_business],
        ];
        const section = document.createElement('section');
        section.className = 'card';
        section.dataset.user360Extra = 'true';
        section.innerHTML = `<h3>Источник и расширенная статистика</h3><div class="row"><span>Источник</span><b>${inviter === 'Прямое подключение' ? inviter : 'По приглашению'}</b></div>${inviter !== 'Прямое подключение' ? `<div style="margin:10px 0">${inviter}</div>` : ''}<div class="metrics">${metrics.map(([label, value]) => `<div class="metric"><small>${esc(label)}</small><b>${esc(value)}</b></div>`).join('')}</div>`;
        profile.prepend(section);
        section.querySelector('[data-open-referrer]')?.addEventListener('click', event => {
          const id = Number(event.currentTarget.dataset.openReferrer);
          document.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ behavior: 'smooth' });
          document.querySelector(`[data-id="${id}"]`)?.click();
        });
      } catch (error) {
        console.error('User360 enhancement failed', error);
      }
    };
    document.addEventListener('click', event => {
      const button = event.target.closest('[data-id]');
      if (button) window.setTimeout(() => renderExtra(Number(button.dataset.id)), 250);
    });
  }

  requestAnimationFrame(() => {
    const active = nav.querySelector('.is-active');
    active?.scrollIntoView({ block: 'nearest', inline: 'center' });
  });
})();
