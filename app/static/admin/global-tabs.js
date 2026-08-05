(() => {
  if (document.querySelector('[data-phantom-global-tabs]')) return;

  const items = [
    { label: 'Главная', href: '/admin', match: pathname => pathname === '/admin' },
    { label: 'Пользователи', href: '/admin/user360-mobile.html?v=7', match: pathname => pathname.includes('user360') },
    { label: 'Диалоги', href: '/admin/dialogs-media.html?v=7', match: pathname => pathname.includes('dialog') },
    { label: 'Статистика', href: '/admin/platform.html?v=7', match: pathname => pathname.includes('platform') || pathname.includes('analytics') },
    { label: 'Операции', href: '/admin/operations.html?v=7', match: pathname => pathname.includes('operations') },
    { label: 'Платежи', href: '/admin/billing-mobile.html?v=7', match: pathname => pathname.includes('billing') },
    { label: 'Настройки', href: '/admin/funnel.html?v=7', match: pathname => pathname.includes('funnel') || pathname.includes('settings') },
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

  if (pathname.includes('dialogs-media')) {
    const header = document.querySelector('.side-head');
    const toolbar = header?.querySelector('.toolbar');
    if (header && toolbar && !document.querySelector('[data-owner-filter]')) {
      const ownerPanel = document.createElement('section');
      ownerPanel.dataset.ownerFilter = 'true';
      ownerPanel.style.cssText = 'display:grid;gap:8px;margin-top:12px;padding:10px;border:1px solid var(--line);border-radius:13px;background:#0c0911';
      ownerPanel.innerHTML = `
        <strong>Архив владельца</strong>
        <div style="display:grid;grid-template-columns:1fr auto;gap:7px">
          <input class="input" id="ownerSearch" placeholder="@username, Telegram ID или имя">
          <button class="btn primary" id="ownerSearchBtn">Выбрать</button>
        </div>
        <div id="ownerResults"></div>
        <div id="selectedOwner"></div>`;
      toolbar.before(ownerPanel);

      const ownerSearch = document.getElementById('ownerSearch');
      const ownerResults = document.getElementById('ownerResults');
      const selectedOwner = document.getElementById('selectedOwner');
      const authToken = () => sessionStorage.getItem('adminToken') || localStorage.getItem('adminToken');
      const safe = value => String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
      })[character]);
      const request = async url => {
        const response = await fetch(url, {
          headers: { Authorization: `Bearer ${authToken()}` },
          cache: 'no-store',
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || 'Не удалось загрузить архив');
        return data;
      };
      const ownerLabel = owner => owner.username
        ? `@${owner.username}`
        : (owner.name || `Telegram ${owner.telegram_id}`);
      const syncOwnerUrl = ownerId => {
        const url = new URL(window.location.href);
        if (ownerId) url.searchParams.set('user_id', String(ownerId));
        else url.searchParams.delete('user_id');
        window.history.replaceState({}, '', url);
      };
      const renderOwnerDialogs = async owner => {
        const data = await request(`/api/admin/users/${owner.id}/dialogs`);
        selectedOwner.innerHTML = `
          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px;border:1px solid var(--line);border-radius:11px">
            <span><small style="color:var(--muted)">Выбран владелец</small><br><b>${safe(ownerLabel(owner))}</b> · ${data.items.length} диал.</span>
            <span style="display:flex;gap:6px">
              <a class="btn" href="/admin/user360-mobile.html?user_id=${owner.id}">User360</a>
              <button class="btn" id="clearOwner">Сбросить</button>
            </span>
          </div>`;
        document.getElementById('clearOwner').onclick = () => {
          syncOwnerUrl(null);
          selectedOwner.innerHTML = '';
          ownerResults.innerHTML = '';
          window.loadDialogs();
        };
        const dialogsRoot = document.getElementById('dialogs');
        dialogsRoot.innerHTML = data.items.length
          ? data.items.map(item => `<button class="dialog" data-dialog="${item.id}">${window.avatar(item.avatar, item.display_name)}<span class="dialog-content"><span class="dialog-top"><span class="dialog-name">${safe(item.display_name || 'Диалог')}</span><span class="time">${window.shortTime(item.last_message_at)}</span></span><span class="preview">Только архив ${safe(ownerLabel(owner))}</span><span class="owner">${item.messages_count} сообщ.</span></span></button>`).join('')
          : '<div class="empty">У владельца пока нет сохранённых диалогов</div>';
        dialogsRoot.querySelectorAll('[data-dialog]').forEach(button => {
          button.onclick = () => window.openDialog(Number(button.dataset.dialog), button);
        });
        syncOwnerUrl(owner.id);
      };
      const searchOwners = async () => {
        const term = ownerSearch.value.trim();
        ownerResults.innerHTML = '<div class="empty" style="padding:10px">Поиск…</div>';
        try {
          const data = await request(`/api/admin/dialog-archive/users?search=${encodeURIComponent(term)}&limit=30`);
          ownerResults.innerHTML = data.items.length
            ? data.items.map(owner => `<button class="btn" style="width:100%;text-align:left;margin-top:6px" data-owner-id="${owner.id}" data-owner="${safe(encodeURIComponent(JSON.stringify(owner)))}"><b>${safe(ownerLabel(owner))}</b><br><small>${owner.dialogs_count} диал. · ${owner.messages_count} сообщ.</small></button>`).join('')
            : '<div class="empty" style="padding:10px">Владелец не найден</div>';
          ownerResults.querySelectorAll('[data-owner-id]').forEach(button => {
            button.onclick = () => {
              const owner = JSON.parse(decodeURIComponent(button.dataset.owner));
              ownerResults.innerHTML = '';
              renderOwnerDialogs(owner).catch(error => { ownerResults.textContent = error.message; });
            };
          });
        } catch (error) {
          ownerResults.innerHTML = `<div class="unavailable">${safe(error.message)}</div>`;
        }
      };
      document.getElementById('ownerSearchBtn').onclick = searchOwners;
      ownerSearch.onkeydown = event => { if (event.key === 'Enter') searchOwners(); };

      const initialOwnerId = Number(new URLSearchParams(window.location.search).get('user_id'));
      if (initialOwnerId) {
        request(`/api/admin/user360/users/${initialOwnerId}`)
          .then(data => renderOwnerDialogs(data.user))
          .catch(error => { ownerResults.innerHTML = `<div class="unavailable">${safe(error.message)}</div>`; });
      }
    }
  }

  requestAnimationFrame(() => {
    const active = nav.querySelector('.is-active');
    active?.scrollIntoView({ block: 'nearest', inline: 'center' });
  });
})();
