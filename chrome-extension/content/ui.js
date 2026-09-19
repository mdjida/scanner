'use strict';

(function () {
  if (window.LiveCompUI) return;

  const POSITION_COLORS = {
    steal: '#22c55e',
    great: '#84cc16',
    good: '#eab308',
    fair: '#9ca3af',
    overpriced: '#ef4444',
  };

  const CONDITION_LABELS = { nm: 'NM', lp: 'LP', mp: 'MP', hp: 'HP', dmg: 'DMG' };

  function formatCurrency(value) {
    if (value == null || isNaN(value)) return 'N/A';
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  }

  function formatScore(score) {
    if (score == null) return 'N/A';
    return `${Math.round(score * 100)}%`;
  }

  function bestPrice(prices) {
    if (!prices || !prices.length) return null;
    const preferred = ['market', 'mid', 'avg', 'low', 'trend'];
    for (const type of preferred) {
      const p = prices.find(x => x.price_type === type && x.price != null);
      if (p) return { value: p.price, type, source: p.price_source };
    }
    return null;
  }

  function conditionTable(pricesByCondition) {
    if (!pricesByCondition) return '';
    const order = ['nm', 'lp', 'mp', 'hp'];
    const rows = order
      .map(cond => {
        const p = pricesByCondition[cond];
        if (!p || p.price == null) return '';
        return `<tr>
          <td class="lco-cond">${CONDITION_LABELS[cond] || cond}${p.estimated ? ' *' : ''}</td>
          <td class="lco-cond-price">${formatCurrency(p.price)}</td>
        </tr>`;
      })
      .join('');
    if (!rows) return '';
    return `<div class="lco-section">Conditions</div>
      <table class="lco-cond-table">
        <thead><tr><th>Cond</th><th>Price</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      ${Object.values(pricesByCondition).some(p => p.estimated) ? '<div class="lco-est-note">* estimated from market price</div>' : ''}`;
  }

  function confidenceBadge(confidence) {
    if (!confidence) return '';
    const cls = confidence === 'high' ? 'lco-conf-high' : confidence === 'medium' ? 'lco-conf-medium' : confidence === 'low' ? 'lco-conf-low' : 'lco-conf-uncertain';
    return `<div class="lco-confidence ${cls}">${String(confidence).toUpperCase()}</div>`;
  }

  function makeDraggable(el) {
    let isDragging = false, startX, startY, startLeft, startTop;
    const header = el.querySelector('.lco-panel-header');
    if (!header) return;
    header.addEventListener('mousedown', (e) => {
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      const rect = el.getBoundingClientRect();
      startLeft = rect.left;
      startTop = rect.top;
      document.body.style.userSelect = 'none';
    });
    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      el.style.left = `${Math.max(0, Math.min(window.innerWidth - el.offsetWidth, startLeft + e.clientX - startX))}px`;
      el.style.top = `${Math.max(0, Math.min(window.innerHeight - el.offsetHeight, startTop + e.clientY - startY))}px`;
      el.style.right = 'auto';
      el.style.bottom = 'auto';
    });
    window.addEventListener('mouseup', () => {
      if (isDragging) { isDragging = false; document.body.style.userSelect = ''; }
    });
  }

  function showLoading() {
    let panel = document.getElementById('lco-root');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'lco-root';
      document.body.appendChild(panel);
      makeDraggable(panel);
    }
    panel.innerHTML = `
      <div class="lco-panel">
        <div class="lco-panel-header">
          <span class="lco-header-brand">Live Comp</span>
          <button id="lco-close" class="lco-close">x</button>
        </div>
        <div class="lco-panel-body" id="lco-body">
          <div class="lco-loading">
            <div class="lco-spinner"></div>
            <div>Identifying card?</div>
          </div>
        </div>
      </div>
    `;
    panel.querySelector('#lco-close')?.addEventListener('click', () => panel.remove());
    return panel;
  }

  function renderResult(data) {
    const best = data.best_match;
    const card = best?.card || {};
    const prices = card.prices || [];
    const price = bestPrice(prices);
    const panel = showLoading();
    const body = panel.querySelector('#lco-body');

    const cardImg = card.image_url
      ? `<div class="lco-card-img-wrap">
           <img class="lco-card-img" src="${card.image_url}" alt="${card.name || ''}" onerror="this.style.display='none'" />
         </div>`
      : '';

    let candidatesHtml = '';
    const candidates = (data.candidates || []).slice(1, 4);
    if (candidates.length > 0) {
      candidatesHtml = `<div class="lco-section">Other possible matches</div>
        <ul class="lco-candidates">${candidates.map(c => {
          const cc = c.card || {};
          const cp = bestPrice(cc.prices || []);
          return `<li>
            <div>
              <div class="lco-cand-name">${cc.name || 'Unknown'}</div>
              <div class="lco-cand-meta">${cc.set_name || ''} ${cc.local_id || ''} - ${cp ? formatCurrency(cp.value) : 'N/A'}</div>
            </div>
            <span class="lco-cand-score">${formatScore(c.score)}</span>
          </li>`;
        }).join('')}</ul>`;
    }

    body.innerHTML = `
      ${cardImg}
      ${confidenceBadge(data.confidence)}
      <div class="lco-card-title">${card.name || 'Unknown'}</div>
      <div class="lco-card-subtitle">${card.set_name || ''} ${card.local_id || ''} - ${card.variant || 'Normal'}</div>
      <div class="lco-price">${price ? formatCurrency(price.value) : 'N/A'}</div>
      <div class="lco-source">${price ? `${price.source} - ${price.type}` : ''}</div>
      ${conditionTable(data.prices_by_condition)}
      ${best?.score != null ? `<div class="lco-score" style="background:${scoreColor(best.score)}">${formatScore(best.score)}</div>` : ''}
      ${candidatesHtml}
    `;
  }

  function scoreColor(score) {
    if (score >= 0.95) return '#22c55e';
    if (score >= 0.90) return '#eab308';
    return '#f97316';
  }

  function showError(message) {
    const panel = showLoading();
    const body = panel.querySelector('#lco-body');
    body.innerHTML = `<div class="lco-error">
      <div>[X]</div>
      <div>${message}</div>
    </div>`;
  }

  window.LiveCompUI = { renderResult, showError, showLoading, makeDraggable, formatCurrency, formatScore, bestPrice };
})();
