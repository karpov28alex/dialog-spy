(() => {
  'use strict';

  const app = document.getElementById('app');
  if (!app) return;

  const screenCache = new Map();
  const avatarCache = new Map();
  let snapshotFrame = 0;

  function currentScreen() {
    if (app.querySelector('.messages')) return 'dialog';
    if (app.querySelector('.list .dialog[data-dialog]')) return 'dialogs';
    if (app.querySelector('main.page')) return 'home';
    return null;
  }

  function avatarKey(image) {
    const dialog = image.closest('[data-dialog]');
    if (dialog?.dataset.dialog) return `dialog:${dialog.dataset.dialog}`;
    const head = image.closest('.dialog-head');
    if (head) return `head:${location.search}`;
    return image.currentSrc || image.src || '';
  }

  function rememberAvatar(image) {
    if (!(image instanceof HTMLImageElement)) return;
    const holder = image.closest('.avatar');
    if (!holder) return;

    const key = avatarKey(image);
    const stored = key ? sessionStorage.getItem(`phantom.avatar.${key}`) : null;
    const previous = avatarCache.get(key) || stored;

    if (previous) {
      holder.style.backgroundImage = `url("${previous.replace(/"/g, '%22')}")`;
      holder.style.backgroundSize = 'cover';
      holder.style.backgroundPosition = 'center';
    }

    image.style.opacity = image.complete && image.naturalWidth > 0 ? '1' : '0';
    image.style.transition = 'opacity .12s ease';
    image.loading = 'eager';
    image.decoding = 'async';
    try { image.fetchPriority = 'high'; } catch {}

    const commit = () => {
      if (!image.currentSrc && !image.src) return;
      const source = image.currentSrc || image.src;
      avatarCache.set(key, source);
      try { sessionStorage.setItem(`phantom.avatar.${key}`, source); } catch {}
      holder.style.backgroundImage = `url("${source.replace(/"/g, '%22')}")`;
      holder.style.backgroundSize = 'cover';
      holder.style.backgroundPosition = 'center';
      image.style.opacity = '1';
    };

    if (image.complete && image.naturalWidth > 0) commit();
    else image.addEventListener('load', commit, {once: true});

    image.addEventListener('error', () => {
      image.style.opacity = '0';
      if (!previous) holder.style.backgroundImage = '';
    }, {once: true});
  }

  function stabilizeAvatars(root = app) {
    root.querySelectorAll?.('.avatar img').forEach(rememberAvatar);
  }

  function saveSnapshot() {
    cancelAnimationFrame(snapshotFrame);
    snapshotFrame = requestAnimationFrame(() => {
      const screen = currentScreen();
      if (screen !== 'home' && screen !== 'dialogs') return;
      if (app.querySelector('.boot,.spinner,.error')) return;
      screenCache.set(screen, {
        html: app.innerHTML,
        scrollY: window.scrollY,
        savedAt: Date.now(),
      });
    });
  }

  function stopDialogMedia() {
    app.querySelectorAll('video,audio').forEach(media => {
      try { media.pause(); } catch {}
      media.removeAttribute('autoplay');
      media.preload = 'none';
      media.removeAttribute('src');
      media.querySelectorAll('source').forEach(source => source.removeAttribute('src'));
      try { media.load(); } catch {}
    });

    app.querySelectorAll('.media-image').forEach(image => {
      image.loading = 'lazy';
      image.decoding = 'async';
    });
  }

  document.addEventListener('click', event => {
    if (!event.target.closest?.('[data-back]')) return;
    stopDialogMedia();
  }, true);

  document.addEventListener('click', event => {
    if (!event.target.closest?.('[data-back]')) return;

    queueMicrotask(() => {
      const requested = new URL(location.href).searchParams.get('screen') || 'home';
      const cached = screenCache.get(requested);
      if (!cached || !app.querySelector('.boot,.spinner')) return;

      app.innerHTML = cached.html;
      stabilizeAvatars();
      requestAnimationFrame(() => window.scrollTo(0, cached.scrollY || 0));
    });
  });

  const observer = new MutationObserver(() => {
    stabilizeAvatars();
    saveSnapshot();
  });

  observer.observe(app, {childList: true, subtree: true});
  stabilizeAvatars();
  saveSnapshot();
})();
