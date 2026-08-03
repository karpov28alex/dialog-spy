(() => {
  const STORAGE_KEY = 'phantom.ui3.onboarding.v2';
  const LOGO_B64_URL = '/app/phantom-logo.b64?v=0.8.1';
  const slides = [
    {
      kicker: '1/6 · Изменённые сообщения',
      title: 'Лови каждую <span>правку</span>',
      copy: 'Phantom сохраняет исходный текст собеседника и показывает, что именно изменилось.',
      demo: `<div class="ph-ui3-label"><span>Сообщение изменено</span><span>23:44</span></div><div class="ph-ui3-message old">Буду в офисе до вечера</div><div class="ph-ui3-message">Буду поздно — не жди к ужину</div>`
    },
    {
      kicker: '2/6 · Удалённые сообщения',
      title: 'Ничего <span>не исчезнет</span>',
      copy: 'Если собеседник удалит сообщение, сохранённая версия останется в вашем приватном архиве.',
      demo: `<div class="ph-ui3-label"><span>Удалено собеседником</span><span>19:21</span></div><div class="ph-ui3-message deleted">Сотри переписку, на всякий случай.</div><div class="ph-ui3-message saved">✓ Сохранено в Phantom</div>`
    },
    {
      kicker: '3/6 · Личные и групповые чаты',
      title: 'Работает <span>в нужных чатах</span>',
      copy: 'Добавьте Phantom как ассистента в выбранные переписки — личные и групповые события появятся в одном архиве.',
      demo: `<div class="ph-ui3-timeline"><div class="ph-ui3-event"><span class="ph-ui3-event-dot">●</span><div class="ph-ui3-event-body"><b>Команда дизайна</b><small>Катя изменила сообщение</small></div></div><div class="ph-ui3-event"><span class="ph-ui3-event-dot">●</span><div class="ph-ui3-event-body"><b>Личный чат</b><small>Удалено 2 сообщения</small></div></div></div>`
    },
    {
      kicker: '4/6 · Исчезающие медиа',
      title: 'Медиа <span>останется у вас</span>',
      copy: 'Фото, видео, кружки и голосовые сохраняются в архиве без лишних действий.',
      demo: `<div class="ph-ui3-media">📷</div>`
    },
    {
      kicker: '5/6 · Голос в текст',
      title: 'Голос <span>становится текстом</span>',
      copy: 'Слушайте запись или быстро находите нужную мысль в удобной расшифровке.',
      demo: `<div class="ph-ui3-label"><span>Голосовое · 0:42</span><span>18:02</span></div><div class="ph-ui3-wave">${Array.from({length:22},()=>'<i></i>').join('')}</div><div class="ph-ui3-message">Подтверждаю сроки по договору. Оплата до пятницы.</div>`
    },
    {
      kicker: '6/6 · Конфиденциальность',
      title: 'Ваш архив — <span>только ваш</span>',
      copy: 'Сообщения и медиа защищены. Доступ к архиву есть только у владельца аккаунта и у тех, кому он сам его предоставит.',
      demo: `<div class="ph-ui3-timeline"><div class="ph-ui3-event"><span class="ph-ui3-event-dot">🔐</span><div class="ph-ui3-event-body"><b>Конфиденциальный доступ</b><small>Архив открывается только после вашей авторизации</small></div></div><div class="ph-ui3-event"><span class="ph-ui3-event-dot">🛡</span><div class="ph-ui3-event-body"><b>Защищённое хранение</b><small>История и медиа находятся в вашем приватном пространстве</small></div></div></div>`
    }
  ];

  function haptic(type='light') { try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(type); } catch {} }

  async function loadLogoData() {
    try {
      const response = await fetch(LOGO_B64_URL, {cache:'no-store'});
      if (!response.ok) return '';
      const encoded = (await response.text()).replace(/\s+/g, '');
      return encoded.length > 1000 ? `data:image/jpeg;base64,${encoded}` : '';
    } catch { return ''; }
  }

  async function hydrateLoaderLogo(loader) {
    const data = await loadLogoData();
    const holder = loader.querySelector('.ph-load-logo');
    if (!holder || !data) return;
    holder.innerHTML = `<img src="${data}" alt="Phantom" draggable="false">`;
  }

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
    loader.innerHTML = `<div class="ph-load-inner"><div class="ph-load-logo" aria-label="Phantom">P</div><div class="ph-load-title">Phantom запускается</div><div class="ph-load-copy">Проверяем подключение ассистента…</div><div class="ph-load-progress"><div class="ph-load-bar"></div></div><div class="ph-load-meta"><span>Защищённое подключение</span><b>4%</b></div><div class="ph-load-card"><b>🔐 Только ваш доступ</b><small>Сообщения и медиа находятся в приватном архиве</small></div></div>`;
    document.body.appendChild(loader);
    hydrateLoaderLogo(loader);
    const steps = [
      [14,'Проверяем подключение ассистента…'],[27,'Подготавливаем приватный архив…'],[43,'Синхронизируем историю событий…'],[61,'Проверяем медиа и голосовые…'],[78,'Настраиваем защиту данных…'],[92,'Собираем главный экран…'],[100,'Готово']
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

  function hidePrematureVip() {
    const state = window.__phantomAccess?.state;
    if (['referral_required','payment_required'].includes(state)) return;
    document.querySelectorAll('#app *').forEach(node => {
      if (node.children.length === 0 && /\bVIP\b|\bВИП\b/i.test(node.textContent || '')) {
        const card = node.closest('.row,.status,.settings-card,.navcard,[data-plan]');
        (card || node).style.display = 'none';
      }
    });
  }

  function enhancePrivacyLabels() {
    document.querySelectorAll('.status').forEach(status => {
      if (status.dataset.privacy === '1') return;
      status.dataset.privacy = '1';
      status.innerHTML = '<b>🔐 Конфиденциальный архив</b><br><small>Сообщения и медиа защищены. Доступ есть только у владельца аккаунта.</small>';
    });
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
        const status=document.createElement('div');status.className='ph-media-status ready';status.textContent='✓ Сохранено в приватном архиве';wrap.appendChild(status);
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

  function refreshUi() {
    enhanceDialog();
    hidePrematureVip();
    enhancePrivacyLabels();
  }

  function observeApp() {
    const app=document.querySelector('#app');if(!app)return;
    new MutationObserver(refreshUi).observe(app,{childList:true,subtree:true});
    refreshUi();
  }

  document.addEventListener('DOMContentLoaded',()=>{
    buildOnboarding();
    if(localStorage.getItem(STORAGE_KEY)==='done')showLoader();
    observeApp();
  });
  window.PhantomUI3={resetOnboarding(){localStorage.removeItem(STORAGE_KEY);location.reload()},showLoader:()=>showLoader(true)};
})();