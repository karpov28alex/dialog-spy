(() => {
  'use strict';

  const app = document.getElementById('app');
  if (!app) return;

  const snapshots = new Map();
  let lastMessageCount = 0;
  let lastScreen = '';
  let restoreTimer = 0;

  function screenKey() {
    const url = new URL(location.href);
    const screen = url.searchParams.get('screen') || 'home';
    const id = url.searchParams.get('id') || '';
    return `${screen}:${id}`;
  }

  function isStable() {
    return !app.querySelector('.boot,.spinner,.error') && Boolean(app.querySelector('main.page,.topbar'));
  }

  function saveSnapshot() {
    if (!isStable()) return;
    const key = screenKey();
    snapshots.set(key, {
      html: app.innerHTML,
      scrollY: window.scrollY,
      savedAt: Date.now(),
    });
    if (snapshots.size > 8) snapshots.delete(snapshots.keys().next().value);
  }

  function stopMedia() {
    app.querySelectorAll('audio,video').forEach(media => {
      try { media.pause(); } catch {}
      media.removeAttribute('autoplay');
    });
  }

  function restoreSoon() {
    clearTimeout(restoreTimer);
    restoreTimer = setTimeout(() => {
      const cached = snapshots.get(screenKey());
      if (!cached || Date.now() - cached.savedAt > 120000) return;
      if (!app.querySelector('.boot,.spinner,.p3-screen-placeholder')) return;
      app.innerHTML = cached.html;
      app.firstElementChild?.classList?.add('p3-restored');
      requestAnimationFrame(() => window.scrollTo(0, cached.scrollY || 0));
    }, 0);
  }

  function ensureSyncBadge() {
    let badge = document.querySelector('.p3-sync');
    if (!badge) {
      badge = document.createElement('div');
      badge.className = 'p3-sync';
      badge.innerHTML = '<i></i><span>Обновление</span>';
      document.body.appendChild(badge);
    }
    return badge;
  }

  function ensureNewMarker(thread) {
    let marker = thread.parentElement?.querySelector('.p3-new-marker');
    if (!marker) {
      marker = document.createElement('button');
      marker.type = 'button';
      marker.className = 'p3-new-marker';
      marker.textContent = 'Новые сообщения ↓';
      thread.after(marker);
      marker.addEventListener('click', () => {
        window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'smooth'});
        marker.classList.remove('visible');
      });
    }
    return marker;
  }

  function trackMessages() {
    const thread = app.querySelector('.messages');
    if (!thread) {
      lastMessageCount = 0;
      return;
    }
    const messages = thread.querySelectorAll('.msg');
    const count = messages.length;
    const marker = ensureNewMarker(thread);
    const distance = document.documentElement.scrollHeight - (window.scrollY + window.innerHeight);
    if (lastMessageCount && count > lastMessageCount && distance > 220) {
      const delta = count - lastMessageCount;
      marker.textContent = `${delta === 1 ? 'Новое сообщение' : `Новых сообщений: ${delta}`} ↓`;
      marker.classList.add('visible');
    }
    if (distance < 100) marker.classList.remove('visible');
    lastMessageCount = count;
  }

  function onMutation() {
    const key = screenKey();
    if (key !== lastScreen) {
      lastScreen = key;
      lastMessageCount = 0;
    }
    saveSnapshot();
    trackMessages();
  }

  document.addEventListener('click', event => {
    const target = event.target.closest('[data-back],[data-dialog],[data-go]');
    if (!target) return;
    saveSnapshot();
    if (target.matches('[data-back]')) stopMedia();
    const badge = ensureSyncBadge();
    badge.classList.add('visible');
    setTimeout(() => badge.classList.remove('visible'), 800);
    queueMicrotask(restoreSoon);
  }, {passive: true});

  window.addEventListener('popstate', () => {
    stopMedia();
    restoreSoon();
  });

  window.addEventListener('scroll', () => {
    const marker = app.querySelector('.p3-new-marker');
    if (!marker) return;
    const distance = document.documentElement.scrollHeight - (window.scrollY + window.innerHeight);
    if (distance < 100) marker.classList.remove('visible');
  }, {passive: true});

  const observer = new MutationObserver(() => requestAnimationFrame(onMutation));
  observer.observe(app, {childList: true, subtree: true});
  onMutation();
})();
