(() => {
  if (document.querySelector('[data-phantom-global-tabs]')) return;

  const items = [
    { label: 'Главная', href: '/admin', match: pathname => pathname === '/admin' },
    { label: 'Пользователи', href: '/admin/user360-mobile.html?v=4', match: pathname => pathname.includes('user360') },
    { label: 'Диалоги', href: '/admin/dialogs-media.html?v=4', match: pathname => pathname.includes('dialog') },
    { label: 'Статистика', href: '/admin/platform.html?v=4', match: pathname => pathname.includes('platform') || pathname.includes('analytics') },
    { label: 'Операции', href: '/admin/operations.html?v=4', match: pathname => pathname.includes('operations') },
    { label: 'Платежи', href: '/admin/billing-mobile.html?v=4', match: pathname => pathname.includes('billing') },
    { label: 'Настройки', href: '/admin/funnel.html?v=4', match: pathname => pathname.includes('funnel') || pathname.includes('settings') },
  ];

  const pathname = window.location.pathname;
  if (pathname === '/admin') {
    document.querySelectorAll('.nav').forEach(element => {
      element.hidden = true;
      element.setAttribute('aria-hidden', 'true');
    });
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

  requestAnimationFrame(() => {
    const active = nav.querySelector('.is-active');
    active?.scrollIntoView({ block: 'nearest', inline: 'center' });
  });
})();
