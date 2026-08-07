(() => {
  'use strict';

  const app = document.getElementById('app');
  if (!app) return;

  const KEY = 'phantom.workspace.v1';
  const emptyState = {favorites: [], tags: {}, recent: [], bookmarks: []};
  let state = load();
  let activeFilter = 'all';

  function load() {
    try {
      const raw = JSON.parse(localStorage.getItem(KEY) || '{}');
      return {
        favorites: Array.isArray(raw.favorites) ? raw.favorites.map(String) : [],
        tags: raw.tags && typeof raw.tags === 'object' ? raw.tags : {},
        recent: Array.isArray(raw.recent) ? raw.recent : [],
        bookmarks: Array.isArray(raw.bookmarks) ? raw.bookmarks : [],
      };
    } catch {
      return {...emptyState, favorites: [], tags: {}, recent: [], bookmarks: []};
    }
  }

  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch {} }
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const dialogId = card => String(card?.dataset.dialog || '');
  const dialogName = card => card?.querySelector('.name')?.textContent?.trim() || 'Диалог';
  const dialogPreview = card => card?.querySelector('.preview')?.textContent?.trim() || '';
  const count = (card, key) => Number(card?.dataset?.[key] || 0);

  function isFavorite(id) { return state.favorites.includes(String(id)); }
  function toggleFavorite(id) {
    id = String(id);
    state.favorites = isFavorite(id) ? state.favorites.filter(item => item !== id) : [id, ...state.favorites.filter(item => item !== id)];
    save(); decorateDialogs(true);
  }
  function setTag(id) {
    id = String(id); const current = state.tags[id] || '';
    const value = prompt('Тег диалога', current)?.trim();
    if (value === undefined) return;
    if (value) state.tags[id] = value.slice(0, 32); else delete state.tags[id];
    save(); decorateDialogs(true);
  }
  function rememberRecent(card) {
    const id = dialogId(card); if (!id) return;
    const item = {id, name: dialogName(card), preview: dialogPreview(card), at: Date.now()};
    state.recent = [item, ...state.recent.filter(row => String(row.id) !== id)].slice(0, 12); save();
  }

  function cardFlags(card) {
    const text = (card.textContent || '').toLowerCase();
    return {
      favorite: isFavorite(dialogId(card)),
      group: /группа|групповой архив|supergroup/.test(text),
      changed: count(card, 'archiveEdited') > 0,
      deleted: count(card, 'archiveDeleted') > 0,
      media: count(card, 'archiveMedia') > 0,
      protected: count(card, 'archiveProtected') > 0,
    };
  }

  function applyFilter() {
    const cards = [...app.querySelectorAll('.list .dialog[data-dialog]')];
    for (const card of cards) {
      const flags = cardFlags(card);
      card.hidden = activeFilter !== 'all' && !flags[activeFilter];
    }
    const toolbar = app.querySelector('.aw-toolbar');
    toolbar?.querySelectorAll('[data-aw-filter]').forEach(button => button.classList.toggle('active', button.dataset.awFilter === activeFilter));
  }

  function decorateCard(card) {
    const id = dialogId(card); if (!id) return;
    let actions = card.querySelector(':scope > .aw-card-actions');
    if (!actions) {
      actions = document.createElement('span'); actions.className = 'aw-card-actions';
      actions.innerHTML = '<button type="button" class="aw-icon" data-aw-favorite aria-label="Избранное">☆</button><button type="button" class="aw-icon" data-aw-tag aria-label="Добавить тег">#</button>';
      card.appendChild(actions);
      actions.querySelector('[data-aw-favorite]').addEventListener('click', event => { event.preventDefault(); event.stopPropagation(); toggleFavorite(id); });
      actions.querySelector('[data-aw-tag]').addEventListener('click', event => { event.preventDefault(); event.stopPropagation(); setTag(id); });
    }
    const favorite = actions.querySelector('[data-aw-favorite]'); favorite.textContent = isFavorite(id) ? '★' : '☆'; favorite.classList.toggle('active', isFavorite(id));
    let tag = card.querySelector('.aw-tag'); const value = state.tags[id];
    if (value && !tag) { tag = document.createElement('span'); tag.className = 'aw-tag'; card.querySelector('.p2-badges,.dialog-count')?.after(tag); }
    if (tag) { if (value) tag.textContent = `#${value}`; else tag.remove(); }
    card.dataset.awFavorite = isFavorite(id) ? '1' : '0'; card.dataset.awTag = value || '';
  }

  function ensureToolbar(list) {
    let toolbar = app.querySelector('.aw-toolbar'); if (toolbar) return toolbar;
    toolbar = document.createElement('section'); toolbar.className = 'aw-toolbar';
    toolbar.innerHTML = '<div class="aw-toolbar-head"><div><b>Мой архив</b><span>Избранное, теги и быстрые переходы</span></div><button type="button" class="aw-workspace-open">Открыть</button></div><div class="aw-filters"><button data-aw-filter="all">Все</button><button data-aw-filter="favorite">Избранные</button><button data-aw-filter="group">Группы</button><button data-aw-filter="media">Медиа</button><button data-aw-filter="changed">Изменённые</button><button data-aw-filter="deleted">Удалённые</button><button data-aw-filter="protected">Защищённые</button></div>';
    const anchor = app.querySelector('.p2-dialog-summary') || list; anchor.before(toolbar);
    toolbar.querySelector('.aw-filters').addEventListener('click', event => {
      const button = event.target.closest('[data-aw-filter]'); if (!button) return;
      activeFilter = button.dataset.awFilter || 'all'; applyFilter();
    });
    toolbar.querySelector('.aw-workspace-open').addEventListener('click', openWorkspace); return toolbar;
  }

  function decorateDialogs(force = false) {
    const list = app.querySelector('.list'); const cards = list ? [...list.querySelectorAll('.dialog[data-dialog]')] : [];
    if (!list || !cards.length) return;
    cards.forEach(card => { decorateCard(card); if (card.dataset.awRecent !== '1') { card.dataset.awRecent = '1'; card.addEventListener('click', () => rememberRecent(card), {passive:true}); } });
    cards.sort((a,b) => Number(isFavorite(dialogId(b))) - Number(isFavorite(dialogId(a)))); cards.forEach(card => list.appendChild(card));
    ensureToolbar(list); applyFilter(); if (force) renderWorkspace();
  }

  function messageKey(message,index){ return message.dataset.messageId || message.id || `${location.search}:${index}`; }
  function decorateMessages(){
    const messages=[...app.querySelectorAll('.messages .msg')]; if(!messages.length)return;
    messages.forEach((message,index)=>{ const key=messageKey(message,index); if(message.querySelector('.aw-bookmark'))return;
      const button=document.createElement('button'); button.type='button'; button.className='aw-bookmark'; const active=state.bookmarks.some(item=>item.key===key); button.textContent=active?'★':'☆'; button.classList.toggle('active',active); button.setAttribute('aria-label','Закладка сообщения');
      button.addEventListener('click',event=>{ event.preventDefault();event.stopPropagation();const exists=state.bookmarks.some(item=>item.key===key);if(exists)state.bookmarks=state.bookmarks.filter(item=>item.key!==key);else{const text=(message.childNodes[0]?.textContent||message.textContent||'Сообщение').trim().slice(0,180);const title=app.querySelector('.topbar .title')?.textContent?.trim()||'Диалог';state.bookmarks.unshift({key,dialog:location.search,title,text,at:Date.now()});state.bookmarks=state.bookmarks.slice(0,100);}save();button.textContent=exists?'☆':'★';button.classList.toggle('active',!exists);renderWorkspace();}); message.appendChild(button);
    });
  }
  function ensureWorkspace(){ let panel=document.getElementById('aw-workspace');if(panel)return panel;panel=document.createElement('section');panel.id='aw-workspace';panel.className='aw-workspace';panel.hidden=true;panel.innerHTML='<div class="aw-sheet"><header><div><b>Рабочее пространство</b><span>Всё важное из архива</span></div><button type="button" data-aw-close>×</button></header><div class="aw-tabs"><button class="active" data-aw-tab="favorites">Избранное</button><button data-aw-tab="recent">Недавние</button><button data-aw-tab="bookmarks">Закладки</button><button data-aw-tab="tags">Теги</button></div><div class="aw-content"></div></div>';document.body.appendChild(panel);panel.querySelector('[data-aw-close]').addEventListener('click',closeWorkspace);panel.addEventListener('click',event=>{if(event.target===panel)closeWorkspace();});panel.querySelector('.aw-tabs').addEventListener('click',event=>{const button=event.target.closest('[data-aw-tab]');if(!button)return;panel.dataset.tab=button.dataset.awTab;panel.querySelectorAll('[data-aw-tab]').forEach(item=>item.classList.toggle('active',item===button));renderWorkspace();});panel.dataset.tab='favorites';return panel; }
  function openDialog(id){closeWorkspace();const card=app.querySelector(`.dialog[data-dialog="${CSS.escape(String(id))}"]`);if(card)card.click();}
  function renderWorkspace(){const panel=ensureWorkspace(),content=panel.querySelector('.aw-content'),tab=panel.dataset.tab||'favorites';if(tab==='favorites'){const cards=state.favorites.map(id=>{const card=app.querySelector(`.dialog[data-dialog="${CSS.escape(String(id))}"]`);return{id,name:card?dialogName(card):`Диалог ${id}`,preview:card?dialogPreview(card):'',tag:state.tags[id]};});content.innerHTML=cards.length?cards.map(item=>`<button class="aw-row" data-open-dialog="${esc(item.id)}"><b>★ ${esc(item.name)}</b><span>${esc(item.preview||item.tag||'Избранный диалог')}</span></button>`).join(''):'<div class="aw-empty">Добавляйте диалоги звёздочкой — они появятся здесь.</div>';}else if(tab==='recent'){content.innerHTML=state.recent.length?state.recent.map(item=>`<button class="aw-row" data-open-dialog="${esc(item.id)}"><b>${esc(item.name)}</b><span>${esc(item.preview||'Недавно открывался')}</span></button>`).join(''):'<div class="aw-empty">Недавних диалогов пока нет.</div>';}else if(tab==='bookmarks'){content.innerHTML=state.bookmarks.length?state.bookmarks.map(item=>`<button class="aw-row" data-open-bookmark="${esc(item.key)}" data-location="${esc(item.dialog)}"><b>🔖 ${esc(item.title)}</b><span>${esc(item.text)}</span></button>`).join(''):'<div class="aw-empty">Отмечайте важные сообщения звёздочкой.</div>';}else{const entries=Object.entries(state.tags);content.innerHTML=entries.length?entries.map(([id,tag])=>`<button class="aw-row" data-open-dialog="${esc(id)}"><b>#${esc(tag)}</b><span>Открыть отмеченный диалог</span></button>`).join(''):'<div class="aw-empty">Теги помогают разделить работу, клиентов и личные чаты.</div>';}content.querySelectorAll('[data-open-dialog]').forEach(button=>button.addEventListener('click',()=>openDialog(button.dataset.openDialog)));}
  function openWorkspace(){const panel=ensureWorkspace();renderWorkspace();panel.hidden=false;requestAnimationFrame(()=>panel.classList.add('open'));}
  function closeWorkspace(){const panel=document.getElementById('aw-workspace');if(!panel)return;panel.classList.remove('open');setTimeout(()=>{panel.hidden=true;},180);}
  function refresh(){decorateDialogs();decorateMessages();}
  let refreshQueued=false;
  const observer=new MutationObserver(()=>{if(refreshQueued)return;refreshQueued=true;requestAnimationFrame(()=>{refreshQueued=false;refresh();});});observer.observe(app,{childList:true,subtree:true});
  document.addEventListener('archive:metrics-ready',applyFilter);
  document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='b'){event.preventDefault();openWorkspace();}if(event.key==='Escape')closeWorkspace();});refresh();
})();