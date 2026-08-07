(() => {
  'use strict';
  const app = document.getElementById('app');
  if (!app) return;

  const numberValue = text => {
    const match = String(text || '').replace(/\s/g, '').match(/-?\d+(?:[.,]\d+)?/);
    return match ? Number(match[0].replace(',', '.')) : null;
  };

  function animateNumber(node) {
    if (!node || node.dataset.motionNumber === '1') return;
    const target = numberValue(node.textContent);
    if (target === null || !Number.isFinite(target) || target < 0) return;
    node.dataset.motionNumber = '1';
    const suffix = String(node.textContent || '').replace(/[\d\s.,-]/g, '');
    const duration = 650;
    const start = performance.now();
    const frame = now => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      const value = target >= 100 ? Math.round(target * eased) : Math.round(target * eased * 10) / 10;
      node.textContent = `${new Intl.NumberFormat('ru-RU').format(value)}${suffix ? ` ${suffix}` : ''}`;
      if (p < 1) requestAnimationFrame(frame);
      else node.textContent = `${new Intl.NumberFormat('ru-RU').format(target)}${suffix ? ` ${suffix}` : ''}`;
    };
    requestAnimationFrame(frame);
  }

  function classifyCards(main) {
    const cards = [...main.querySelectorAll(':scope > .settings-card')];
    for (const card of cards) {
      const title = card.querySelector('h3')?.textContent?.trim().toLowerCase() || '';
      if (title === 'период') card.classList.add('motion-period');
      else if (title.includes('лидер')) card.classList.add('motion-leaders');
      else if (title.includes('активность по времени')) card.classList.add('motion-activity');
      else if (title.includes('последние дни')) card.classList.add('motion-days');
      else if (title.includes('интересные факты')) card.classList.add('motion-insights');
      else if (title.includes('экспорт')) card.classList.add('motion-export');
    }
  }

  function barsFor(card, className) {
    if (!card || card.dataset.motionBars === '1') return;
    const rows = [...card.querySelectorAll('.row')];
    const values = rows.map(row => numberValue(row.querySelector('b')?.textContent)).map(v => v || 0);
    const max = Math.max(1, ...values);
    rows.forEach((row, index) => {
      row.classList.add('motion-bar-row');
      row.style.setProperty('--motion-value', `${Math.max(4, Math.round((values[index] / max) * 100))}%`);
      row.style.setProperty('--motion-delay', `${index * 70}ms`);
      const bar = document.createElement('i');
      bar.className = className;
      row.appendChild(bar);
    });
    card.dataset.motionBars = '1';
  }

  function decorate() {
    const title = app.querySelector('.topbar .title')?.textContent?.trim();
    if (title !== 'Статистика') return;
    const main = app.querySelector('main.page');
    if (!main || main.dataset.motionStats === '1') return;
    main.dataset.motionStats = '1';
    main.classList.add('motion-stats');

    const aura = document.createElement('div');
    aura.className = 'motion-stats-aura';
    main.prepend(aura);

    classifyCards(main);
    const metricGrid = main.querySelector(':scope > .grid');
    metricGrid?.classList.add('motion-metric-grid');
    metricGrid?.querySelectorAll('.settings-card').forEach((card, index) => {
      card.classList.add('motion-metric');
      card.style.setProperty('--motion-delay', `${index * 55}ms`);
      animateNumber(card.querySelector('b'));
    });

    const leaders = main.querySelector('.motion-leaders');
    leaders?.querySelectorAll('.row').forEach((row, index) => {
      row.classList.add('motion-leader-row');
      row.style.setProperty('--motion-delay', `${index * 70}ms`);
    });

    barsFor(main.querySelector('.motion-activity'), 'motion-activity-fill');
    barsFor(main.querySelector('.motion-days'), 'motion-day-fill');

    main.querySelectorAll('.settings-card').forEach((card, index) => {
      card.classList.add('motion-enter');
      card.style.setProperty('--motion-card-delay', `${Math.min(index, 8) * 45}ms`);
    });
  }

  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; decorate(); });
  }).observe(app, {childList: true, subtree: true});
  decorate();
})();
