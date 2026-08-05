(() => {
  if (document.querySelector('[data-phantom-global-tabs]')) return;

  const items = [
    { label: 'Главная', href: '/admin', match: pathname => pathname === '/admin' },
    { label: 'Пользователи', href: '/admin/user360-mobile.html?v=8', match: pathname => pathname.includes('user360') },
    { label: 'Диалоги', href: '/admin/dialogs-media.html?v=8', match: pathname => pathname.includes('dialog') },
    { label: 'Статистика', href: '/admin/platform.html?v=8', match: pathname => pathname.includes('platform') || pathname.includes('analytics') },
    { label: 'Операции', href: '/admin/operations.html?v=8', match: pathname => pathname.includes('operations') },
    { label: 'Платежи', href: '/admin/billing-mobile.html?v=8', match: pathname => pathname.includes('billing') },
    { label: 'Настройки', href: '/admin/funnel.html?v=8', match: pathname => pathname.includes('funnel') || pathname.includes('settings') },
  ];

  const pathname = window.location.pathname;
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
    if (response.status === 401) {
      window.location.assign('/admin');
      throw new Error('Требуется повторный вход');
    }
    if (!response.ok) throw new Error(data.detail || 'Не удалось выполнить запрос');
    return data;
  };

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

  const searchButton = document.createElement('button');
  searchButton.type = 'button';
  searchButton.className = 'phantom-global-tabs__item';
  searchButton.dataset.globalSearchButton = 'true';
  searchButton.textContent = '⌕ Поиск';
  searchButton.setAttribute('aria-label', 'Глобальный поиск, Ctrl K');

  const logout = document.createElement('button');
  logout.type = 'button';
  logout.className = 'phantom-global-tabs__logout';
  logout.textContent = 'Выйти';
  logout.addEventListener('click', () => {
    sessionStorage.removeItem('adminToken');
    localStorage.removeItem('adminToken');
    window.location.assign('/admin');
  });

  nav.append(scroller, searchButton, logout);
  document.body.prepend(nav);

  const searchStyle = document.createElement('style');
  searchStyle.textContent = `
    .phantom-command{position:fixed;inset:0;z-index:10000;display:none;align-items:flex-start;justify-content:center;padding:calc(env(safe-area-inset-top) + 74px) 14px 20px;background:rgba(3,2,7,.82);backdrop-filter:blur(16px)}
    .phantom-command.is-open{display:flex}.phantom-command__panel{width:min(720px,100%);max-height:min(760px,78dvh);overflow:hidden;border:1px solid #513168;border-radius:20px;background:#100b18;box-shadow:0 30px 100px rgba(0,0,0,.7)}
    .phantom-command__head{display:grid;grid-template-columns:1fr auto;gap:8px;padding:12px;border-bottom:1px solid #342641}.phantom-command__input,.phantom-command__close{min-height:48px;border:1px solid #3b294b;border-radius:13px;background:#09070e;color:#fff;padding:10px 13px;font:inherit}.phantom-command__input{font-size:16px}.phantom-command__body{overflow:auto;max-height:calc(min(760px,78dvh) - 74px);padding:10px}.phantom-command__section{margin:6px 0 12px;color:#c794ff;font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase}.phantom-command__result{display:flex;width:100%;align-items:center;justify-content:space-between;gap:12px;padding:12px;border:1px solid transparent;border-radius:13px;background:transparent;color:#fff;text-align:left;text-decoration:none;font:inherit}.phantom-command__result:hover,.phantom-command__result:focus{border-color:#633b7e;background:rgba(168,76,255,.12);outline:none}.phantom-command__result small{display:block;color:#aa9eb8;margin-top:2px}.phantom-command__badge{white-space:nowrap;border:1px solid #3b294b;border-radius:999px;padding:4px 8px;color:#cbbdd8;font-size:11px}.phantom-command__empty{padding:28px 12px;text-align:center;color:#aa9eb8}.phantom-command__quick{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}@media(max-width:520px){.phantom-command__quick{grid-template-columns:1fr}.phantom-global-tabs [data-global-search-button]{position:sticky;right:0}}
  `;
  document.head.appendChild(searchStyle);

  const command = document.createElement('div');
  command.className = 'phantom-command';
  command.dataset.phantomCommand = 'true';
  command.innerHTML = `
    <section class="phantom-command__panel" role="dialog" aria-modal="true" aria-label="Глобальный поиск">
      <div class="phantom-command__head">
        <input class="phantom-command__input" id="phantomCommandInput" placeholder="Пользователь, Telegram ID, диалог или сообщение" autocomplete="off">
        <button class="phantom-command__close" id="phantomCommandClose">Закрыть</button>
      </div>
      <div class="phantom-command__body" id="phantomCommandBody"></div>
    </section>`;
  document.body.appendChild(command);
  const commandInput = document.getElementById('phantomCommandInput');
  const commandBody = document.getElementById('phantomCommandBody');
  const commandClose = document.getElementById('phantomCommandClose');
  let commandTimer;

  const quickActions = () => `
    <div class="phantom-command__section">Быстрые действия</div>
    <div class="phantom-command__quick">
      <a class="phantom-command__result" href="/admin/user360-mobile.html?v=8"><span><b>Найти владельца</b><small>User360, доступ и история</small></span><span class="phantom-command__badge">Пользователи</span></a>
      <a class="phantom-command__result" href="/admin/dialogs-media.html?v=8"><span><b>Открыть архив</b><small>Диалоги, сообщения и медиа</small></span><span class="phantom-command__badge">Диалоги</span></a>
      <a class="phantom-command__result" href="/admin/billing-mobile.html?v=8"><span><b>Финансовая операция</b><small>Платежи и ручное списание</small></span><span class="phantom-command__badge">Платежи</span></a>
      <a class="phantom-command__result" href="/admin/operations.html?v=8"><span><b>Проверить систему</b><small>Ошибки, очереди и операции</small></span><span class="phantom-command__badge">Система</span></a>
    </div>`;

  const openCommand = () => {
    command.classList.add('is-open');
    commandBody.innerHTML = quickActions();
    commandInput.value = '';
    setTimeout(() => commandInput.focus(), 30);
  };
  const closeCommand = () => command.classList.remove('is-open');
  searchButton.onclick = openCommand;
  commandClose.onclick = closeCommand;
  command.addEventListener('click', event => { if (event.target === command) closeCommand(); });

  const renderCommandResults = (users, dialogs, term) => {
    const userRows = users.map(user => {
      const title = user.username ? `@${user.username}` : (user.name || `Telegram ${user.telegram_id}`);
      return `<a class="phantom-command__result" href="/admin/user360-mobile.html?user_id=${user.id}"><span><b>${safe(title)}</b><small>Telegram ${safe(user.telegram_id)} · ${safe(user.subscription_status || 'без статуса')}</small></span><span class="phantom-command__badge">User360</span></a>`;
    }).join('');
    const dialogRows = dialogs.map(dialog => {
      const owner = dialog.owner_username ? `@${dialog.owner_username}` : (dialog.owner_name || dialog.owner_telegram_id || '—');
      return `<a class="phantom-command__result" href="/admin/dialogs-media.html?user_id=${dialog.owner_user_id}&search=${encodeURIComponent(term)}"><span><b>${safe(dialog.display_name || 'Диалог')}</b><small>Владелец ${safe(owner)} · ${safe(dialog.preview || 'нет текста')}</small></span><span class="phantom-command__badge">${dialog.messages_count} сообщ.</span></a>`;
    }).join('');
    commandBody.innerHTML = `${userRows ? `<div class="phantom-command__section">Владельцы</div>${userRows}` : ''}${dialogRows ? `<div class="phantom-command__section">Диалоги</div>${dialogRows}` : ''}${!userRows && !dialogRows ? '<div class="phantom-command__empty">Ничего не найдено</div>' : ''}`;
  };

  const runCommandSearch = async () => {
    const term = commandInput.value.trim();
    if (term.length < 2) {
      commandBody.innerHTML = quickActions();
      return;
    }
    commandBody.innerHTML = '<div class="phantom-command__empty">Поиск…</div>';
    try {
      const [users, dialogs] = await Promise.all([
        request(`/api/admin/user360/search?q=${encodeURIComponent(term)}&limit=12`),
        request(`/api/admin/dialog-viewer/dialogs?search=${encodeURIComponent(term)}&limit=20`),
      ]);
      renderCommandResults(users.items || [], dialogs.items || [], term);
    } catch (error) {
      commandBody.innerHTML = `<div class="phantom-command__empty">${safe(error.message)}</div>`;
    }
  };
  commandInput.addEventListener('input', () => {
    clearTimeout(commandTimer);
    commandTimer = setTimeout(runCommandSearch, 220);
  });
  commandInput.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeCommand();
    if (event.key === 'Enter') {
      const first = commandBody.querySelector('.phantom-command__result');
      if (first) window.location.assign(first.href);
    }
  });
  document.addEventListener('keydown', event => {
    const target = event.target;
    const typing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target?.isContentEditable;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      openCommand();
    } else if (event.key === '/' && !typing) {
      event.preventDefault();
      openCommand();
    } else if (event.key === 'Escape' && command.classList.contains('is-open')) {
      closeCommand();
    }
  });

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
      ownerPanel.innerHTML = `<strong>Архив владельца</strong><div style="display:grid;grid-template-columns:1fr auto;gap:7px"><input class="input" id="ownerSearch" placeholder="@username, Telegram ID или имя"><button class="btn primary" id="ownerSearchBtn">Выбрать</button></div><div id="ownerResults"></div><div id="selectedOwner"></div>`;
      toolbar.before(ownerPanel);
      const ownerSearch = document.getElementById('ownerSearch');
      const ownerResults = document.getElementById('ownerResults');
      const selectedOwner = document.getElementById('selectedOwner');
      const ownerLabel = owner => owner.username ? `@${owner.username}` : (owner.name || `Telegram ${owner.telegram_id}`);
      const shortDate = value => value ? new Date(value).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }) : '';
      const renderAvatar = (source, name) => source ? `<img class="avatar" src="${safe(source)}" alt="">` : `<span class="avatar">${safe(String(name || '?').replace('@', '').trim().charAt(0).toUpperCase() || '?')}</span>`;
      const syncOwnerUrl = ownerId => {
        const url = new URL(window.location.href);
        if (ownerId) url.searchParams.set('user_id', String(ownerId)); else url.searchParams.delete('user_id');
        window.history.replaceState({}, '', url);
      };
      const renderOwnerDialogs = async owner => {
        const data = await request(`/api/admin/users/${owner.id}/dialogs`);
        selectedOwner.innerHTML = `<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px;border:1px solid var(--line);border-radius:11px"><span><small style="color:var(--muted)">Выбран владелец</small><br><b>${safe(ownerLabel(owner))}</b> · ${data.items.length} диал.</span><span style="display:flex;gap:6px"><a class="btn" href="/admin/user360-mobile.html?user_id=${owner.id}">User360</a><button class="btn" id="clearOwner">Сбросить</button></span></div>`;
        document.getElementById('clearOwner').onclick = () => { syncOwnerUrl(null); selectedOwner.innerHTML = ''; ownerResults.innerHTML = ''; loadDialogs(); };
        const dialogsRoot = document.getElementById('dialogs');
        dialogsRoot.innerHTML = data.items.length ? data.items.map(item => `<button class="dialog" data-dialog="${item.id}">${renderAvatar(item.avatar, item.display_name)}<span class="dialog-content"><span class="dialog-top"><span class="dialog-name">${safe(item.display_name || 'Диалог')}</span><span class="time">${shortDate(item.last_message_at)}</span></span><span class="preview">Только архив ${safe(ownerLabel(owner))}</span><span class="owner">${item.messages_count} сообщ.</span></span></button>`).join('') : '<div class="empty">У владельца пока нет сохранённых диалогов</div>';
        dialogsRoot.querySelectorAll('[data-dialog]').forEach(button => { button.onclick = () => openDialog(Number(button.dataset.dialog), button); });
        syncOwnerUrl(owner.id);
      };
      const searchOwners = async () => {
        const term = ownerSearch.value.trim();
        ownerResults.innerHTML = '<div class="empty" style="padding:10px">Поиск…</div>';
        try {
          const data = await request(`/api/admin/dialog-archive/users?search=${encodeURIComponent(term)}&limit=30`);
          ownerResults.innerHTML = data.items.length ? data.items.map(owner => `<button class="btn" style="width:100%;text-align:left;margin-top:6px" data-owner="${safe(encodeURIComponent(JSON.stringify(owner)))}"><b>${safe(ownerLabel(owner))}</b><br><small>${owner.dialogs_count} диал. · ${owner.messages_count} сообщ.</small></button>`).join('') : '<div class="empty" style="padding:10px">Владелец не найден</div>';
          ownerResults.querySelectorAll('[data-owner]').forEach(button => { button.onclick = () => { const owner = JSON.parse(decodeURIComponent(button.dataset.owner)); ownerResults.innerHTML = ''; renderOwnerDialogs(owner).catch(error => { ownerResults.textContent = error.message; }); }; });
        } catch (error) { ownerResults.innerHTML = `<div class="unavailable">${safe(error.message)}</div>`; }
      };
      document.getElementById('ownerSearchBtn').onclick = searchOwners;
      ownerSearch.onkeydown = event => { if (event.key === 'Enter') searchOwners(); };
      const initialOwnerId = Number(new URLSearchParams(window.location.search).get('user_id'));
      if (initialOwnerId) request(`/api/admin/user360/users/${initialOwnerId}`).then(data => renderOwnerDialogs(data.user)).catch(error => { ownerResults.innerHTML = `<div class="unavailable">${safe(error.message)}</div>`; });
    }
  }

  requestAnimationFrame(() => {
    const active = nav.querySelector('.is-active');
    active?.scrollIntoView({ block: 'nearest', inline: 'center' });
  });
})();
