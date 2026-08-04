(() => {
  'use strict';

  const tg = window.Telegram?.WebApp;
  let token = null;
  let timer = 0;
  let controller = null;

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const fmt = value => value ? new Intl.DateTimeFormat('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(value)) : '';
  const icon = item => item.kind === 'dialog' ? '💬' : item.kind === 'version' ? '✏️' : item.kind === 'media' ? ({photo:'🖼',video:'🎬',voice:'🎤',video_note:'⭕',document:'📄',audio:'🎵'}[item.media_type] || '📎') : '✉️';

  async function authenticate() {
    if (token) return token;
    const initData = tg?.initData || '';
    if (!initData) throw new Error('Поиск доступен только внутри Telegram Mini App.');
    const response = await fetch('/api/auth/telegram', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({init_data:initData}),
      cache: 'no-store',
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || 'Не удалось авторизовать поиск');
    token = body.access_token;
    return token;
  }

  const overlay = document.createElement('section');
  overlay.className = 'gs-overlay';
  overlay.setAttribute('aria-hidden','true');
  overlay.innerHTML = '<div class="gs-panel"><div class="gs-head"><button class="gs-back" type="button" aria-label="Закрыть">‹</button><input class="gs-input" type="search" placeholder="Сообщение, имя, файл или старая версия" autocomplete="off"></div><div class="gs-status">Поиск по всему приватному архиву</div><div class="gs-counts" hidden></div><div class="gs-results"><div class="gs-empty">Введите минимум два символа</div></div></div>';
  document.body.appendChild(overlay);

  const launch = document.createElement('button');
  launch.className = 'gs-launch';
  launch.type = 'button';
  launch.setAttribute('aria-label','Глобальный поиск');
  launch.textContent = '⌕';
  document.body.appendChild(launch);

  const input = overlay.querySelector('.gs-input');
  const status = overlay.querySelector('.gs-status');
  const counts = overlay.querySelector('.gs-counts');
  const results = overlay.querySelector('.gs-results');

  function close() {
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden','true');
    controller?.abort();
  }

  function open() {
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden','false');
    requestAnimationFrame(() => input.focus());
    try { tg?.HapticFeedback?.impactOccurred?.('light'); } catch {}
  }

  function openResult(item) {
    close();
    const current = new URL(location.href);
    current.searchParams.set('screen','dialog');
    current.searchParams.set('id',String(item.dialog_id));
    if (item.message_id) current.searchParams.set('message',String(item.message_id));
    else current.searchParams.delete('message');
    location.assign(current.toString());
  }

  function render(data) {
    const c = data.counts || {};
    counts.hidden = false;
    counts.innerHTML = `<span class="gs-count">💬 ${c.dialogs||0} диалогов</span><span class="gs-count">✉️ ${c.messages||0} сообщений</span><span class="gs-count">✏️ ${c.versions||0} версий</span><span class="gs-count">📎 ${c.media||0} медиа</span>`;
    status.textContent = data.items?.length ? `Найдено: ${data.items.length}` : 'Совпадений нет';
    if (!data.items?.length) {
      results.innerHTML = '<div class="gs-empty">Ничего не найдено</div>';
      return;
    }
    results.innerHTML = data.items.map((item,index) => `<button class="gs-item" type="button" data-index="${index}"><span class="gs-icon">${icon(item)}</span><span><div class="gs-title">${esc(item.title)}</div><div class="gs-sub">${esc(item.subtitle)}</div><div class="gs-snippet">${esc(item.snippet||'Открыть результат')}</div><span class="gs-badges">${item.edited?'<span class="gs-badge">изменено</span>':''}${item.deleted?'<span class="gs-badge">удалено</span>':''}${item.media_type?`<span class="gs-badge">${esc(item.media_type)}</span>`:''}</span></span><span class="gs-time">${fmt(item.at)}</span></button>`).join('');
    results.querySelectorAll('[data-index]').forEach(button => button.addEventListener('click', () => openResult(data.items[Number(button.dataset.index)])));
  }

  async function search(query) {
    controller?.abort();
    controller = new AbortController();
    status.textContent = 'Ищу по архиву…';
    counts.hidden = true;
    results.innerHTML = '<div class="gs-empty">Загрузка…</div>';
    try {
      const accessToken = await authenticate();
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=60`, {
        headers:{Authorization:`Bearer ${accessToken}`},
        signal:controller.signal,
        cache:'no-store',
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'Ошибка поиска');
      render(body);
    } catch (error) {
      if (error?.name === 'AbortError') return;
      status.textContent = 'Поиск временно недоступен';
      results.innerHTML = `<div class="gs-error">${esc(error?.message || 'Не удалось выполнить поиск')}</div>`;
    }
  }

  input.addEventListener('input', () => {
    clearTimeout(timer);
    const query = input.value.trim();
    if (query.length < 2) {
      controller?.abort();
      status.textContent = 'Поиск по всему приватному архиву';
      counts.hidden = true;
      results.innerHTML = '<div class="gs-empty">Введите минимум два символа</div>';
      return;
    }
    timer = window.setTimeout(() => search(query), 260);
  });

  launch.addEventListener('click', open);
  overlay.querySelector('.gs-back').addEventListener('click', close);
  overlay.addEventListener('click', event => { if (event.target === overlay) close(); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && overlay.classList.contains('open')) close();
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); open(); }
  });
})();
