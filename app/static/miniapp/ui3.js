(() => {
  const STORAGE_KEY = 'phantom.ui3.onboarding.v1';
  const slides = [
    {
      kicker: '1/6 · Изменённые сообщения',
      title: 'Лови каждую <span>правку</span>',
      copy: 'Phantom сохраняет исходный текст и показывает, что именно изменилось.',
      demo: `<div class="ph-ui3-label"><span>Сообщение изменено</span><span>23:44</span></div><div class="ph-ui3-message old">Буду в офисе до вечера</div><div class="ph-ui3-message">Буду поздно — не жди к ужину</div>`
    },
    {
      kicker: '2/6 · Удалённые сообщения',
      title: 'Ничего <span>не исчезнет</span>',
      copy: 'Даже если собеседник удалит сообщение, оно останется в вашем архиве.',
      demo: `<div class="ph-ui3-label"><span>Удалено собеседником</span><span>19:21</span></div><div class="ph-ui3-message deleted">Сотри переписку, на всякий случай.</div><div class="ph-ui3-message saved">✓ Восстановлено Phantom</div>`
    },
    {
      kicker: '3/6 · Личные и групповые чаты',
      title: 'Работает <span>везде</span>',
      copy: 'Личные переписки и групповые чаты собираются в одном понятном архиве.',
      demo: `<div class="ph-ui3-timeline"><div class="ph-ui3-event"><span class="ph-ui3-event-dot">●</span><div class="ph-ui3-event-body"><b>Команда дизайна</b><small>Катя изменила сообщение</small></div></div><div class="ph-ui3-event"><span class="ph-ui3-event-dot">●</span><div class="ph-ui3-event-body"><b>Личный чат</b><small>Удалено 2 сообщения</small></div></div></div>`
    },
    {
      kicker: '4/6 · Исчезающие медиа',
      title: 'Медиа <span>без следов</span>',
      copy: 'Фото, видео, кружки и голосовые сохраняются без отметки о просмотре.',
      demo: `<div class="ph-ui3-media">📷</div>`
    },
    {
      kicker: '5/6 · Голос в текст',
      title: 'Голос <span>становится текстом</span>',
      copy: 'Слушайте запись или быстро находите нужную мысль в расшифровке.',
      demo: `<div class="ph-ui3-label"><span>Голосовое · 0:42</span><span>18:02</span></div><div class="ph-ui3-wave">${Array.from({length:22},()=>'<i></i>').join('')}</div><div class="ph-ui3-message">Подтверждаю сроки по договору. Оплата до пятницы.</div>`
    },
    {
      kicker: '6/6 · Приватный архив',
      title: 'Под защитой <span>Phantom</span>',
      copy: 'Доступ, медиа и история событий собраны в одном приватном пространстве.',
      demo: `<div class="ph-ui3-timeline"><div class="ph-ui3-event"><span class="ph-ui3-event-dot">🔐</span><div class="ph-ui3-event-body"><b>Telegram Business</b><small>Подключение подтверждено</small></div></div><div class="ph-ui3-event"><span class="ph-ui3-event-dot">🛡</span><div class="ph-ui3-event-body"><b>Архив готов</b><small>История и медиа защищены</small></div></div></div>`
    }
  ];

  function haptic(type='light') { try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(type); } catch {} }

  function buildOnboarding() {
    if (localStorage.getItem(STORAGE_KEY) === 'done') return;
    const root = document.createElement('section');
    root.className = 'ph-ui3-overlay';
    root.innerHTML = `<div class="ph-ui3-top"><button class="ph-ui3-skip">Пропустить</button><button class="ph-ui3-lang">RU</button></div><div class="ph-ui3-stage">${slides.map((s,i)=>`<article class="ph-ui3-slide ${i===0?'active':''}" data-slide="${i}"><div class="ph-ui3-kicker">${s.kicker}</div><h1 class="ph-ui3-title">${s.title}</h1><p class="ph-ui3-copy">${s.copy}</p><div class="ph-ui3-demo">${s.demo}</div></article>`).join('')}</div><div class="ph-ui3-footer"><div class="ph-ui3-dots">${slides.map((_,i)=>`<i class="${i===0?'active':''}"></i>`).join('')}</div><button class="ph-ui3-next">Далее</button></div>`;
    document.body.appendChild(root);
    let index = 0;
    const setSlide = next => {
      index = Math.max(0, Math.min(slides.length - 1, next));
      root.querySelectorAll('.ph-ui3-slide').forEach((el,i)=>el.classList.toggle('active', i===index));
      root.querySelectorAll('.ph-ui3-dots i').forEach((el,i)=>el.classList.toggle('active', i===index));
      root.querySelector('.ph-ui3-next').textContent = index === slides.length - 1 ? 'Начать работу' : 'Далее';
      haptic(index === slides.length - 1 ? 'medium' : 'light');
    };
    const finish = () => { localStorage.setItem(STORAGE_KEY, 'done'); root.remove(); showLoader(); };
    root.querySelector('.ph-ui3-next').addEventListener('click',()=> index === slides.length - 1 ? finish() : setSlide(index+1));
    root.querySelector('.ph-ui3-skip').addEventListener('click',finish);
    let startX = 0;
    root.addEventListener('touchstart',e=>{startX=e.touches[0].clientX},{passive:true});
    root.addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-startX;if(Math.abs(dx)>55)setSlide(index+(dx<0?1:-1))},{passive:true});
  }

  function showLoader(force=false) {
    if (!force && document.querySelector('.ph-load')) return;
    const loader = document.createElement('section');
    loader.className = 'ph-load';
    loader.innerHTML = `<div class="ph-load-inner"><div class="ph-load-logo">P</div><div class="ph-load-title">Phantom запускается</div><div class="ph-load-copy">Проверяем Telegram Business…</div><div class="ph-load-progress"><div class="ph-load-bar"></div></div><div class="ph-load-meta"><span>Безопасное подключение</span><b>4%</b></div><div class="ph-load-card">Ваши данные под надёжной защитой</div></div>`;
    document.body.appendChild(loader);
    const steps = [
      [14,'Проверяем Telegram Business…'],[27,'Подготавливаем приватный архив…'],[43,'Синхронизируем историю событий…'],[61,'Проверяем медиа и голосовые…'],[78,'Настраиваем уведомления…'],[92,'Собираем главный экран…'],[100,'Готово']
    ];
    let i=0;
    const tick=()=>{
      const [value,text]=steps[i++];
      loader.querySelector('.ph-load-bar').style.width=`${value}%`;
      loader.querySelector('.ph-load-copy').textContent=text;
      loader.querySelector('.ph-load-meta b').textContent=`${value}%`;
      if(i<steps.length)setTimeout(tick,420+Math.random()*280);else setTimeout(()=>loader.remove(),500);
    };
    setTimeout(tick,120);
  }

  function classifyMessage(msg) {
    if (msg.classList.contains('deleted')) return 'deleted';
    if (msg.querySelector('.history') || /изменено/i.test(msg.textContent)) return 'edited';
    if (msg.querySelector('.media-image,.media-video,.media-audio,.media-file,.media-wait')) return 'media';
    return 'all';
  }

  function enhanceDialog() {
    const messages = document.querySelector('.messages');
    if (!messages || messages.dataset.ui3 === '1') return;
    messages.dataset.ui3='1';
    const toolbar=document.createElement('div');
    toolbar.className='ph-event-tabs';
    toolbar.innerHTML='<button class="ph-event-tab active" data-filter="all">Все</button><button class="ph-event-tab" data-filter="edited">Изменённые</button><button class="ph-event-tab" data-filter="deleted">Удалённые</button><button class="ph-event-tab" data-filter="media">Медиа</button>';
    messages.before(toolbar);
    toolbar.addEventListener('click',e=>{
      const btn=e.target.closest('[data-filter]');if(!btn)return;
      toolbar.querySelectorAll('.ph-event-tab').forEach(x=>x.classList.toggle('active',x===btn));
      messages.querySelectorAll('.msg').forEach(msg=>{const type=classifyMessage(msg);msg.classList.toggle('ph-hidden-by-filter',btn.dataset.filter!=='all'&&type!==btn.dataset.filter)});
      haptic();
    });
    messages.querySelectorAll('.msg').forEach(msg=>{
      msg.querySelectorAll('.media-image,.media-video').forEach(media=>{
        if(media.parentElement?.classList.contains('ph-media-wrap'))return;
        const wrap=document.createElement('div');wrap.className='ph-media-wrap';media.parentNode.insertBefore(wrap,media);wrap.appendChild(media);
        const open=document.createElement('button');open.className='ph-media-expand';open.type='button';open.textContent='↗';wrap.appendChild(open);
        const status=document.createElement('div');status.className='ph-media-status ready';status.textContent='✓ Сохранено в Phantom';wrap.appendChild(status);
        open.addEventListener('click',()=>openLightbox(media));
      });
      msg.querySelectorAll('.media-wait').forEach(el=>{const status=document.createElement('div');status.className='ph-media-status unavailable';status.textContent='Медиа пока недоступно для восстановления';el.after(status)});
    });
  }

  function openLightbox(media) {
    let box=document.querySelector('.ph-lightbox');
    if(!box){box=document.createElement('div');box.className='ph-lightbox';box.hidden=true;box.innerHTML='<button class="ph-lightbox-close">×</button><div class="ph-lightbox-body"></div>';document.body.appendChild(box);box.querySelector('button').onclick=()=>{box.hidden=true;box.querySelector('.ph-lightbox-body').innerHTML=''}}
    const clone=media.cloneNode(true);clone.removeAttribute('loading');if(clone.tagName==='VIDEO')clone.controls=true;
    box.querySelector('.ph-lightbox-body').replaceChildren(clone);box.hidden=false;haptic('medium');
  }

  function observeApp() {
    const app=document.querySelector('#app');if(!app)return;
    new MutationObserver(()=>enhanceDialog()).observe(app,{childList:true,subtree:true});
    enhanceDialog();
  }

  document.addEventListener('DOMContentLoaded',()=>{
    buildOnboarding();
    if(localStorage.getItem(STORAGE_KEY)==='done')showLoader();
    observeApp();
  });
  window.PhantomUI3={resetOnboarding(){localStorage.removeItem(STORAGE_KEY);location.reload()},showLoader:()=>showLoader(true)};
})();