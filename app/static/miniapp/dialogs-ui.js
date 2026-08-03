(() => {
  'use strict';

  const STYLE_ID = 'phantom-dialogs-ui-style';
  const AVATAR_KEY = 'phantom.dialog.avatar.';

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .pdu-shell{display:grid;gap:12px;margin-bottom:14px}
      .pdu-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
      .pdu-summary-card{padding:13px 8px;border:1px solid rgba(166,83,255,.22);border-radius:18px;background:linear-gradient(145deg,rgba(38,25,55,.92),rgba(15,11,25,.96));text-align:center;box-shadow:inset 0 0 24px rgba(139,54,255,.035)}
      .pdu-summary-card b{display:block;font-size:22px;line-height:1.1;color:var(--text)}
      .pdu-summary-card span{display:block;margin-top:5px;color:var(--muted);font-size:10px;font-weight:700}
      .pdu-tabs{display:flex;gap:7px;overflow-x:auto;padding-bottom:2px;scrollbar-width:none}
      .pdu-tabs::-webkit-scrollbar{display:none}
      .pdu-tab{flex:0 0 auto;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--muted);padding:9px 13px;font-size:12px;font-weight:800}
      .pdu-tab.active{border-color:rgba(170,75,255,.62);background:linear-gradient(135deg,#7131d9,#a947ff);color:#fff;box-shadow:0 8px 24px rgba(133,46,222,.24)}
      .dialog.pdu-card{position:relative;grid-template-columns:58px minmax(0,1fr) auto!important;gap:12px!important;min-height:102px;padding:15px!important;border-radius:22px!important;background:linear-gradient(145deg,rgba(27,20,41,.98),rgba(16,12,26,.98))!important;transition:transform .16s ease,border-color .16s ease,opacity .16s ease}
      .dialog.pdu-card:active{transform:scale(.988)}
      .dialog.pdu-card[hidden]{display:none!important}
      .dialog.pdu-card .avatar{width:58px!important;height:58px!important;border-radius:50%;overflow:hidden;box-shadow:0 0 0 3px rgba(153,69,255,.12)}
      .dialog.pdu-card .avatar img{width:100%;height:100%;object-fit:cover;display:block}
      .dialog.pdu-card .name{font-size:16px!important;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:8px}
      .dialog.pdu-card .preview{margin-top:4px;max-width:54vw;font-size:13px!important;line-height:1.35;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .dialog.pdu-card .time{font-size:10px!important;color:var(--muted);white-space:nowrap;align-self:start;padding-top:2px}
      .pdu-meta{display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-top:9px}
      .pdu-chip{display:inline-flex;align-items:center;gap:4px;padding:4px 7px;border-radius:999px;border:1px solid rgba(160,82,255,.2);background:rgba(147,65,241,.08);color:#caa7f2;font-size:9px;font-weight:800;line-height:1}
      .pdu-chip.edit{border-color:rgba(178,105,255,.26);color:#c99aff}
      .pdu-chip.delete{border-color:rgba(255,86,125,.28);background:rgba(255,71,111,.08);color:#ff91aa}
      .pdu-chip.media{border-color:rgba(77,151,255,.28);background:rgba(62,132,241,.08);color:#8fc0ff}
      .pdu-chevron{position:absolute;right:13px;bottom:13px;color:#a854ff;font-size:21px;line-height:1;pointer-events:none}
      .pdu-private{display:flex;align-items:center;justify-content:center;gap:7px;margin:14px 0 4px;color:var(--muted);font-size:11px;text-align:center}
      .pdu-private::before{content:'🔐'}

      .dialog-page{padding-bottom:34px!important}
      .dialog-head{position:sticky;top:calc(var(--safe-top,0px) + 70px);z-index:8;padding:12px 14px!important;border:1px solid rgba(162,75,255,.18);border-radius:20px;background:rgba(18,13,29,.88);backdrop-filter:blur(18px);box-shadow:0 12px 30px rgba(0,0,0,.22)}
      .messages.pdu-thread{display:flex!important;flex-direction:column;gap:7px;padding-top:14px}
      .msg.pdu-message{position:relative;max-width:88%;margin:0!important;padding:11px 13px 9px!important;border:1px solid rgba(255,255,255,.06)!important;border-radius:18px!important;background:linear-gradient(145deg,rgba(34,26,47,.98),rgba(24,18,35,.98))!important;box-shadow:0 7px 20px rgba(0,0,0,.14);overflow:hidden}
      .msg.pdu-message.incoming{align-self:flex-start;border-bottom-left-radius:7px!important}
      .msg.pdu-message.outgoing{align-self:flex-end;border-bottom-right-radius:7px!important;background:linear-gradient(145deg,rgba(86,43,136,.96),rgba(54,31,91,.98))!important}
      .msg.pdu-message.deleted{border-color:rgba(255,84,123,.24)!important;background:linear-gradient(145deg,rgba(69,28,43,.9),rgba(35,18,28,.98))!important}
      .pdu-message-status{display:flex;align-items:center;gap:6px;margin:-2px 0 8px;font-size:10px;font-weight:850;letter-spacing:.01em}
      .pdu-message-status.edited{color:#c897ff}
      .pdu-message-status.deleted{color:#ff8eaa}
      .pdu-message-status.protected{color:#8dc2ff}
      .msg.pdu-message .meta{margin-top:7px!important;font-size:9px!important;opacity:.72;text-align:right}
      .pdu-day{align-self:center;position:sticky;top:126px;z-index:5;margin:12px 0 5px;padding:6px 11px;border:1px solid rgba(170,91,255,.18);border-radius:999px;background:rgba(18,13,28,.82);backdrop-filter:blur(12px);color:#cdb7df;font-size:10px;font-weight:850;box-shadow:0 6px 18px rgba(0,0,0,.18)}
      .msg.pdu-message .history{margin-top:9px;border-top:1px solid rgba(255,255,255,.08);padding-top:8px}
      .msg.pdu-message .history summary{cursor:pointer;color:#c69af2;font-size:11px;font-weight:850;list-style:none}
      .msg.pdu-message .history summary::-webkit-details-marker{display:none}
      .msg.pdu-message .history summary::after{content:'⌄';float:right}
      .msg.pdu-message .history[open] summary::after{content:'⌃'}
      .msg.pdu-message .version{margin-top:7px;padding:9px 10px;border-radius:12px;background:rgba(0,0,0,.18);font-size:12px;line-height:1.38}
      .msg.pdu-message .version-label{margin-bottom:4px;color:#b69bc9;font-size:9px;font-weight:800}
      .pdu-media-wrap{position:relative;margin-top:8px;border-radius:15px;overflow:hidden;background:rgba(0,0,0,.2)}
      .pdu-media-wrap img,.pdu-media-wrap video{display:block;width:100%;max-height:58vh;object-fit:cover;border-radius:15px}
      .pdu-media-wrap audio{width:100%;display:block;padding:6px}
      .pdu-media-open{position:absolute;right:8px;top:8px;width:34px;height:34px;border:1px solid rgba(255,255,255,.18);border-radius:50%;background:rgba(9,7,14,.68);color:#fff;font-size:17px;backdrop-filter:blur(10px)}
      .pdu-media-label{position:absolute;left:8px;bottom:8px;padding:5px 8px;border-radius:999px;background:rgba(9,7,14,.7);color:#fff;font-size:9px;font-weight:800;backdrop-filter:blur(10px)}
      .media-file{display:flex!important;align-items:center;gap:9px;margin-top:8px;padding:12px 13px!important;border-radius:14px!important;background:rgba(119,63,184,.13)!important;border:1px solid rgba(165,86,255,.18)!important;color:#d9baff!important;text-decoration:none!important}
      .media-wait{margin-top:8px;padding:12px;border-radius:14px;background:rgba(255,255,255,.035);border:1px dashed rgba(255,255,255,.12);color:var(--muted);font-size:11px}
      .pdu-jump-latest{position:fixed;right:16px;bottom:calc(var(--safe-bottom,0px) + 18px);z-index:30;display:none;width:44px;height:44px;border:1px solid rgba(178,94,255,.36);border-radius:50%;background:linear-gradient(145deg,#7130cf,#9c47ef);color:#fff;font-size:21px;box-shadow:0 10px 28px rgba(96,33,164,.34)}
      .pdu-jump-latest.visible{display:grid;place-items:center}
      .pdu-lightbox{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;padding:18px;background:rgba(4,3,8,.95);backdrop-filter:blur(18px)}
      .pdu-lightbox[hidden]{display:none}
      .pdu-lightbox-content{max-width:100%;max-height:88vh}
      .pdu-lightbox-content img,.pdu-lightbox-content video{display:block;max-width:100%;max-height:88vh;border-radius:16px;object-fit:contain}
      .pdu-lightbox-close{position:absolute;right:14px;top:calc(var(--safe-top,0px) + 14px);width:42px;height:42px;border:1px solid rgba(255,255,255,.16);border-radius:50%;background:rgba(22,17,31,.82);color:#fff;font-size:26px}
      @media(max-width:430px){.pdu-summary{gap:6px}.pdu-summary-card{padding:11px 5px}.dialog.pdu-card{grid-template-columns:52px minmax(0,1fr) auto!important}.dialog.pdu-card .avatar{width:52px!important;height:52px!important}.msg.pdu-message{max-width:92%}}
    `;
    document.head.appendChild(style);
  }

  function classify(card) {
    const preview = card.querySelector('.preview')?.textContent || '';
    const text = card.textContent || '';
    return {
      edited: /изменено:/i.test(preview),
      deleted: /удалено:/i.test(preview),
      media: /\[медиа\]|фото|видео|голос|кружок|документ|стикер/i.test(text),
    };
  }

  function stabilizeAvatar(card) {
    const id = card.dataset.dialog;
    const image = card.querySelector('.avatar img');
    if (!id || !image) return;
    const key = AVATAR_KEY + id;
    const cached = sessionStorage.getItem(key);
    if (image.src) sessionStorage.setItem(key, image.src);
    if (!image.complete && cached && image.src !== cached) image.src = cached;
    image.addEventListener('error', () => {
      const fallback = sessionStorage.getItem(key);
      if (fallback && image.src !== fallback) image.src = fallback;
    }, {once: true});
  }

  function decorateCard(card) {
    if (card.dataset.pdu === '1') return;
    card.dataset.pdu = '1';
    card.classList.add('pdu-card');
    stabilizeAvatar(card);
    const flags = classify(card);
    card.dataset.pduEdited = flags.edited ? '1' : '0';
    card.dataset.pduDeleted = flags.deleted ? '1' : '0';
    card.dataset.pduMedia = flags.media ? '1' : '0';
    const count = card.querySelector('.dialog-count');
    const meta = document.createElement('div');
    meta.className = 'pdu-meta';
    meta.innerHTML = `<span class="pdu-chip">💬 ${count?.textContent?.replace(/\s*сообщени.*$/i, '') || 'архив'}</span>`
      + (flags.edited ? '<span class="pdu-chip edit">✎ правка</span>' : '')
      + (flags.deleted ? '<span class="pdu-chip delete">⌫ удалено</span>' : '')
      + (flags.media ? '<span class="pdu-chip media">▧ медиа</span>' : '');
    count?.replaceWith(meta);
    const chevron = document.createElement('span');
    chevron.className = 'pdu-chevron';
    chevron.textContent = '›';
    card.appendChild(chevron);
  }

  function applyFilter(list, filter) {
    list.querySelectorAll('.dialog[data-dialog]').forEach(card => {
      const visible = filter === 'all'
        || (filter === 'edited' && card.dataset.pduEdited === '1')
        || (filter === 'deleted' && card.dataset.pduDeleted === '1')
        || (filter === 'media' && card.dataset.pduMedia === '1');
      card.hidden = !visible;
    });
  }

  function enhanceDialogs() {
    const list = document.querySelector('.list');
    const cards = list ? [...list.querySelectorAll('.dialog[data-dialog]')] : [];
    if (!list || !cards.length) return;
    cards.forEach(decorateCard);
    if (list.dataset.pduShell === '1') return;
    list.dataset.pduShell = '1';
    const edited = cards.filter(card => card.dataset.pduEdited === '1').length;
    const deleted = cards.filter(card => card.dataset.pduDeleted === '1').length;
    const media = cards.filter(card => card.dataset.pduMedia === '1').length;
    const shell = document.createElement('section');
    shell.className = 'pdu-shell';
    shell.innerHTML = `<div class="pdu-summary"><div class="pdu-summary-card"><b>${cards.length}</b><span>диалогов</span></div><div class="pdu-summary-card"><b>${edited + deleted}</b><span>изменений</span></div><div class="pdu-summary-card"><b>${media}</b><span>с медиа</span></div></div><div class="pdu-tabs" role="tablist"><button class="pdu-tab active" data-pdu-filter="all">Все</button><button class="pdu-tab" data-pdu-filter="edited">Изменённые</button><button class="pdu-tab" data-pdu-filter="deleted">Удалённые</button><button class="pdu-tab" data-pdu-filter="media">Медиа</button></div>`;
    list.before(shell);
    shell.addEventListener('click', event => {
      const button = event.target.closest('[data-pdu-filter]');
      if (!button) return;
      shell.querySelectorAll('.pdu-tab').forEach(item => item.classList.toggle('active', item === button));
      applyFilter(list, button.dataset.pduFilter);
      try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light'); } catch {}
    });
    const privacy = document.createElement('div');
    privacy.className = 'pdu-private';
    privacy.textContent = 'Архив доступен только владельцу аккаунта';
    list.after(privacy);
  }

  function getMessageDate(message) {
    const text = message.querySelector('.meta')?.textContent || '';
    return text.match(/\b\d{2}\.\d{2}\.\d{4}\b/)?.[0] || '';
  }

  function addStatus(message) {
    if (message.querySelector('.pdu-message-status')) return;
    const meta = message.querySelector('.meta')?.textContent || '';
    let label = '';
    let type = '';
    if (message.classList.contains('deleted') || /удалено/i.test(meta)) { label = '⌫ Сообщение удалено собеседником'; type = 'deleted'; }
    else if (/изменено/i.test(meta)) { label = '✎ Сообщение изменено'; type = 'edited'; }
    else if (/защищено/i.test(meta)) { label = '🔐 Сохранено в приватном архиве'; type = 'protected'; }
    if (!label) return;
    const status = document.createElement('div');
    status.className = `pdu-message-status ${type}`;
    status.textContent = label;
    message.prepend(status);
  }

  function openLightbox(media) {
    let box = document.querySelector('.pdu-lightbox');
    if (!box) {
      box = document.createElement('div');
      box.className = 'pdu-lightbox';
      box.hidden = true;
      box.innerHTML = '<button class="pdu-lightbox-close" type="button" aria-label="Закрыть">×</button><div class="pdu-lightbox-content"></div>';
      document.body.appendChild(box);
      const close = () => {
        box.querySelectorAll('video,audio').forEach(item => { try { item.pause(); } catch {} });
        box.hidden = true;
        box.querySelector('.pdu-lightbox-content').replaceChildren();
      };
      box.querySelector('.pdu-lightbox-close').addEventListener('click', close);
      box.addEventListener('click', event => { if (event.target === box) close(); });
    }
    const clone = media.cloneNode(true);
    clone.removeAttribute('loading');
    if (clone instanceof HTMLVideoElement) { clone.controls = true; clone.autoplay = true; }
    box.querySelector('.pdu-lightbox-content').replaceChildren(clone);
    box.hidden = false;
  }

  function decorateMedia(message) {
    message.querySelectorAll('.media-image,.media-video,.media-audio').forEach(media => {
      if (media.closest('.pdu-media-wrap')) return;
      const wrap = document.createElement('div');
      wrap.className = 'pdu-media-wrap';
      media.parentNode.insertBefore(wrap, media);
      wrap.appendChild(media);
      const label = document.createElement('span');
      label.className = 'pdu-media-label';
      label.textContent = media.matches('img') ? 'Фото' : media.matches('video') ? 'Видео' : 'Аудио';
      wrap.appendChild(label);
      if (!media.matches('audio')) {
        const open = document.createElement('button');
        open.type = 'button';
        open.className = 'pdu-media-open';
        open.textContent = '↗';
        open.addEventListener('click', event => { event.stopPropagation(); openLightbox(media); });
        wrap.appendChild(open);
      }
    });
  }

  function enhanceThread() {
    const messages = document.querySelector('.messages');
    if (!messages || messages.dataset.pduThread === '1') return;
    messages.dataset.pduThread = '1';
    messages.classList.add('pdu-thread');
    let lastDate = '';
    [...messages.querySelectorAll('.msg')].forEach(message => {
      const date = getMessageDate(message);
      if (date && date !== lastDate) {
        const separator = document.createElement('div');
        separator.className = 'pdu-day';
        separator.textContent = date;
        messages.insertBefore(separator, message);
        lastDate = date;
      }
      message.classList.add('pdu-message');
      addStatus(message);
      decorateMedia(message);
    });
    const jump = document.createElement('button');
    jump.type = 'button';
    jump.className = 'pdu-jump-latest';
    jump.textContent = '↓';
    jump.setAttribute('aria-label', 'К новым сообщениям');
    document.body.appendChild(jump);
    const sync = () => jump.classList.toggle('visible', document.documentElement.scrollHeight - (window.scrollY + window.innerHeight) > 520);
    jump.addEventListener('click', () => window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'smooth'}));
    window.addEventListener('scroll', sync, {passive: true});
    sync();
  }

  function refresh() {
    injectStyles();
    enhanceDialogs();
    enhanceThread();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');
    if (app) new MutationObserver(refresh).observe(app, {childList: true, subtree: true});
    refresh();
  });
})();
