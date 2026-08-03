(() => {
  'use strict';

  const seen = new WeakSet();

  function promote(image) {
    if (!(image instanceof HTMLImageElement) || seen.has(image)) return;
    const holder = image.closest('.avatar');
    if (!holder) return;
    seen.add(image);

    image.loading = 'eager';
    image.decoding = 'async';
    try { image.fetchPriority = 'high'; } catch {}

    const source = image.currentSrc || image.src;
    if (!source) return;

    const key = `phantom.avatar.url.${image.closest('[data-dialog]')?.dataset.dialog || source}`;
    let previous = null;
    try { previous = localStorage.getItem(key); } catch {}
    if (previous) {
      holder.style.backgroundImage = `url("${previous.replace(/"/g, '%22')}")`;
      holder.style.backgroundSize = 'cover';
      holder.style.backgroundPosition = 'center';
    }

    const probe = new Image();
    probe.decoding = 'async';
    try { probe.fetchPriority = 'high'; } catch {}
    probe.onload = () => {
      if (!image.isConnected) return;
      image.src = source;
      image.style.opacity = '1';
      holder.style.backgroundImage = `url("${source.replace(/"/g, '%22')}")`;
      try { localStorage.setItem(key, source); } catch {}
    };
    probe.onerror = () => {
      if (previous) image.style.opacity = '0';
    };
    probe.src = source;
  }

  function scan(root = document) {
    root.querySelectorAll?.('.avatar img').forEach(promote);
  }

  const observer = new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (!(node instanceof Element)) continue;
        if (node.matches?.('.avatar img')) promote(node);
        scan(node);
      }
    }
  });

  observer.observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener('DOMContentLoaded', () => scan());
})();
