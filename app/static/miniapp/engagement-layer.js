(() => {
  'use strict';

  const PRODUCT_MARKER = 'PHANTOM PULSE';
  void PRODUCT_MARKER;
  const app = document.getElementById('app');
  const tg = window.Telegram?.WebApp;
  if (!app || !tg?.initData) return;

  const CACHE_KEY = 'phantom:intelligence:v0194';
  const CACHE_TTL = 6 * 60 * 60 * 1000;
  const REQUEST_TIMEOUT = 8000;
  let token = null;
  let loading = false;
  let mounted = false;
  let lastSignature = '';
  let activePeriod = 'today';
  let cachedData = null;

  async function auth(force = false) {
    if (token && !force) return token;
    const response = await fetch('/api/auth/telegram', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({init_data: tg.initData}),
      cache: 'no-store',
    });
    if (!response.ok) throw new Error(`auth:${response.status}`);
    token = (await response.json()).access_token;
    return token;
  }

  async function api(path, retryAuth = true) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    try {
      const bearer = await auth();
      const response = await fetch(path, {
        headers: {Authorization: `Bearer ${bearer}`},
        cache: 'no-store',
        signal: controller.signal,
      });
      if (response.status === 401 && retryAuth) {
        token = null;
        await auth(true);
        return api(path, false);
      }
      if (!response.ok) throw new Error(`api:${response.status}`);
      return response.json();
    } finally {
      clearTimeout(timer);
    }
  }

  function readCache() {
    try {
      const item = JSON.parse(localStorage.getItem(CACHE_KEY) || 'null');
      if (!item?.data || !item?.savedAt) return null;
      if (Date.now() - Number(item.savedAt) > CACHE_TTL) return null;
      return item.data;
    } catch {
      return null;
    }
  }

  function writeCache(data) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({savedAt: Date.now(), data}));
    } catch {}
  }

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const num = value => Number(value || 0);
  function isHome(){return Boolean(app.querySelector('.brand')&&app.querySelector('.navcard[data-go="dialogs"]'));}
  function activityRows(data){return Array.isArray(data?.activity)?data.activity:[];}
  function signalRows(data){return Array.isArray(data?.signals)?data.signals:[];}

  function streak(rows){let total=0;for(let index=rows.length-1;index>=0;index-=1){if(num(rows[index]?.messages)<=0)break;total+=1;}return total;}

  function aggregate(data,period){
    const rows=activityRows(data);const selected=period==='today'?rows.slice(-1):rows.slice(-7);
    return selected.reduce((acc,row)=>{acc.messages+=num(row.messages);acc.edited+=num(row.edited);acc.deleted+=num(row.deleted);acc.media+=num(row.media);return acc;},{messages:0,edited:0,deleted:0,media:0});
  }

  function primarySignal(data){
    const signal=signalRows(data)[0];
    if(signal?.text)return `${signal.icon||'🧠'} ${esc(signal.text)}`;
    const leaders=data?.leaders||{};
    if(leaders.deleted?.value)return `🗑 ${esc(leaders.deleted.name)} чаще остальных удаляет сообщения`;
    if(leaders.active?.value)return `🔥 Больше всего общения — ${esc(leaders.active.name)}`;
    if(num(data?.totals?.protected)>0)return `👻 В архиве уже ${num(data.totals.protected).toLocaleString('ru-RU')} скрытых медиа`;
    return '✨ Phantom продолжает собирать события вашего архива';
  }

  function stories(data){
    const rows=activityRows(data);const week=aggregate(data,'week');const currentStreak=streak(rows);const signals=signalRows(data);
    const base=[
      {icon:'🔥',title:`${currentStreak||1} дн.`,label:'серия',detail:currentStreak>1?`Вы активны уже ${currentStreak} дней подряд.`:'Начните серию: загляните завтра снова.'},
      {icon:'💬',title:week.messages.toLocaleString('ru-RU'),label:'за 7 дней',detail:`За неделю Phantom сохранил ${week.messages.toLocaleString('ru-RU')} сообщений.`},
    ];
    const signalStories=signals.slice(0,4).map(item=>({icon:item.icon||'🧠',title:String(item.title||'Insight').slice(0,16),label:'Phantom заметил',detail:item.text||'',dialogId:item.dialog_id||null}));
    if(signalStories.length)return [...base,...signalStories].slice(0,6);
    return [...base,{icon:'✏️',title:week.edited.toLocaleString('ru-RU'),label:'правок',detail:week.edited?`За неделю было ${week.edited} изменений сообщений.`:'На этой неделе правок пока не было.'},{icon:'👀',title:'Факты',label:'интересное',detail:primarySignal(data).replace(/^\S+\s/,'')}];
  }

  function trendBadge(data){
    const change=num(data?.comparison?.change_percent);
    if(!change)return '';
    const arrow=change>0?'↑':'↓';
    return `<span class="pulse-trend ${change>0?'up':'down'}">${arrow} ${Math.abs(change)}%</span>`;
  }

  function render(data,{stale=false}={}){
    cachedData=data;const values=aggregate(data,activePeriod);const currentStreak=streak(activityRows(data));const signals=signalRows(data);
    const signature=JSON.stringify(values)+primarySignal(data)+currentStreak+activePeriod+JSON.stringify(signals)+stale;
    if(mounted&&signature===lastSignature)return;lastSignature=signature;
    let section=app.querySelector('.engagement-pulse');if(!section){section=document.createElement('section');section.className='engagement-pulse';app.querySelector('.grid')?.before(section);}
    section.classList.remove('is-loading','is-error');
    section.classList.toggle('is-stale',stale);
    const storyItems=stories(data);
    section.innerHTML=`<div class="pulse-head"><div><span class="pulse-kicker">PHANTOM INSIGHTS</span><h2>${activePeriod==='today'?'Сегодня в архиве':'Неделя в Phantom'} ${trendBadge(data)}</h2></div><span class="pulse-live ${stale?'stale':''}"><i></i>${stale?' сохранено':currentStreak>1?` ${currentStreak} дней`:' live'}</span></div><div class="recap-tabs"><button data-recap="today" class="${activePeriod==='today'?'active':''}">Сегодня</button><button data-recap="week" class="${activePeriod==='week'?'active':''}">7 дней</button></div><div class="pulse-metrics"><button type="button" data-go="dialogs"><b data-count="${values.messages}">0</b><span>сообщений</span></button><button type="button" data-go="dialogs"><b data-count="${values.edited}">0</b><span>изменено</span></button><button type="button" data-go="dialogs"><b data-count="${values.deleted}">0</b><span>удалено</span></button><button type="button" data-go="stats"><b data-count="${values.media}">0</b><span>медиа</span></button></div><div class="smart-stories">${storyItems.map((item,index)=>`<button type="button" class="smart-story" data-story="${index}"><span>${item.icon}</span><b>${esc(item.title)}</b><small>${esc(item.label)}</small></button>`).join('')}</div><div class="story-detail" hidden></div><button type="button" class="pulse-insight" data-go="stats"><span>${primarySignal(data)}</span><strong>→</strong></button>${stale?'<button type="button" class="pulse-refresh" data-insights-refresh>Обновить данные</button>':''}`;
    mounted=true;animateCounts(section);
  }

  function renderSkeleton(){
    if(!isHome()||app.querySelector('.engagement-pulse'))return;
    const section=document.createElement('section');section.className='engagement-pulse is-loading';section.innerHTML='<div class="pulse-skeleton-head"></div><div class="pulse-skeleton-tabs"></div><div class="pulse-skeleton-grid"><i></i><i></i><i></i><i></i></div>';app.querySelector('.grid')?.before(section);
  }

  function renderError(){
    let section=app.querySelector('.engagement-pulse');if(!section){section=document.createElement('section');section.className='engagement-pulse';app.querySelector('.grid')?.before(section);}
    section.className='engagement-pulse is-error';
    section.innerHTML='<div class="pulse-error"><b>Phantom Insights временно недоступен</b><span>Основные функции Mini App продолжают работать.</span><button type="button" data-insights-refresh>Повторить</button></div>';
  }

  function animateCounts(root){root.querySelectorAll('[data-count]').forEach(node=>{const target=Number(node.dataset.count||0);const start=performance.now();const duration=Math.min(850,320+target*2);const frame=now=>{const p=Math.min(1,(now-start)/duration);const eased=1-Math.pow(1-p,3);node.textContent=Math.round(target*eased).toLocaleString('ru-RU');if(p<1)requestAnimationFrame(frame);};requestAnimationFrame(frame);});}

  async function refresh({force=false}={}){
    if(loading||!isHome())return;
    loading=true;
    if(force) token=null;
    try{
      const data=await api('/api/intelligence?days=14');
      writeCache(data);
      render(data);
    }catch{
      const fallback=cachedData||readCache();
      if(fallback)render(fallback,{stale:true});else renderError();
    }finally{loading=false;}
  }

  app.addEventListener('click',event=>{
    const recap=event.target.closest('[data-recap]');if(recap&&cachedData){activePeriod=recap.dataset.recap||'today';lastSignature='';render(cachedData);return;}
    const refreshButton=event.target.closest('[data-insights-refresh]');if(refreshButton){lastSignature='';refresh({force:true});return;}
    const story=event.target.closest('[data-story]');if(story&&cachedData){const item=stories(cachedData)[Number(story.dataset.story||0)];const detail=app.querySelector('.engagement-pulse .story-detail');if(detail&&item){detail.hidden=false;detail.innerHTML=`<b>${item.icon} ${esc(item.title)}</b><span>${esc(item.detail)}</span>${item.dialogId?'<button type="button" data-insight-dialog>Открыть диалоги →</button>':''}`;detail.dataset.dialogId=item.dialogId||'';detail.animate([{opacity:.3,transform:'translateY(6px)'},{opacity:1,transform:'translateY(0)'}],{duration:260,easing:'ease-out'});}}
    const insightDialog=event.target.closest('[data-insight-dialog]');if(insightDialog){const detail=insightDialog.closest('.story-detail');if(detail?.dataset.dialogId)sessionStorage.setItem('phantom:focus-dialog',detail.dataset.dialogId);app.querySelector('[data-go="dialogs"]')?.click();}
  });

  async function mount(){
    if(loading||!isHome())return;
    const cached=readCache();
    if(cached&&!cachedData)render(cached,{stale:true});else if(!cachedData)renderSkeleton();
    await refresh();
  }

  let queued=false;new MutationObserver(()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;if(isHome())mount();else mounted=false;});}).observe(app,{childList:true,subtree:true});
  let ticking=false;addEventListener('scroll',()=>{if(ticking)return;ticking=true;requestAnimationFrame(()=>{ticking=false;const section=app.querySelector('.engagement-pulse');if(!section)return;const rect=section.getBoundingClientRect();const progress=Math.max(-1,Math.min(1,(innerHeight*.5-rect.top)/innerHeight));section.style.setProperty('--pulse-shift',`${progress*12}px`);section.style.setProperty('--pulse-glow',String(Math.max(0,.7-Math.abs(progress)*.25)));});},{passive:true});
  mount();
})();