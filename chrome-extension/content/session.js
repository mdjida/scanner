'use strict';

(function () {
  if (window.LiveCompSession) return;

  const _browser = typeof browser !== 'undefined' ? browser : chrome;

  const S = { IDLE: 'idle', READY: 'ready', SELECTING: 'selecting', TAP_BUSY: 'tap_busy', AUTO_RUNNING: 'auto_running' };

  let sState = S.IDLE;
  let sRegion = null;
  let sSelectorUi = null;
  let sTapBusy = false;
  let sAutoRunning = false;
  let sAutoTimer = null;
  let sAutoBusy = false;
  let sPrevHash = null;
  let sLastSendMs = 0;

  const SCAN_PARAMS = {
    cooldown: 0.5,
    diffThreshold: 0.02,
    stationaryRefresh: 1.2,
    fps: 2,
    jpegQuality: 0.85,
    maxWidth: 800,
    centerCrop: { w: 0.80, h: 0.90 },
  };

  async function getBackendUrl() {
    return new Promise(resolve => {
      _browser.runtime.sendMessage({ type: 'GET_BACKEND_URL' }, response => {
        resolve(response?.url || 'http://localhost:8000');
      });
    });
  }

  async function identify(jpeg, useOcr = 1) {
    const url = (await getBackendUrl()).replace(/\/$/, '') + '/identify';
    const bin = LiveCompHash.base64ToArrayBuffer(jpeg);
    const form = new FormData();
    form.append('file', new Blob([bin], { type: 'image/jpeg' }), 'frame.jpg');
    form.append('use_ocr', String(useOcr));

    const res = await fetch(url, { method: 'POST', body: form });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  function mount() {
    if (document.getElementById('lco-fab')) return;
    const fab = document.createElement('div');
    fab.id = 'lco-fab';
    fab.innerHTML = '[scan]';
    fab.title = 'Live Comp Overlay ? scan cards';
    fab.addEventListener('click', activate);
    document.body.appendChild(fab);
  }

  function activate() {
    sState = S.READY;
    render();
  }

  function deactivate() {
    stopAuto();
    sState = S.IDLE;
    sRegion = null;
    const fab = document.getElementById('lco-fab');
    const controls = document.getElementById('lco-controls');
    if (controls) controls.remove();
    if (fab) fab.style.display = 'flex';
  }

  function render() {
    let controls = document.getElementById('lco-controls');
    if (!controls) {
      controls = document.createElement('div');
      controls.id = 'lco-controls';
      document.body.appendChild(controls);
    }
    const fab = document.getElementById('lco-fab');
    if (fab) fab.style.display = sState === S.IDLE ? 'flex' : 'none';

    if (sState === S.AUTO_RUNNING) {
      controls.innerHTML = `
        <div class="lco-pill lco-auto">
          <span class="lco-pulse"></span>
          <span>Auto Scanning</span>
          <button id="lco-stop" class="lco-btn">Stop</button>
        </div>`;
      controls.querySelector('#lco-stop')?.addEventListener('click', stopAuto);
      return;
    }

    if (sState === S.READY || sState === S.TAP_BUSY) {
      const hasRegion = !!sRegion;
      controls.innerHTML = `
        <div class="lco-pill">
          ${hasRegion ? `<button id="lco-clear-region" class="lco-btn">Clear Area</button>` : ''}
          <button id="lco-region" class="lco-btn" style="${hasRegion ? 'color:#fdba74;border-color:#f97316;' : ''}">${hasRegion ? '[target] Area Set' : '[target] Set Area'}</button>
          <button id="lco-tap" class="lco-btn" ${sTapBusy ? 'disabled' : ''}>${sTapBusy ? 'Scanning?' : '[scan] Tap Scan'}</button>
          <button id="lco-auto" class="lco-btn lco-btn-danger" ${sTapBusy ? 'disabled' : ''}>[auto] Auto</button>
          <button id="lco-hide" class="lco-btn">X</button>
        </div>`;
      controls.querySelector('#lco-hide')?.addEventListener('click', deactivate);
      controls.querySelector('#lco-region')?.addEventListener('click', startRegionSelect);
      controls.querySelector('#lco-clear-region')?.addEventListener('click', () => { sRegion = null; render(); });
      if (!sTapBusy) {
        controls.querySelector('#lco-tap')?.addEventListener('click', tapScan);
        controls.querySelector('#lco-auto')?.addEventListener('click', startAuto);
      }
    }
  }

  function startRegionSelect() {
    if (sSelectorUi) return;
    sState = S.SELECTING;
    render();

    const ui = document.createElement('div');
    sSelectorUi = ui;
    ui.id = 'lco-zone-overlay';
    ui.innerHTML = `
      <div id="lco-zone-backdrop"></div>
      <div id="lco-zone-hint">Drag a box over where cards are shown - Esc to cancel</div>
      <div id="lco-zone-rect"></div>`;
    document.body.appendChild(ui);

    const rect = ui.querySelector('#lco-zone-rect');
    const hint = ui.querySelector('#lco-zone-hint');
    let startX, startY, dragging = false;

    function cleanup() {
      window.removeEventListener('keydown', onKey, true);
      if (sSelectorUi) { sSelectorUi.remove(); sSelectorUi = null; }
      sState = S.READY;
      render();
    }

    function onKey(e) {
      if (e.key === 'Escape') cleanup();
    }
    window.addEventListener('keydown', onKey, true);

    const clampX = (x) => Math.min(Math.max(x, 0), window.innerWidth);
    const clampY = (y) => Math.min(Math.max(y, 0), window.innerHeight);

    ui.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      e.preventDefault();
      dragging = true;
      startX = clampX(e.clientX);
      startY = clampY(e.clientY);
    });

    ui.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const curX = clampX(e.clientX);
      const curY = clampY(e.clientY);
      rect.style.display = 'block';
      rect.style.left = Math.min(startX, curX) + 'px';
      rect.style.top = Math.min(startY, curY) + 'px';
      rect.style.width = Math.abs(curX - startX) + 'px';
      rect.style.height = Math.abs(curY - startY) + 'px';
    });

    ui.addEventListener('mouseup', (e) => {
      if (!dragging) return;
      dragging = false;
      const endX = clampX(e.clientX);
      const endY = clampY(e.clientY);
      if (Math.max(Math.abs(endX - startX), Math.abs(endY - startY)) < 5) { cleanup(); return; }

      const vw = window.innerWidth;
      const vh = window.innerHeight;
      sRegion = {
        x: Math.min(startX, endX) / vw,
        y: Math.min(startY, endY) / vh,
        w: Math.abs(endX - startX) / vw,
        h: Math.abs(endY - startY) / vh,
      };
      cleanup();
    });
  }

  async function tapScan() {
    if (sTapBusy) return;
    sTapBusy = true;
    sState = S.TAP_BUSY;
    render();
    LiveCompUI.showLoading();

    try {
      const frame = await LiveCompCapture.captureRegion({
        region: sRegion,
        centerCrop: sRegion ? null : SCAN_PARAMS.centerCrop,
        maxWidth: SCAN_PARAMS.maxWidth,
        jpegQuality: SCAN_PARAMS.jpegQuality,
      });
      if (!frame?.jpeg) throw new Error('Could not capture frame');
      const data = await identify(frame.jpeg, 1);
      LiveCompUI.renderResult(data);
    } catch (err) {
      LiveCompUI.showError(err.message);
    } finally {
      sTapBusy = false;
      sState = S.READY;
      render();
    }
  }

  async function startAuto() {
    if (sAutoRunning) return;
    sAutoRunning = true;
    sState = S.AUTO_RUNNING;
    sPrevHash = null;
    sLastSendMs = 0;
    render();

    const intervalMs = Math.round(1000 / SCAN_PARAMS.fps);
    sAutoTimer = setInterval(async () => {
      if (document.hidden || sTapBusy) return;
      if (sAutoBusy) return;
      sAutoBusy = true;
      try {
        const now = Date.now();
        if (sLastSendMs && now - sLastSendMs < SCAN_PARAMS.cooldown * 1000) return;

        const frame = await LiveCompCapture.captureRegion({
          region: sRegion,
          centerCrop: sRegion ? null : SCAN_PARAMS.centerCrop,
          maxWidth: SCAN_PARAMS.maxWidth,
          jpegQuality: SCAN_PARAMS.jpegQuality,
        });
        if (!frame?.jpeg) return;

        const hash = LiveCompHash.dHashFromCanvas(frame.canvas);
        const diffThresholdBits = SCAN_PARAMS.diffThreshold * 64;
        const isStationary = sPrevHash !== null && LiveCompHash.hammingDistance(hash, sPrevHash) < diffThresholdBits;
        if (isStationary && now - sLastSendMs < SCAN_PARAMS.stationaryRefresh * 1000) return;

        const data = await identify(frame.jpeg, 0);
        sPrevHash = hash;
        sLastSendMs = Date.now();
        if (data?.best_match?.score >= 0.85) {
          LiveCompUI.renderResult(data);
        }
      } catch (err) {
        console.error('[LiveComp] auto scan error:', err);
      } finally {
        sAutoBusy = false;
      }
    }, intervalMs);
  }

  function stopAuto() {
    sAutoRunning = false;
    if (sAutoTimer) { clearInterval(sAutoTimer); sAutoTimer = null; }
    if (sState === S.AUTO_RUNNING) { sState = S.READY; render(); }
  }

  window.LiveCompSession = {
    mount,
    activate,
    deactivate,
  };
})();
