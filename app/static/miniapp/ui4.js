(() => {
  const MARK_URL='/app/phantom-mark.svg?v=0.9.0';
  const DETAIL_RE=/\/api\/dialogs\/(\d+)(?:\?|$)/;
  let markText='';
  let lastDetail=null;
  let lastAuthHeaders=null;
  let olderLoading=false;
  let userPinnedToBottom=true;

  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[char]));
  const fmt=value=>value?new Intl.DateTimeFormat('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(value)):'—';

  async function loadMark(){
    if(markText)return markText;
    try{const response=await fetch(MARK_URL,{cache:'force-cache'});if(response.ok)markText=await response.text();}catch{}
    return markText;
  }

  function mark(className='ph4-mark'){
    if(!markText)return '';
    return markText.replace('<svg ','<svg class="'+className+'" ');
  }

  async function upgradeMarks(){
    await loadMark();
    if(!markText)return;
    document.querySelectorAll('.boot').forEach(boot=>{
      if(boot.querySelector('.ph4-transition-logo'))return;
      boot.innerHTML=`<div class="ph4-transition-logo">${mark()}</div>`;
    });
    document.querySelectorAll('.ph-load-logo').forEach(holder=>{
      if(holder.querySelector('.ph4-mark'))return;
      holder.innerHTML=mark();
    });
    document.querySelectorAll('.brand').forEach(brand=>{
      if(!brand.querySelector('.ph4-brand-mark')){
        brand.querySelector('.logo,.phantom-logo')?.remove();
        brand.insertAdjacentHTML('afterbegin',`<div class="ph4-brand-mark">${mark()}</div>`);
      }
      const tagline=[...brand.querySelectorAll('p')].find(node=>/Telegram Business/i.test(node.textContent||''));
      if(tagline)tagline.textContent='Приватный архив переписок';
    });
  }

  const previousFetch=window.fetch.bind(window);
  window.fetch=async function phantomUi4Fetch(input,options={}){
    const raw=typeof input==='string'?input:input?.url||'';
    const match=raw.match(DETAIL_RE);
    if(match&&options?.headers)lastAuthHeaders={...(options.headers||{})};
    const response=await previousFetch(input,options);
    if(match&&response.ok){
      try{const data=await response.clone().json();if(data?.dialog&&Array.isArray(data.messages))lastDetail={dialogId:Number(match[1]),data};}catch{}
    }
    return response;
  };

  function enhanceList(){
    const list=document.querySelector('.list');
    if(!list||list.dataset.ui4==='1'||!document.querySelector('[data-dialog]'))return;
    list.dataset.ui4='1';
    const dialogs=[...list.querySelectorAll('.dialog')];
    const edited=dialogs.filter(item=>/Изменено:/i.test(item.textContent)).length;
    const deleted=dialogs.filter(item=>/Удалено:/i.test(item.textContent)).length;
    const summary=document.createElement('section');
    summary.className='ph4-dialog-summary';
    summary.innerHTML=`<div class="ph4-summary-item"><b>${dialogs.length}</b><small>диалогов</small></div><div class="ph4-summary-item"><b>${edited}</b><small>с правками</small></div><div class="ph4-summary-item"><b>${deleted}</b><small>с удалениями</small></div>`;
    list.before(summary);
    dialogs.forEach(item=>{
      const preview=item.querySelector('.preview');
      const count=item.querySelector('.dialog-count');
      const text=preview?.textContent||'';
      const row=document.createElement('div');row.className='ph4-event-row';
      if(/Изменено:/i.test(text))row.innerHTML+='<span class="ph4-event-pill">✎ изменено</span>';
      if(/Удалено:/i.test(text))row.innerHTML+='<span class="ph4-event-pill deleted">⌫ удалено</span>';
      if(/\[медиа\]|фото|видео|голос/i.test(text))row.innerHTML+='<span class="ph4-event-pill media">▧ медиа</span>';
      row.innerHTML+=`<span class="ph4-event-pill">${esc(count?.textContent||'архив')}</span>`;
      count?.replaceWith(row);
      const direction=document.createElement('span');direction.className='ph4-direction';direction.textContent=/^Вы:/i.test(text)?'исходящее':'архив';item.appendChild(direction);
    });
    const readonly=document.createElement('div');readonly.className='ph4-readonly';readonly.textContent='Переписки доступны только владельцу аккаунта';list.after(readonly);
  }

  function mediaHtml(item){
    if(!item?.url)return `<div class="media-wait">${esc(item?.type||'медиа')} · ${esc(item?.status||'ожидает')}</div>`;
    const url=esc(item.url);
    if(['photo','sticker'].includes(item.type))return `<img class="media-image" src="${url}" alt="${esc(item.type)}" loading="lazy">`;
    if(['video','animation','video_note'].includes(item.type))return `<video class="media-video" src="${url}" controls playsinline preload="metadata"></video>`;
    if(['voice','audio'].includes(item.type))return `<audio class="media-audio" src="${url}" controls preload="metadata"></audio>`;
    return `<a class="media-file" href="${url}" target="_blank" rel="noopener">Скачать ${esc(item.filename||item.type)}</a>`;
  }

  function versionsHtml(message){
    if(!message.edited_at||!message.versions?.length)return '';
    return `<details class="history"><summary>История изменений · ${message.versions.length}</summary>${message.versions.map(version=>`<div class="version"><div class="version-label">Версия ${esc(version.version)} · ${fmt(version.created_at)}</div>${esc(version.text||version.caption||'[медиа]')}</div>`).join('')}</details>`;
  }

  function messageHtml(message){
    return `<article class="msg ${esc(message.direction)} ${message.is_deleted?'deleted':''}" data-message-id="${message.id}"><div>${esc(message.text||message.caption||(!message.media?.length?'Сообщение':''))}</div>${(message.media||[]).map(mediaHtml).join('')}<div class="meta">${fmt(message.sent_at)}${message.edited_at?' · изменено':''}${message.is_deleted?' · удалено':''}</div>${versionsHtml(message)}</article>`;
  }

  function scrollNewest(force=false){
    const messages=document.querySelector('.messages');if(!messages)return;
    if(force||userPinnedToBottom){requestAnimationFrame(()=>window.scrollTo({top:document.documentElement.scrollHeight,behavior:'auto'}));}
  }

  async function loadOlder(button){
    if(olderLoading||!lastDetail?.data?.next_cursor||!lastAuthHeaders)return;
    olderLoading=true;button.disabled=true;button.textContent='Загружаем…';
    const messages=document.querySelector('.messages');const oldHeight=document.documentElement.scrollHeight;
    try{
      const id=lastDetail.dialogId;const cursor=lastDetail.data.next_cursor;
      const response=await previousFetch(`/api/dialogs/${id}?limit=50&before_id=${cursor}`,{headers:lastAuthHeaders,cache:'no-store'});
      if(!response.ok)throw new Error('HTTP '+response.status);
      const data=await response.json();
      const fragment=document.createRange().createContextualFragment((data.messages||[]).map(messageHtml).join(''));
      messages.prepend(fragment);
      lastDetail.data.next_cursor=data.next_cursor;
      button.hidden=!data.next_cursor;button.disabled=false;button.textContent='Показать более ранние сообщения';
      requestAnimationFrame(()=>window.scrollTo(0,document.documentElement.scrollHeight-oldHeight));
    }catch{button.disabled=false;button.textContent='Повторить загрузку';}
    finally{olderLoading=false;}
  }

  function enhanceConversation(){
    const messages=document.querySelector('.messages');
    if(!messages)return;
    if(messages.dataset.ui4!=='1'){
      messages.dataset.ui4='1';
      const older=document.createElement('button');older.className='ph4-older';older.textContent='Показать более ранние сообщения';older.hidden=!lastDetail?.data?.next_cursor;older.onclick=()=>loadOlder(older);messages.before(older);
      const newest=document.createElement('button');newest.className='ph4-newest';newest.textContent='↓ К новым';newest.hidden=true;newest.onclick=()=>{userPinnedToBottom=true;newest.hidden=true;scrollNewest(true)};document.body.appendChild(newest);
      const security=document.createElement('div');security.className='ph4-security-strip';security.innerHTML='<span class="ph4-security-icon">◆</span><span><b>Защищённая переписка</b>Архив доступен только после вашей авторизации</span>';messages.after(security);
      const track=()=>{const distance=document.documentElement.scrollHeight-(window.scrollY+window.innerHeight);userPinnedToBottom=distance<180;newest.hidden=userPinnedToBottom};
      window.addEventListener('scroll',track,{passive:true});
      new MutationObserver(records=>{if(records.some(record=>record.addedNodes.length)){if(userPinnedToBottom)scrollNewest(true);else newest.hidden=false;}}).observe(messages,{childList:true});
      [40,180,520].forEach(delay=>setTimeout(()=>scrollNewest(true),delay));
    }
  }

  function cleanLegacyCopy(){
    document.querySelectorAll('#app p,#app small,#app .sub').forEach(node=>{
      if(/Telegram Business/i.test(node.textContent||''))node.textContent=(node.textContent||'').replace(/Telegram Business/gi,'ассистент в чатах');
    });
  }

  async function refresh(){await upgradeMarks();enhanceList();enhanceConversation();cleanLegacyCopy();}
  document.addEventListener('DOMContentLoaded',()=>{
    const app=document.querySelector('#app');if(app)new MutationObserver(refresh).observe(app,{childList:true,subtree:true});
    refresh();
  });
})();