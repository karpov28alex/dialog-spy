(() => {
  window.__phantomUseCleanLogo = true;
  const LOGO_PARTS=['/app/logo-data/0.txt?v=0.9.2','/app/logo-data/1.txt?v=0.9.2'];
  let cleanLogo='';
  let dialogsCache=null;
  const nativeFetch=window.fetch.bind(window);

  async function loadCleanLogo(){
    if(cleanLogo)return cleanLogo;
    try{
      const parts=await Promise.all(LOGO_PARTS.map(url=>nativeFetch(url,{cache:'force-cache'}).then(r=>r.ok?r.text():'')));
      const encoded=parts.join('').replace(/\s+/g,'');
      if(encoded.length>10000)cleanLogo=`data:image/webp;base64,${encoded}`;
    }catch{}
    return cleanLogo;
  }

  function logoImage(className='ph5-logo'){
    const img=document.createElement('img');
    img.className=className;
    img.src=cleanLogo;
    img.alt='Phantom';
    img.decoding='async';
    img.draggable=false;
    return img;
  }

  window.fetch=async function phantomUi5Fetch(input,options={}){
    const response=await nativeFetch(input,options);
    const url=typeof input==='string'?input:input?.url||'';
    if(response.ok&&/\/api\/dialogs(?:\?|$)/.test(url)){
      try{dialogsCache=await response.clone().json();queueMicrotask(refreshUi);}catch{}
    }
    return response;
  };

  function replaceLogos(){
    if(!cleanLogo)return;
    document.querySelectorAll('.ph4-transition-logo,.ph4-brand-mark,.ph-load-logo').forEach(holder=>{
      const existing=holder.querySelector(':scope > .ph5-logo');
      if(existing)return;
      holder.dataset.cleanLogo='1';
      holder.replaceChildren(logoImage(holder.classList.contains('ph-load-logo')?'ph5-logo ph5-loader-logo':'ph5-logo'));
    });
    document.querySelectorAll('.brand .phantom-logo,.brand>.logo,.ph4-mark').forEach(node=>node.remove());
  }

  function protectionPanel(){
    const panel=document.createElement('section');
    panel.className='ph5-protection';
    panel.innerHTML='<div class="ph5-protection-title">🛡 Ваши данные под защитой</div><div class="ph5-protection-grid"><span><b>🔐</b>Сообщения защищены</span><span><b>👤</b>Доступ только у вас</span><span><b>🙈</b>Приватный архив</span></div>';
    return panel;
  }

  function enhanceHome(){
    const page=document.querySelector('main.page');
    const brand=page?.querySelector(':scope > .brand');
    const grid=page?.querySelector(':scope > .grid');
    if(!page||!brand||!grid||page.dataset.ui5Home==='1')return;
    page.dataset.ui5Home='1';
    brand.after(protectionPanel());
    const cards=[...grid.querySelectorAll('.navcard')];
    cards.forEach((card,index)=>card.classList.add('ph5-main-card',`ph5-card-${index+1}`));
    const recent=document.createElement('section');
    recent.className='ph5-recent';
    recent.innerHTML='<div class="ph5-section-head"><h2>Последние диалоги</h2><button data-go="dialogs">Все</button></div><div class="ph5-recent-list"></div>';
    grid.after(recent);
    renderRecent();
    addBottomNav('home');
  }

  function renderRecent(){
    const host=document.querySelector('.ph5-recent-list');
    if(!host)return;
    const items=dialogsCache?.items?.slice(0,5)||[];
    if(!items.length){host.innerHTML='<div class="ph5-recent-empty">Откройте раздел «Диалоги», чтобы загрузить последние переписки</div>';return;}
    host.innerHTML=items.map(item=>{
      const name=item.peer_name||item.peer_username||'Без имени';
      const initial=(name[0]||'?').toUpperCase();
      const avatar=item.avatar?`<img src="${item.avatar}" alt="" loading="lazy">`:`<span>${initial}</span>`;
      const preview=(item.last_message_deleted?'Удалено: ':item.last_message_edited?'Изменено: ':'')+(item.last_message_text||'Нет сообщений');
      return `<button class="ph5-recent-row" data-dialog="${item.id}"><span class="ph5-recent-avatar">${avatar}</span><span class="ph5-recent-body"><b>${name}</b><small>${preview}</small><i>💬 ${item.message_count||0}${item.last_message_edited?' · ✎':''}${item.last_message_deleted?' · 🗑':''}</i></span><span class="ph5-recent-arrow">›</span></button>`;
    }).join('');
  }

  function addBottomNav(active){
    if(document.querySelector('.ph5-bottom-nav'))return;
    const nav=document.createElement('nav');
    nav.className='ph5-bottom-nav';
    nav.innerHTML=`<button data-go="dialogs" class="${active==='dialogs'?'active':''}"><b>💬</b><span>Диалоги</span></button><button data-go="dialogs"><b>✎</b><span>Изменения</span></button><button data-go="dialogs"><b>🗑</b><span>Удаления</span></button><button data-go="dialogs"><b>▧</b><span>Медиа</span></button><button data-go="profile"><b>⚙</b><span>Настройки</span></button>`;
    document.body.appendChild(nav);
  }

  function enhanceDialogs(){
    if(!document.querySelector('.list [data-dialog]'))return;
    document.body.classList.add('ph5-dialogs-screen');
    addBottomNav('dialogs');
  }

  function cleanStaleNav(){
    if(document.querySelector('main.page .brand')||document.querySelector('.list [data-dialog]'))return;
    document.querySelector('.ph5-bottom-nav')?.remove();
    document.body.classList.remove('ph5-dialogs-screen');
  }

  async function refreshUi(){
    await loadCleanLogo();
    replaceLogos();
    enhanceHome();
    enhanceDialogs();
    cleanStaleNav();
    renderRecent();
  }

  document.addEventListener('DOMContentLoaded',()=>{
    const app=document.querySelector('#app');
    if(app)new MutationObserver(()=>queueMicrotask(refreshUi)).observe(app,{childList:true,subtree:true});
    refreshUi();
  });
})();