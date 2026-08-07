(() => {
  'use strict';
  // Navigation is owned by app.js. The previous capture-phase handler used
  // location.assign() for every click, forcing a full Telegram WebView reload,
  // re-authentication and visible UI rollback/latency. Keep this file as a
  // compatibility no-op so cached index.html references remain harmless.
})();
