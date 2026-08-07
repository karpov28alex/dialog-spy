(() => {
  'use strict';

  const PRODUCT_MARKER = 'PHANTOM PULSE';
  void PRODUCT_MARKER;
  const app = document.getElementById('app');
  const tg = window.Telegram?.WebApp;
  if (!app || !tg?.initData) return;

  let token = null;
  let loading = false;
  let mounted = false;
  let lastSignature = '';
  let activePeriod = 'today';
  let cachedData = null;

  async function auth() {
    if (token) return token;
    const response = await fetch('/api/auth/telegram', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({init_data: tg.initData}), cache: 'no-store',
    });
    if (!response.ok) throw new Error('auth');
    token = (await response.json()).access_token;
    return token;
  }

  async function api(path) {
    const bearer = await auth();
    const response = await fetch(path, {headers: {Authorization: `Bearer ${bearer}`}, cache: 'no-store'});
    if (!response.ok) throw new Error(String(response.status));
    return response.json();
  }

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const num = value => Number(value || 0);

  function isHome() { return Boolean(app.querySelector('.brand') && app.querySelector('.navcard[data-go="dialogs"]')); }
  function activityRows(data) { return Array.isArray(data?.activity) ? data.activity : []; }

  function streak(rows) {
    let total = 0;
    for (let index = rows.length - 1; index >= 0; index -= 1) {
      if (num(rows[index]?.messages) <= 0) break;
      total += 1;
    }
    return total;
  }

  function aggregate(data, period) {
    const rows = activityRows(data);
    const selected = period === 'today' ? rows.slice(-1) : rows.slice(-7);
    return selected.reduce((acc, row) => {
      acc.messages += num(row.messages); acc.edited += num(row.edited);
      acc.deleted += num(row.deleted); acc.media += num(row.media); return acc;
    }, {messages:0, edited:0, deleted:0, media:0});
  }

  function insightLine(data) {
    const leaders = data?.leaders || {};
    if (leaders.deleted?.value) return `🗑 ${esc(leaders.deleted.name)} чаще остальных удаляет сообщения`;
    if (leaders.active?.value) return `🔥 Больше всего общения — ${esc(leaders.active.name)}`;
    if (num(data?.totals?.protected) > 0) return `👻 В архиве уже ${num(data.totals.protected).toLocaleString('ru-RU')} скрытых медиа`;
    return '✨ Phantom продолжает собирать события вашего архива';
  }

  function stories(data) {
    const rows = activityRows(data); const week = aggregate(data, 'week'); const currentStreak = streak(rows); const leaders = data?.leaders || {};
    return [
      {icon:'🔥', title:`${currentStreak || 1} дн.`, label:'серия', detail: currentStreak > 1 ? `Вы активны уже ${currentStreak} дней подряд.` : 'Начните серию: загляните завтра снова.'},
      {icon:'💬', title:week.messages.toLocaleString('ru-RU'), label:'за 7 дней', detail:`За неделю Phantom сохранил ${week.messages.toLocaleString('ru-RU')} сообщений.`},
      {icon:'✏️', title:week.edited.toLocaleString('ru-RU'), label:'правок', detail: week.edited ? `За неделю было ${week.edited} изменений сообщений.` : 'На этой неделе правок пока не было.'},
      {icon:'👀', title:leaders.deleted?.name ? String(leaders.deleted.name).slice(0,10) : 'Факты', label:'интересное', detail: insightLine(data).replace(/^\S+\s/, '')},
    ];
  }

  function render(data) {
    cachedData = data;
    const values = aggregate(data, activePeriod); const currentStreak = streak(activityRows(data));
    const signature = JSON.stringify(values) + insightLine(data) + currentStreak + activePeriod;
    if (mounted && signature === lastSignature) return;
    lastSignature = signature;
    let section = app.querySelector('.engagement-pulse');
    if (!section) { section = document.createElement('section'); section.className = 'engagement-pulse'; app.querySelector('.grid')?.before(section); }
    const storyItems = stories(data);
    section.innerHTML = `<div class="pulse-head"><div><span class="pulse-kicker">PHANTOM RECAP</span><h2>${activePeriod === 'today' ? 'Сегодня в архиве' : 'Неделя в Phantom'}</h2></div><span class="pulse-live"><i></i>${currentStreak > 1 ? ` ${currentStreak} дней` : ' live'}</span></div><div class="recap-tabs"><button data-recap="today" class="${activePeriod==='today'?'active':''}">Сегодня</button><button data-recap="week" class="${activePeriod==='week'?'active':''}">7 дней</button></div><div class="pulse-metrics"><button type="button" data-go="dialogs"><b data-count="${values.messages}">0</b><span>сообщений</span></button><button type="button" data-go="dialogs"><b data-count="${values.edited}">0</b><span>изменено</span></button><button type="button" data-go="dialogs"><b data-count="${values.deleted}">0</b><span>удалено</span></button><button type="button" data-go="stats"><b data-count="${values.media}">0</b><span>медиа</span></button></div><div class="smart-stories">${storyItems.map((item,index)=>`<button type="button" class="smart-story" data-story="${index}"><span>${item.icon}</span><b>${esc(item.title)}</b><small>${esc(item.label)}</small></button>`).join('')}</div><div class="story-detail" hidden></div><button type="button" class="pulse-insight" data-go="stats"><span>${insightLine(data)}</span><strong>→</strong></button>`;
    mounted = true; animateCounts(section);
  }

  function animateCounts(root) {
    root.querySelectorAll('[data-count]').forEach(node => {
      const target = Number(node.dataset.count || 0); const start = performance.now(); const duration = Math.min(850, 320 + target * 2);
      const frame = now => { const p=Math.min(1,(now-start)/duration); const eased=1-Math.pow(1-p,3); node.textContent=Math.round(target*eased).toLocaleString('ru-RU'); if(p<1)requestAnimationFrame(frame); };
      requestAnimationFrame(frame);
    });
  }

  app.addEventListener('click', event => {
    const recap = event.target.closest('[data-recap]');
    if (recap && cachedData) { activePeriod=recap.dataset.recap||'today'; lastSignature=''; render(cachedData); return; }
    const story = event.target.closest('[data-story]');
    if (story && cachedData) { const item=stories(cachedData)[Number(story.dataset.story||0)]; const detail=app.querySelector('.engagement-pulse .story-detail'); if(detail&&item){detail.hidden=false;detail.innerHTML=`<b>${item.icon} ${esc(item.title)}</b><span>${esc(item.detail)}</span>`;detail.animate([{opacity:.3,transform:'translateY(6px)'},{opacity:1,transform:'translateY(0)'}],{duration:260,easing:'ease-out'});} }
  });

  async function mount() { if(loading||!isHome())return;loading=true;try{render(await api('/api/intelligence?days=7'));}catch{}finally{loading=false;} }
  let queued=false;new MutationObserver(()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;if(isHome())mount();else mounted=false;});}).observe(app,{childList:true,subtree:true});
  let ticking=false;addEventListener('scroll',()=>{if(ticking)return;ticking=true;requestAnimationFrame(()=>{ticking=false;const section=app.querySelector('.engagement-pulse');if(!section)return;const rect=section.getBoundingClientRect();const progress=Math.max(-1,Math.min(1,(innerHeight*.5-rect.top)/innerHeight));section.style.setProperty('--pulse-shift',`${progress*12}px`);section.style.setProperty('--pulse-glow',String(Math.max(0,.7-Math.abs(progress)*.25)));});},{passive:true});
  mount();
})();