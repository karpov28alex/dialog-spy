(() => {
  'use strict';
  const app = document.getElementById('app');
  if (!app) return;

  const text = node => (node?.textContent || '').trim();
  const detail = () => window.__phantomDialogDetail || null;

  function bindStructuredState(messages) {
    const payload = detail();
    const rows = Array.isArray(payload?.messages) ? payload.messages : [];
    if (!rows.length || rows.length !== messages.length) return;
    rows.forEach((item, index) => {
      const message = messages[index];
      if (!message) return;
      message.dataset.msgId = String(item.id ?? '');
      message.dataset.msgEdited = item.edited_at || (item.versions?.length || 0) > 1 ? '1' : '0';
      message.dataset.msgDeleted = item.is_deleted || item.deleted_at ? '1' : '0';
      message.dataset.msgMedia = (item.media?.length || 0) > 0 ? '1' : '0';
      message.dataset.msgProtected = item.media?.some(media => media.is_protected) ? '1' : '0';
    });
  }

  const kindOf = message => {
    if (message?.dataset?.msgId) {
      return {
        media: message.dataset.msgMedia === '1',
        edited: message.dataset.msgEdited === '1',
        deleted: message.dataset.msgDeleted === '1',
        protected: message.dataset.msgProtected === '1',
      };
    }
    const value = text(message).toLowerCase();
    return {
      media: Boolean(message.querySelector('img,video,audio,.media-file,.media-wait')),
      edited: value.includes('изменено') || Boolean(message.querySelector('.history')),
      deleted: message.classList.contains('deleted') || value.includes('удалено'),
      protected: value.includes('защищено') || value.includes('приватн'),
    };
  };

  function decorateGroupHeader(page) {
    const head = page.querySelector('.dialog-head');
    if (!head || head.dataset.p11Group === '1') return;
    const title = text(head.querySelector('b')).toLowerCase();
    const subtitle = text(head.querySelector('.muted')).toLowerCase();
    if (!/группа|group|supergroup|участник/.test(`${title} ${subtitle}`)) return;
    head.dataset.p11Group = '1';
    const label = document.createElement('span');
    label.className = 'p11-group-label';
    label.textContent = '👥 групповой архив';
    head.querySelector('b')?.after(label);
  }

  function overviewCounts(messages) {
    const metrics = detail()?.metrics;
    if (metrics) {
      return {
        total: Number(metrics.message_count || 0),
        media: Number(metrics.media_count || 0),
        edited: Number(metrics.edited_count || 0),
        deleted: Number(metrics.deleted_count || 0),
      };
    }
    return messages.reduce((acc, message) => {
      const flags = kindOf(message);
      acc.total += 1;
      if (flags.media) acc.media += 1;
      if (flags.edited) acc.edited += 1;
      if (flags.deleted) acc.deleted += 1;
      return acc;
    }, {total:0, media:0, edited:0, deleted:0});
  }

  function buildOverview(page, messages) {
    const counts = overviewCounts(messages);
    let overview = page.querySelector('.p11-overview');
    if (!overview) {
      overview = document.createElement('section');
      overview.className = 'p11-overview';
      const head = page.querySelector('.dialog-head');
      head?.after(overview);
    }
    overview.innerHTML = [
      ['Сообщений', counts.total], ['Медиа', counts.media],
      ['Изменено', counts.edited], ['Удалено', counts.deleted],
    ].map(([label,value]) => `<div class="p11-overview-card"><b>${value}</b><span>${label}</span></div>`).join('');
  }

  function applyThreadFilter(page, messages, target) {
    let visible = 0;
    messages.forEach(message => {
      const flags = kindOf(message);
      const show = target === 'all' || Boolean(flags[target]);
      message.classList.toggle('p11-hidden', !show);
      if (show) visible += 1;
    });
    let empty = page.querySelector('.p11-filter-empty');
    if (!empty) {
      empty = document.createElement('div');
      empty.className = 'p11-filter-empty';
      page.querySelector('.messages')?.before(empty);
    }
    if (target !== 'all' && visible === 0) {
      const metrics = detail()?.metrics || {};
      const totals = {
        edited: Number(metrics.edited_count || 0),
        deleted: Number(metrics.deleted_count || 0),
        media: Number(metrics.media_count || 0),
        protected: Number(metrics.protected_media_count || 0),
      };
      empty.textContent = totals[target] > 0
        ? `В архиве есть ${totals[target]} событий этого типа. Они находятся глубже в истории.`
        : 'Событий этого типа в диалоге нет.';
      empty.hidden = false;
    } else {
      empty.hidden = true;
    }
  }

  function buildTabs(page, messages) {
    let tabs = page.querySelector('.p11-tabs');
    if (!tabs) {
      tabs = document.createElement('div');
      tabs.className = 'p11-tabs';
      tabs.innerHTML = '<button class="p11-tab active" data-p11="all">Все</button><button class="p11-tab" data-p11="media">Медиа</button><button class="p11-tab" data-p11="edited">Изменённые</button><button class="p11-tab" data-p11="deleted">Удалённые</button><button class="p11-tab" data-p11="protected">Защищённые</button>';
      const overview = page.querySelector('.p11-overview');
      overview?.after(tabs);
      tabs.addEventListener('click', event => {
        const button = event.target.closest('[data-p11]');
        if (!button) return;
        const target = button.dataset.p11;
        tabs.dataset.active = target;
        tabs.querySelectorAll('.p11-tab').forEach(item => item.classList.toggle('active', item === button));
        applyThreadFilter(page, [...page.querySelectorAll('.messages .msg')], target);
      });
    }
    applyThreadFilter(page, messages, tabs.dataset.active || 'all');
  }

  function buildGallery(page, messages) {
    const existing = page.querySelector('.p11-gallery');
    if (existing) existing.remove();
    const media = [];
    messages.forEach((message, messageIndex) => {
      message.querySelectorAll('img.media-image,video.media-video,audio.media-audio,a.media-file').forEach(node => media.push({node,message,messageIndex}));
    });
    if (!media.length) return;
    const gallery = document.createElement('section');
    gallery.className = 'p11-gallery';
    gallery.innerHTML = `<div class="p11-gallery-head"><b>Медиа диалога</b><span>${detail()?.metrics?.media_count ?? media.length} файлов</span></div><div class="p11-gallery-grid"></div>`;
    const grid = gallery.querySelector('.p11-gallery-grid');
    media.forEach(({node,message}, index) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'p11-gallery-item';
      if (node instanceof HTMLImageElement) item.innerHTML = `<img src="${node.currentSrc || node.src}" alt=""><small>Фото ${index + 1}</small>`;
      else if (node instanceof HTMLVideoElement) item.innerHTML = `<video src="${node.currentSrc || node.src}" muted playsinline preload="metadata"></video><small>Видео ${index + 1}</small>`;
      else if (node instanceof HTMLAudioElement) { item.classList.add('audio'); item.innerHTML = '<span>🎙</span><small>Голосовое</small>'; }
      else { item.classList.add('file'); item.innerHTML = '<span>📎</span><small>Документ</small>'; }
      item.addEventListener('click', () => {
        message.classList.remove('p11-hidden');
        message.scrollIntoView({behavior:'smooth', block:'center'});
        message.classList.remove('p11-message-focus');
        void message.offsetWidth;
        message.classList.add('p11-message-focus');
        if (node instanceof HTMLImageElement) node.click();
      });
      grid.appendChild(item);
    });
    const tabs = page.querySelector('.p11-tabs');
    tabs?.after(gallery);
  }

  function buildTimeline(page, messages) {
    const existing = page.querySelector('.p11-timeline');
    if (existing) existing.remove();
    const events = messages.map((message, index) => ({message,index,flags:kindOf(message),meta:text(message.querySelector('.meta'))}))
      .filter(item => item.flags.edited || item.flags.deleted || item.flags.media)
      .slice(-40);
    if (!events.length) return;
    const timeline = document.createElement('section');
    timeline.className = 'p11-timeline';
    timeline.innerHTML = events.map((event, i) => {
      const type = event.flags.deleted ? 'Удаление' : event.flags.edited ? 'Изменение' : 'Медиа';
      const cls = event.flags.deleted ? 'deleted' : event.flags.media ? 'media' : '';
      return `<button type="button" class="p11-event ${cls}" data-p11-event="${i}"><b>${type}</b><small>${event.meta || `Сообщение ${event.index + 1}`}</small></button>`;
    }).join('');
    timeline.addEventListener('click', event => {
      const button = event.target.closest('[data-p11-event]');
      if (!button) return;
      const target = events[Number(button.dataset.p11Event)]?.message;
      if (!target) return;
      target.classList.remove('p11-hidden');
      target.scrollIntoView({behavior:'smooth', block:'center'});
      target.classList.remove('p11-message-focus');
      void target.offsetWidth;
      target.classList.add('p11-message-focus');
    });
    const gallery = page.querySelector('.p11-gallery');
    (gallery || page.querySelector('.p11-tabs'))?.after(timeline);
  }

  function optimizeMedia(page) {
    if (page.dataset.p11Observer === '1') return;
    page.dataset.p11Observer = '1';
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const media = entry.target;
        if (entry.isIntersecting) {
          media.classList.remove('p11-media-paused');
          if (media.preload === 'none') media.preload = 'metadata';
        } else {
          media.classList.add('p11-media-paused');
          if (!media.paused) { try { media.pause(); } catch {} }
          media.preload = 'none';
        }
      });
    }, {rootMargin:'320px 0px'});
    page.querySelectorAll('video,audio').forEach(media => observer.observe(media));
  }

  function decorateStatus(messages) {
    messages.forEach(message => {
      const flags = kindOf(message);
      let line = message.querySelector('.p11-statusline');
      const meta = message.querySelector('.meta');
      if (!meta) return;
      if (!flags.edited && !flags.deleted && !flags.protected) {
        line?.remove();
        return;
      }
      if (!line) {
        line = document.createElement('div');
        line.className = 'p11-statusline';
        meta.before(line);
      }
      line.innerHTML = (flags.edited ? '<span class="p11-status">✎ изменено</span>' : '')
        + (flags.deleted ? '<span class="p11-status">⌫ удалено</span>' : '')
        + (flags.protected ? '<span class="p11-status good">🔒 защищено</span>' : '');
    });
  }

  function enhance() {
    const page = app.querySelector('.dialog-page');
    const thread = page?.querySelector('.messages');
    if (!page || !thread) return;
    const messages = [...thread.querySelectorAll('.msg')];
    if (!messages.length) return;
    bindStructuredState(messages);
    decorateGroupHeader(page);
    buildOverview(page, messages);
    buildTabs(page, messages);
    buildGallery(page, messages);
    buildTimeline(page, messages);
    decorateStatus(messages);
    optimizeMedia(page);
  }

  let frame = 0;
  const schedule = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(enhance); };
  new MutationObserver(schedule).observe(app, {childList:true, subtree:true});
  document.addEventListener('phantom:dialog-detail', schedule);
  document.addEventListener('DOMContentLoaded', schedule, {once:true});
  schedule();
})();