(() => {
  'use strict';

  const STYLE_ID = 'phantom-audio-player-style';

  function formatDuration(seconds) {
    if (!Number.isFinite(seconds) || seconds <= 0) return 'Голосовое сообщение';
    const minutes = Math.floor(seconds / 60);
    const rest = Math.floor(seconds % 60);
    return `${minutes}:${String(rest).padStart(2, '0')}`;
  }

  function installStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .pdu-audio-card{
        position:relative!important;
        display:block!important;
        width:min(330px,76vw)!important;
        min-width:250px!important;
        margin-top:8px!important;
        padding:12px!important;
        border:1px solid rgba(177,101,255,.2)!important;
        border-radius:17px!important;
        overflow:visible!important;
        background:linear-gradient(145deg,rgba(75,45,103,.28),rgba(14,11,22,.38))!important;
      }
      .pdu-audio-head{display:flex;align-items:center;gap:9px;margin-bottom:9px;color:#f3eaff;font-size:12px;font-weight:800}
      .pdu-audio-icon{display:grid;place-items:center;width:32px;height:32px;flex:0 0 32px;border-radius:50%;background:linear-gradient(145deg,#8d43e4,#bd62ff);color:#fff;font-size:15px;box-shadow:0 6px 18px rgba(131,55,205,.24)}
      .pdu-audio-copy{min-width:0;display:grid;gap:2px}
      .pdu-audio-title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .pdu-audio-state{color:var(--muted);font-size:10px;font-weight:600}
      .pdu-audio-card audio,
      .pdu-audio-card .media-audio{
        display:block!important;
        visibility:visible!important;
        opacity:1!important;
        position:static!important;
        width:100%!important;
        min-width:0!important;
        height:44px!important;
        max-height:44px!important;
        margin:0!important;
        padding:0!important;
        border:0!important;
        border-radius:12px!important;
        background:transparent!important;
        transform:none!important;
        pointer-events:auto!important;
      }
      .pdu-audio-card .pdu-media-label,
      .pdu-audio-card .pdu-media-open{display:none!important}
      .pdu-audio-error{display:none;margin-top:8px;padding:9px 10px;border-radius:11px;background:rgba(255,79,116,.09);color:#ff9ab0;font-size:11px;line-height:1.35}
      .pdu-audio-card.is-error audio{display:none!important}
      .pdu-audio-card.is-error .pdu-audio-error{display:block}
      .pdu-audio-link{display:inline-block;margin-top:6px;color:#d2a6ff;text-decoration:none;font-weight:800}
      @media(max-width:390px){.pdu-audio-card{width:min(300px,78vw)!important;min-width:225px!important}}
    `;
    document.head.appendChild(style);
  }

  function enhance(audio) {
    if (!(audio instanceof HTMLAudioElement) || audio.dataset.phantomAudio === '1') return;
    audio.dataset.phantomAudio = '1';
    audio.controls = true;
    audio.preload = 'metadata';
    audio.setAttribute('playsinline', '');

    const wrap = audio.closest('.pdu-media-wrap') || audio.parentElement;
    if (!wrap) return;
    wrap.classList.add('pdu-audio-card');
    wrap.querySelectorAll('.pdu-media-label,.pdu-media-open').forEach(node => node.remove());

    const head = document.createElement('div');
    head.className = 'pdu-audio-head';
    head.innerHTML = '<span class="pdu-audio-icon">▶</span><span class="pdu-audio-copy"><span class="pdu-audio-title">Голосовое сообщение</span><span class="pdu-audio-state">Нажмите, чтобы прослушать</span></span>';
    wrap.insertBefore(head, audio);

    const state = head.querySelector('.pdu-audio-state');
    const icon = head.querySelector('.pdu-audio-icon');
    const error = document.createElement('div');
    error.className = 'pdu-audio-error';
    const source = audio.currentSrc || audio.src || '';
    error.innerHTML = `Файл пока недоступен.${source ? `<br><a class="pdu-audio-link" href="${source.replace(/&/g, '&amp;').replace(/"/g, '&quot;')}" target="_blank" rel="noopener">Открыть файл отдельно</a>` : ''}`;
    wrap.appendChild(error);

    const metadataReady = () => {
      wrap.classList.remove('is-error');
      state.textContent = formatDuration(audio.duration);
    };
    audio.addEventListener('loadedmetadata', metadataReady);
    audio.addEventListener('durationchange', metadataReady);
    audio.addEventListener('play', () => {
      document.querySelectorAll('audio').forEach(other => {
        if (other !== audio && !other.paused) other.pause();
      });
      icon.textContent = 'Ⅱ';
      state.textContent = Number.isFinite(audio.duration) ? formatDuration(audio.duration) : 'Воспроизведение';
    });
    audio.addEventListener('pause', () => { icon.textContent = '▶'; });
    audio.addEventListener('ended', () => { icon.textContent = '▶'; });
    audio.addEventListener('error', () => {
      wrap.classList.add('is-error');
      state.textContent = 'Не удалось загрузить';
      icon.textContent = '!';
    });

    if (audio.readyState >= 1) metadataReady();
  }

  function refresh() {
    installStyles();
    document.querySelectorAll('audio.media-audio, .pdu-media-wrap audio, .msg audio').forEach(enhance);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');
    if (app) new MutationObserver(refresh).observe(app, {childList:true, subtree:true});
    refresh();
  });
})();
