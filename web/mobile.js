(function () {
  const $ = (id) => document.getElementById(id);

  const state = {
    stream: null,
    backendUrl: localStorage.getItem('lco_backend_url') || '',
    scanning: false,
  };

  const condLabels = { nm: 'NM', lp: 'LP', mp: 'MP', hp: 'HP', dmg: 'DMG' };

  async function getBackendUrl() {
    if (state.backendUrl) return state.backendUrl.replace(/\/$/, '');
    // Try auto-discovery from the same host (works if page is served by backend).
    const candidate = `${location.protocol}//${location.host}`;
    try {
      const r = await fetch(`${candidate}/health`, { method: 'GET', mode: 'cors' });
      if (r.ok) {
        state.backendUrl = candidate;
        localStorage.setItem('lco_backend_url', candidate);
        return candidate;
      }
    } catch (e) {
      // ignore
    }
    return '';
  }

  function setStatus(msg, isError = false) {
    const el = $('status');
    el.textContent = msg;
    el.className = isError ? 'error' : '';
  }

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      });
      state.stream = stream;
      const video = $('video');
      video.srcObject = stream;
      $('start').style.display = 'none';
      $('camera').style.display = 'flex';
      $('controls').style.display = 'flex';
      checkBackend();
    } catch (e) {
      alert('Camera failed: ' + e.message);
    }
  }

  function captureFrame() {
    const video = $('video');
    if (!video.videoWidth) return null;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
  }

  async function scan() {
    if (state.scanning) return;
    const url = await getBackendUrl();
    if (!url) {
      setStatus('No backend URL. Open Settings.', true);
      showSettings();
      return;
    }

    state.scanning = true;
    $('btn-scan').disabled = true;
    $('btn-scan').textContent = 'Scanning…';
    $('result').style.display = 'none';
    setStatus('Capturing frame…');

    const blob = await captureFrame();
    if (!blob) {
      setStatus('Camera not ready', true);
      state.scanning = false;
      $('btn-scan').disabled = false;
      $('btn-scan').textContent = 'Scan Card';
      return;
    }

    const form = new FormData();
    form.append('file', blob, 'card.png');

    try {
      setStatus('Identifying…');
      const res = await fetch(`${url}/identify?use_ocr=1`, {
        method: 'POST',
        body: form,
        mode: 'cors',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderResult(data);
      setStatus('Done');
    } catch (e) {
      setStatus('Scan failed: ' + e.message, true);
    } finally {
      state.scanning = false;
      $('btn-scan').disabled = false;
      $('btn-scan').textContent = 'Scan Card';
    }
  }

  function renderResult(data) {
    const best = data.best_match;
    const card = best?.card || {};
    const prices = data.prices_by_condition || {};

    let rows = '';
    ['nm', 'lp', 'mp', 'hp', 'dmg'].forEach((cond) => {
      const p = prices[cond];
      if (!p || p.price == null) return;
      const sym = p.currency === 'EUR' ? '€' : '$';
      const est = p.estimated ? ' *' : '';
      rows += `<div class="price-row"><span class="cond">${condLabels[cond]}${est}</span><span>${sym}${p.price.toFixed(2)}</span></div>`;
    });

    const confClass = `conf conf-${data.confidence || 'uncertain'}`;
    const verified = (data.verified_by || []).join(', ') || 'visual';

    $('result').innerHTML = `
      <div class="card">
        <div class="card-title">${escapeHtml(card.name || 'Unknown')}</div>
        <div class="card-meta">
          ${escapeHtml(card.set_name || '')} ${escapeHtml(card.local_id || '')} · ${escapeHtml(card.variant || 'Normal')}
        </div>
        <div class="card-meta">
          <span class="${confClass}">${escapeHtml(data.confidence || 'uncertain')}</span>
          <span> · verified by ${escapeHtml(verified)}</span>
        </div>
        ${rows ? `<div>${rows}</div>` : ''}
      </div>
    `;
    $('result').style.display = 'flex';
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  function showSettings() {
    $('camera').style.display = 'none';
    $('controls').style.display = 'none';
    $('settings').style.display = 'flex';
    $('backend-url').value = state.backendUrl || '';
  }

  function hideSettings() {
    $('settings').style.display = 'none';
    $('camera').style.display = 'flex';
    $('controls').style.display = 'flex';
  }

  async function checkBackend() {
    const url = await getBackendUrl();
    if (!url) return;
    try {
      const r = await fetch(`${url}/health`, { method: 'GET', mode: 'cors' });
      setStatus(r.ok ? 'Connected' : `HTTP ${r.status}`, !r.ok);
    } catch (e) {
      setStatus('Backend unreachable', true);
    }
  }

  async function discoverBackend() {
    $('settings-status').textContent = 'Searching…';
    // Try the current page's origin first.
    const origins = [`${location.protocol}//${location.host}`];
    // Common LAN prefixes for the current gateway.
    try {
      const candidate = location.hostname;
      if (/^192\.168\.\d+\.\d+$/.test(candidate)) {
        const prefix = candidate.replace(/\.\d+$/, '');
        for (let i = 1; i <= 254; i++) origins.push(`http://${prefix}.${i}:8000`);
      }
    } catch (e) {}

    for (const origin of origins) {
      try {
        const r = await fetch(`${origin}/health`, { method: 'GET', mode: 'cors' });
        if (r.ok) {
          state.backendUrl = origin;
          localStorage.setItem('lco_backend_url', origin);
          $('backend-url').value = origin;
          $('settings-status').textContent = `Found ${origin}`;
          return;
        }
      } catch (e) {}
    }
    $('settings-status').textContent = 'Not found. Type URL manually.';
  }

  $('btn-start').addEventListener('click', startCamera);
  $('btn-scan').addEventListener('click', scan);
  $('btn-settings').addEventListener('click', showSettings);
  $('btn-save').addEventListener('click', () => {
    state.backendUrl = $('backend-url').value.trim().replace(/\/$/, '');
    localStorage.setItem('lco_backend_url', state.backendUrl);
    hideSettings();
    checkBackend();
  });
  $('btn-discover').addEventListener('click', discoverBackend);
})();
