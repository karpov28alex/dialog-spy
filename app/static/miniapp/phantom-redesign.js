const app=document.getElementById('app');
const safe=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function removeLegacyDuplicates(){
  document.querySelectorAll('.phantom-stories,.phantom-archive-summary,.phantom-fab,.phantom-story-overlay').forEach(node=>node.remove());
}

function enhanceStats(){
  const page=document.querySelector('.page');
  if(!page||document.querySelector('.topbar .title')?.textContent.trim()!=='Статистика')return;
  page.classList.add('phantom-stats-enhanced');
  [...page.querySelectorAll('.grid')].forEach(grid=>{
    grid.classList.add('phantom-metric-grid');
    [...grid.children].forEach((card,index)=>{
      if(card.classList.contains('phantom-metric'))return;
      card.classList.add('phantom-metric');
      const row=card.querySelector('.row');
      if(!row)return;
      const value=row.querySelector('b')?.textContent||'0';
      const raw=row.querySelector('span')?.textContent||'';
      const icon=['💬','✉️','📸','🗑️','✏️','👁️'][index%6];
      const label=raw.replace(/[💬✉️📸🗑️✏️👁️👻]/gu,'').trim();
      card.innerHTML=`<div class="phantom-metric-icon">${icon}</div><div><small>${safe(label)}</small><b>${safe(value)}</b></div>`;
    });
  });
  [...page.querySelectorAll('.settings-card')].forEach(card=>{
    const title=card.querySelector('h3')?.textContent||'';
    if(title.includes('Лидеры')&&!card.dataset.phantomLeaders){
      card.dataset.phantomLeaders='1';
      [...card.querySelectorAll('.row')].forEach((row,index)=>{
        const left=row.querySelector('span')?.innerHTML||'';
        const value=row.querySelector('b')?.textContent||'';
        row.className='phantom-leader-row';
        row.innerHTML=`<span class="phantom-leader-icon">${['🏆','📸','🗑️','🔥'][index%4]}</span><span>${left}</span><strong>${safe(value)}</strong>`;
      });
    }
    if(title.includes('Активность по времени')&&!card.querySelector('.phantom-bars')){
      const rows=[...card.querySelectorAll('.row')];
      if(!rows.length)return;
      const max=Math.max(...rows.map(row=>Number(row.querySelector('b')?.textContent||0)),1);
      const bars=document.createElement('div');
      bars.className='phantom-bars';
      bars.innerHTML=rows.map(row=>{
        const label=row.querySelector('span')?.textContent||'';
        const value=Number(row.querySelector('b')?.textContent||0);
        return `<div class="phantom-bar"><span>${safe(label)}</span><span class="phantom-bar-track"><span class="phantom-bar-fill" style="width:${Math.max(6,Math.round(value/max*100))}%"></span></span><b>${value}</b></div>`;
      }).join('');
      rows.forEach(row=>row.remove());
      card.appendChild(bars);
    }
  });
}

function enhance(){removeLegacyDuplicates();enhanceStats();}
new MutationObserver(()=>requestAnimationFrame(enhance)).observe(app,{childList:true,subtree:true});
document.addEventListener('click',event=>{if(event.target.closest('[data-go],[data-back],[data-stats-days],[data-theme]'))setTimeout(enhance,80)});
enhance();
