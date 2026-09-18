'use strict';

(function () {
  if (window.__liveCompBootstrapped) return;
  window.__liveCompBootstrapped = true;

  function bootstrap() {
    if (window.LiveCompSession) {
      try {
        window.LiveCompSession.mount();
      } catch (e) {
        console.error('[LiveComp] mount failed:', e);
      }
      return;
    }
    if (!bootstrap.attempts) bootstrap.attempts = 0;
    bootstrap.attempts += 1;
    if (bootstrap.attempts < 50) {
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
        const root = document.getElementById('lco-root');
        const zone = document.getElementById('lco-zone-overlay');
        if (controls) controls.remove();
        if (fab) fab.remove();
        if (root) root.remove();
        if (zone) zone.remove();
        if (window.LiveCompSession) {
          window.LiveCompSession.deactivate();
          window.LiveCompSession.mount();
        }
      } catch (e) {
        console.error('[LiveComp] SPA watcher error:', e);
      }
    }
  }, 1000);
})();
