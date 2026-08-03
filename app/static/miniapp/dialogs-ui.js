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
      .pdu-chevron{position:absolute;right:13px;bottom:13px;color:#a854ff;font-size:21px;line-height:1}
      .pdu-private{display:flex;align-items:center;justify-content:center;gap:7px;margin:14px 0 4px;color:var(--muted);font-size:11px;text-align:center}
      .pdu-private::before{content:'🔐'}
      @media(max-width:430px){.pdu-summary{gap:6px}.pdu-summary-card{padding:11px 5px}.dialog.pdu-card{grid-template-columns:52px minmax(0,1fr) auto!important}.dialog.pdu-card .avatar{width:52px!important;height:52px!important}}
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
    shell.innerHTML = `
      <div class="pdu-summary">
        <div class="pdu-summary-card"><b>${cards.length}</b><span>диалогов</span></div>
        <div class="pdu-summary-card"><b>${edited + deleted}</b><span>изменений</span></div>
        <div class="pdu-summary-card"><b>${media}</b><span>с медиа</span></div>
      </div>
      <div class="pdu-tabs" role="tablist">
        <button class="pdu-tab active" data-pdu-filter="all">Все</button>
        <button class="pdu-tab" data-pdu-filter="edited">Изменённые</button>
        <button class="pdu-tab" data-pdu-filter="deleted">Удалённые</button>
        <button class="pdu-tab" data-pdu-filter="media">Медиа</button>
      </div>`;
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

  function refresh() {
    injectStyles();
    enhanceDialogs();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('app');
    if (app) new MutationObserver(refresh).observe(app, {childList: true, subtree: true});
    refresh();
  });
})();
