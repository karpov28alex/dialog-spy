(() => {
  'use strict';

  const app = document.getElementById('app');
  if (!app) return;

  let lightbox = null;

  function ensureLightbox() {
    if (lightbox) return lightbox;
    lightbox = document.createElement('div');
    lightbox.className = 'p2-lightbox';
    lightbox.innerHTML = '<div class="p2-lightbox-bar"><div class="p2-lightbox-title">Медиа</div><button class="p2-lightbox-close" type="button" aria-label="Закрыть">×</button></div><div class="p2-lightbox-stage"></div>';
    document.body.appendChild(lightbox);
    const close = () => {
      lightbox.classList.remove('visible');
      const stage = lightbox.querySelector('.p2-lightbox-stage');
      stage.querySelectorAll('video,audio').forEach(node => { try { node.pause(); } catch {} });
      setTimeout(() => { if (!lightbox.classList.contains('visible')) stage.replaceChildren(); }, 180);
    };
    lightbox.querySelector('.p2-lightbox-close').addEventListener('click', close);
    lightbox.addEventListener('click', event => { if (event.target === lightbox || event.target.classList.contains('p2-lightbox-stage')) close(); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
    return lightbox;
  }

  function openMedia(source, type) {
    const box = ensureLightbox();
    const stage = box.querySelector('.p2-lightbox-stage');
    const title = box.querySelector('.p2-lightbox-title');
    stage.replaceChildren();
    title.textContent = type === 'video' ? 'Видео' : 'Фото';
    let node;
    if (type === 'video') {
      node = document.createElement('video');
      node.src = source.currentSrc || source.src;
      node.controls = true;
      node.playsInline = true;
      node.autoplay = true;
    } else {
      node = document.createElement('img');
      node.src = source.currentSrc || source.src;
      node.alt = source.alt || 'Фото';
    }
    stage.appendChild(node);
    requestAnimationFrame(() => box.classList.add('visible'));
  }

  function wrapMedia(message, node, kind) {
    if (node.dataset.p2MediaReady === '1') return;
    node.dataset.p2MediaReady = '1';
    const shell = document.createElement('div');
    shell.className = `p2-media-shell ${kind === 'video' ? 'p2-video-shell' : ''}`;
    const label = document.createElement('div');
    label.className = 'p2-media-label';
    label.textContent = kind === 'photo' ? '📷 Фото' : kind === 'video' ? '🎥 Видео' : kind === 'voice' ? '🎙 Голосовое сообщение' : '📎 Файл';
    node.before(shell);
    shell.append(label, node);

    if (kind === 'photo') {
      node.loading = 'eager';
      node.decoding = 'async';
      node.addEventListener('click', () => openMedia(node, 'photo'));
    }
    if (kind === 'video') {
      node.preload = 'metadata';
      node.addEventListener('play', () => shell.classList.add('p2-playing'));
      node.addEventListener('pause', () => shell.classList.remove('p2-playing'));
      node.addEventListener('ended', () => shell.classList.remove('p2-playing'));
      node.addEventListener('dblclick', () => openMedia(node, 'video'));
    }
    if (kind === 'voice') {
      node.preload = 'metadata';
      const state = document.createElement('div');
      state.className = 'p2-voice-state';
      state.textContent = 'Нажмите ▶ для прослушивания';
      shell.appendChild(state);
      node.addEventListener('loadedmetadata', () => {
        if (Number.isFinite(node.duration)) {
          const seconds = Math.max(0, Math.round(node.duration));
          state.textContent = `Длительность ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
        }
      }, {once:true});
      node.addEventListener('play', () => {
        document.querySelectorAll('audio').forEach(other => { if (other !== node) { try { other.pause(); } catch {} } });
        state.textContent = 'Воспроизводится';
        state.classList.remove('p2-voice-error');
      });
      node.addEventListener('pause', () => { if (!node.ended) state.textContent = 'Пауза'; });
      node.addEventListener('ended', () => { state.textContent = 'Прослушано'; });
      node.addEventListener('error', () => {
        state.textContent = 'Файл недоступен или ещё не восстановлен';
        state.classList.add('p2-voice-error');
      });
    }
  }

  function enhanceMessage(message) {
    if (message.dataset.p2MediaEnhanced === '1') return;
    message.dataset.p2MediaEnhanced = '1';
    const meta = (message.querySelector('.meta')?.textContent || '').toLowerCase();
    if (meta.includes('защищено')) message.dataset.p2Protected = '1';
    message.querySelectorAll(':scope > img.media-image').forEach(node => wrapMedia(message, node, 'photo'));
    message.querySelectorAll(':scope > video.media-video').forEach(node => wrapMedia(message, node, 'video'));
    message.querySelectorAll(':scope > audio.media-audio').forEach(node => wrapMedia(message, node, 'voice'));
    message.querySelectorAll(':scope > a.media-file').forEach(node => wrapMedia(message, node, 'file'));
  }

  function refresh() {
    app.querySelectorAll('.messages .msg').forEach(enhanceMessage);
  }

  const observer = new MutationObserver(() => requestAnimationFrame(refresh));
  observer.observe(app, {childList:true, subtree:true});
  document.addEventListener('DOMContentLoaded', refresh, {once:true});
  refresh();
})();