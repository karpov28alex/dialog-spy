(() => {
  const MAX_VISIBLE_MS = 6500;
  const MIN_VISIBLE_MS = 900;
  const startedAt = Date.now();

  function appReady(){
    const app=document.querySelector('#app');
    if(!app)return false;
    return Boolean(app.querySelector('main.page,.topbar,.error')) && !app.querySelector(':scope > .boot');
  }

  function closeLoaders(force=false){
    const elapsed=Date.now()-startedAt;
    if(!force&&elapsed<MIN_VISIBLE_MS)return;
    document.querySelectorAll('.ph-load').forEach(loader=>{
      loader.classList.add('ph-load-closing');
      setTimeout(()=>loader.remove(),180);
    });
  }

  function recoverBoot(){
    const app=document.querySelector('#app');
    if(!app||!app.querySelector(':scope > .boot'))return;
    const retry=document.createElement('button');
    retry.className='retry ph-loader-retry';
    retry.textContent='Повторить загрузку';
    retry.onclick=()=>location.reload();
    const boot=app.querySelector(':scope > .boot');
    if(!boot.querySelector('.ph-loader-retry'))boot.appendChild(retry);
  }

  const observer=new MutationObserver(()=>{
    if(appReady())closeLoaders();
  });

  document.addEventListener('DOMContentLoaded',()=>{
    observer.observe(document.documentElement,{childList:true,subtree:true});
    if(appReady())closeLoaders();

    setTimeout(()=>closeLoaders(true),MAX_VISIBLE_MS);
    setTimeout(()=>{
      if(!appReady())recoverBoot();
    },MAX_VISIBLE_MS+300);
  });

  window.addEventListener('error',()=>setTimeout(()=>closeLoaders(true),250));
  window.addEventListener('unhandledrejection',()=>setTimeout(()=>closeLoaders(true),250));
})();