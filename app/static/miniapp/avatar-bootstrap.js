(() => {
  'use strict';

  const observed = new WeakSet();
  const queue = [];
  const tasks = new Map();
  const objectUrls = new Map();
  let active = 0;
  const MAX_CONCURRENT = 3;
  const RETRY_DELAY_MS = 3000;

  function identity(image) {
    return image.closest('[data-dialog]')?.dataset.dialog || image.dataset.avatarSource || '';
  }

  function sourceFor(image) {
    return image.dataset.avatarSource || image.currentSrc || image.getAttribute('src') || '';
  }

  function applyToCurrent(identityKey, objectUrl) {
    document.querySelectorAll('.avatar img[data-avatar-key]').forEach(image => {
      if (image.dataset.avatarKey !== identityKey) return;
      const holder = image.closest('.avatar');
      if (!holder) return;
      image.src = objectUrl;
      image.style.opacity = '1';
      holder.style.backgroundImage = `url("${objectUrl}")`;
      holder.style.backgroundSize = 'cover';
      holder.style.backgroundPosition = 'center';
    });
  }

  function retry(job) {
    window.setTimeout(() => {
      if (objectUrls.has(job.key) || tasks.has(job.key)) return;
      queue.push(job);
      tasks.set(job.key, true);
      pump();
    }, RETRY_DELAY_MS);
  }

  async function download(job) {
    try {
      const response = await fetch(job.source, {
        cache: 'no-store',
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error(`avatar HTTP ${response.status}`);
      if (response.headers.get('x-avatar-pending') === '1') {
        throw new Error('avatar pending');
      }
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.startsWith('image/jpeg')) {
        throw new Error(`unexpected avatar type ${contentType}`);
      }
      const blob = await response.blob();
      if (!blob.size) throw new Error('empty avatar');
      const previous = objectUrls.get(job.key);
      if (previous) URL.revokeObjectURL(previous);
      const objectUrl = URL.createObjectURL(blob);
      objectUrls.set(job.key, objectUrl);
      applyToCurrent(job.key, objectUrl);
    } catch {
      retry(job);
    } finally {
      tasks.delete(job.key);
      active -= 1;
      pump();
    }
  }

  function pump() {
    while (active < MAX_CONCURRENT && queue.length) {
      const job = queue.shift();
      if (!job || !job.source || objectUrls.has(job.key)) continue;
      active += 1;
      void download(job);
    }
  }

  function enqueue(image) {
    const key = identity(image);
    const source = sourceFor(image);
    if (!key || !source) return;

    const cached = objectUrls.get(key);
    if (cached) {
      applyToCurrent(key, cached);
      return;
    }
    if (tasks.has(key)) return;
    tasks.set(key, true);
    queue.push({key, source});
    pump();
  }

  const intersection = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      intersection.unobserve(entry.target);
      enqueue(entry.target);
    }
  }, {rootMargin: '700px 0px'});

  function prepare(image) {
    if (!(image instanceof HTMLImageElement) || observed.has(image)) return;
    const holder = image.closest('.avatar');
    if (!holder) return;

    observed.add(image);
    const source = sourceFor(image);
    const key = identity(image);
    image.dataset.avatarSource = source;
    image.dataset.avatarKey = key;
    image.removeAttribute('src');
    image.loading = 'lazy';
    image.decoding = 'async';
    image.style.opacity = '0';
    image.style.transition = 'opacity .2s ease';

    const cached = objectUrls.get(key);
    if (cached) applyToCurrent(key, cached);
    else intersection.observe(image);
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
