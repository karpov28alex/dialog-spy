(() => {
  const modules = [
    { label: "🔎 Поиск и User360", href: "/admin/user360-v2.html?v=1" },
    { label: "💬 Диалоги пользователей", href: "/admin/dialogs-media.html?v=1" },
    { label: "📊 Расширенная статистика", href: "/admin/platform.html?v=1" },
    { label: "🩺 Операции и здоровье", href: "/admin/operations.html?v=1" },
    { label: "💳 Платежи и доступ", href: "/admin/billing-v2-1.html?v=1" },
    { label: "⚙️ Расширенные настройки", href: "/admin/funnel.html?v=1" },
  ];

  function install() {
    const nav = document.querySelector(".nav");
    if (!nav || document.querySelector("[data-restored-admin-modules]")) return;

    const marker = document.createElement("div");
    marker.dataset.restoredAdminModules = "true";
    marker.style.cssText = "margin:10px 10px 4px;color:var(--muted);font-size:11px;letter-spacing:.08em;text-transform:uppercase";
    marker.textContent = "Расширенные модули";
    nav.appendChild(marker);

    for (const item of modules) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = item.label;
      button.addEventListener("click", () => {
        window.location.assign(item.href);
      });
      nav.appendChild(button);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", install, { once: true });
  } else {
    install();
  }
})();
