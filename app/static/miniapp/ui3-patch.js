(() => {
  function refineOnboardingMedia() {
    const slide = document.querySelector('.ph-ui3-slide[data-slide="3"] .ph-ui3-demo');
    if (!slide || slide.dataset.refined === '1') return;
    slide.dataset.refined = '1';
    slide.innerHTML = `
      <div class="ph-ui3-fire-cover" role="img" aria-label="Исчезающее медиа сохранено">
        <div class="ph-ui3-fire-orbit"></div>
        <div class="ph-ui3-fire-core">🔥</div>
        <div class="ph-ui3-fire-counter">↻ 1</div>
        <div class="ph-ui3-fire-caption">
          <b>Исчезающее медиа сохранено</b>
          <small>Оригинал доступен в вашем приватном архиве</small>
        </div>
      </div>`;
  }

  function neutralizeProductWording(root = document) {
    const replacements = new Map([
      ['Архив Telegram Business', 'Приватный архив переписок'],
      ['Telegram Business', 'Ассистент в чатах'],
      ['Подключён', 'Активен'],
      ['Не подключён', 'Не активен'],
    ]);
    root.querySelectorAll('h1,h2,h3,p,small,b,span,div').forEach(node => {
      if (node.children.length) return;
      const text = (node.textContent || '').trim();
      if (replacements.has(text)) node.textContent = replacements.get(text);
    });
  }

  function apply() {
    refineOnboardingMedia();
    neutralizeProductWording();
  }

  document.addEventListener('DOMContentLoaded', () => {
    apply();
    const target = document.querySelector('#app') || document.body;
    new MutationObserver(apply).observe(target, {childList: true, subtree: true});
  });
})();
