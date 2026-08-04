(() => {
  'use strict';

  const observed = new WeakSet();
  const pending = [];
  const active = new Set();
  const MAX_CONCURRENT = 3;

  function cacheKey(image) {
    const dialogId = image.closest('[data-dialog]')?.dataset.dialog;
    return `phantom.avatar.url.${dialogId || image.dataset.avatarSource || image.src}`;
  }

  function applyCachedBackground(image) {
    const holder = image.closest('.avatar');
    if (!holder) return;
    let previous = null;
    try { previous = localStorage.getItem(cacheKey(image)); } catch {}
    if (!previous) return;
    holder.style.backgroundImage = `url("${previous.replace(/"/g, '%22')}")`;
    holder.style.backgroundSize = 'cover';
    holder.style.backgroundPosition = 'center';
  }

  function finish(image) {
    active.delete(image);
    image.dataset.avatarState = 'done';
    pump();
  }

  function load(image) {
    if (!image.isConnected || image.dataset.avatarState === 'loading') return;
    const source = image.dataset.avatarSource;
    if (!source) return;

    image.dataset.avatarState = 'loading';
    active.add(image);
    image.decoding = 'async';
    image.loading = 'eager';
    try { image.fetchPriority = 'auto'; } catch {}

    image.addEventListener('load', () => {
      const holder = image.closest('.avatar');
      if (holder) {
        holder.style.backgroundImage = `url("${source.replace(/"/g, '%22')}")`;
        holder.style.backgroundSize = 'cover';
        holder.style.backgroundPosition = 'center';
      }
      try { localStorage.setItem(cacheKey(image), source); } catch {}
      image.style.opacity = '1';
      finish(image);
    }, {once: true});

    image.addEventListener('error', () => {
      image.style.opacity = '0';
      finish(image);
    }, {once: true});

    image.src = source;
  }

  function pump() {
    while (active.size < MAX_CONCURRENT && pending.length) {
      const image = pending.shift();
      if (!image?.isConnected || image.dataset.avatarState === 'done') continue;
      load(image);
    }
  }

  const intersection = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const image = entry.target;
      intersection.unobserve(image);
      pending.push(image);
    }
    pump();
  }, {rootMargin: '320px 0px'});

  function prepare(image) {
    if (!(image instanceof HTMLImageElement) || observed.has(image)) return;
    const holder = image.closest('.avatar');
    if (!holder) return;

    observed.add(image);
    image.dataset.avatarSource = image.currentSrc || image.getAttribute('src') || '';
    image.removeAttribute('src');
    image.loading = 'lazy';
    image.decoding = 'async';
    image.style.opacity = '0';
    image.style.transition = 'opacity .2s ease';
    applyCachedBackground(image);
    intersection.observe(image);
  }

  function scan(root = document) {
    root.querySelectorAll?.('.avatar img').forEach(prepare);
  }

  const observer = new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (!(node instanceof Element)) continue;
        if (node.matches?.('.avatar img')) prepare(node);
        scan(node);
      }
    }
  });

  observer.observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener('DOMContentLoaded', () => scan());
})();
