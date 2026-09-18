'use strict';

(function () {
  if (window.__liveCompBootstrapped) return;
  window.__liveCompBootstrapped = true;

  function bootstrap() {
    if (window.LiveCompSession) {
      window.LiveCompSession.mount();
    } else {
      setTimeout(bootstrap, 200);
    }
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    bootstrap();
  } else {
    document.addEventListener('DOMContentLoaded', bootstrap);
  }

  // SPA navigation watcher
  let lastHref = location.href;
  setInterval(() => {
    if (location.href !== lastHref) {
      lastHref = location.href;
      try {
        const fab = document.getElementById('lco-fab');
        const controls = document.getElementById('lco-controls');
        if (controls) controls.remove();
        if (fab) fab.remove();
        if (window.LiveCompSession) window.LiveCompSession.mount();
      } catch (e) {}
    }
  }, 1000);
})();
