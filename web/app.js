const backendInput = document.getElementById('backend-url');
const testBackendButton = document.getElementById('test-backend');
const backendStatus = document.getElementById('backend-status');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const browseButton = document.getElementById('browse-button');
const previewContainer = document.getElementById('preview-container');
const previewImage = document.getElementById('preview-image');
const scanButton = document.getElementById('scan-button');

const resultEmpty = document.getElementById('result-empty');
const resultContent = document.getElementById('result-content');
const cardName = document.getElementById('card-name');
const cardVariant = document.getElementById('card-variant');
const cardSet = document.getElementById('card-set');
const cardPrice = document.getElementById('card-price');
const cardSource = document.getElementById('card-source');
const scoreBadge = document.getElementById('score-badge');
const candidatesList = document.getElementById('candidates-list');

const dynamicIsland = document.querySelector('.dynamic-island');
const islandStatus = document.getElementById('island-status');
const islandDetail = document.getElementById('island-detail');
const islandExpanded = document.getElementById('island-expanded');
const expandedName = document.getElementById('expanded-name');
const expandedSet = document.getElementById('expanded-set');
const expandedVariant = document.getElementById('expanded-variant');
const expandedPrice = document.getElementById('expanded-price');
const expandedScore = document.getElementById('expanded-score');
const expandedCandidates = document.getElementById('expanded-candidates');

let currentFile = null;

function getBackendUrl() {
  return backendInput.value.trim().replace(/\/$/, '');
}

testBackendButton.addEventListener('click', async () => {
  backendStatus.textContent = 'Checking...';
  backendStatus.className = 'status';
  try {
    const res = await fetch(`${getBackendUrl()}/health`, { method: 'GET' });
    if (res.ok) {
      backendStatus.textContent = 'Connected';
      backendStatus.className = 'status ok';
    } else {
      backendStatus.textContent = `HTTP ${res.status}`;
      backendStatus.className = 'status error';
    }
  } catch (err) {
    backendStatus.textContent = 'Unreachable';
    backendStatus.className = 'status error';
  }
});

browseButton.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
  if (e.target.files && e.target.files[0]) {
    handleFile(e.target.files[0]);
  }
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    handleFile(e.dataTransfer.files[0]);
  }
});

function handleFile(file) {
  if (!file.type.startsWith('image/')) {
    alert('Please upload an image file.');
    return;
  }
  currentFile = file;
  const url = URL.createObjectURL(file);
  previewImage.src = url;
  previewContainer.classList.remove('hidden');
  scanButton.disabled = false;
  setIslandScanning(false);
}

scanButton.addEventListener('click', async () => {
  if (!currentFile) return;
  scanButton.disabled = true;
  scanButton.textContent = 'Scanning...';
  setIslandScanning(true);

  try {
    const formData = new FormData();
    formData.append('file', currentFile);

    const res = await fetch(`${getBackendUrl()}/identify`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    renderResult(data);
    setIslandDetected(data);
  } catch (err) {
    alert(`Scan failed: ${err.message}`);
    islandStatus.textContent = 'Scan failed';
    islandDetail.textContent = err.message;
    dynamicIsland.classList.add('detected');
  } finally {
    scanButton.disabled = false;
    scanButton.textContent = 'Scan Card';
  }
});

function renderResult(data) {
  const best = data.best_match;
  const card = best?.card || {};
  const variant = card.variant || 'Normal';
  const market = bestPrice(card.prices || []);

  cardName.textContent = card.name || 'Unknown';
  cardVariant.textContent = variant;
  cardSet.textContent = `${card.set_name || ''} ${card.local_id || ''}`.trim() || 'Unknown set';
  cardPrice.textContent = market.display;
  cardSource.textContent = market.source ? `Source: ${market.source}` : '';
  scoreBadge.textContent = formatScore(best.score);

  resultEmpty.classList.add('hidden');
  resultContent.classList.remove('hidden');

  candidatesList.innerHTML = '';
  const candidates = (data.candidates || []).slice(1, 4);
  candidates.forEach((candidate) => {
    const c = candidate.card || {};
    const price = bestPrice(c.prices || []);
    const li = document.createElement('li');
    li.innerHTML = `
      <div>
        <div class="candidate-name">${c.name || 'Unknown'}</div>
        <div class="candidate-meta">${c.set_name || ''} ${c.local_id || ''} · ${price.display}</div>
      </div>
      <span class="candidate-score">${formatScore(candidate.score)}</span>
    `;
    candidatesList.appendChild(li);
  });
}

function setIslandScanning(active) {
  dynamicIsland.classList.remove('detected');
  islandExpanded.classList.add('hidden');
  if (active) {
    dynamicIsland.classList.add('scanning');
    islandStatus.textContent = 'Scanning...';
    islandDetail.textContent = 'Detecting card';
  } else {
    dynamicIsland.classList.remove('scanning');
    islandStatus.textContent = 'Ready to scan';
    islandDetail.textContent = 'Upload a card';
  }
}

function setIslandDetected(data) {
  const best = data.best_match;
  const card = best?.card || {};
  const market = bestPrice(card.prices || []);

  expandedName.textContent = card.name || 'Unknown';
  expandedSet.textContent = `${card.set_name || ''} ${card.local_id || ''}`.trim();
  expandedVariant.textContent = card.variant || 'Normal';
  expandedPrice.textContent = market.display;
  expandedScore.textContent = formatScore(best.score);
  expandedScore.className = 'score badge small';

  expandedCandidates.innerHTML = '';
  const candidates = (data.candidates || []).slice(1, 3);
  candidates.forEach((candidate) => {
    const c = candidate.card || {};
    const price = bestPrice(c.prices || []);
    const li = document.createElement('li');
    li.innerHTML = `
      <span>${c.name || 'Unknown'}</span>
      <span>${formatScore(candidate.score)} · ${price.display}</span>
    `;
    expandedCandidates.appendChild(li);
  });

  dynamicIsland.classList.remove('scanning');
  dynamicIsland.classList.add('detected');
  islandStatus.textContent = card.name || 'Unknown';
  islandDetail.textContent = `${card.set_name || ''} · ${market.display}`.trim();
  islandExpanded.classList.remove('hidden');
}

function bestPrice(prices) {
  const preferred = ['market', 'mid', 'avg', 'low', 'trend'];
  for (const type of preferred) {
    const p = prices.find((x) => x.price_type === type && x.price != null);
    if (p) {
      const symbol = p.currency === 'EUR' ? '€' : '$';
      return {
        display: `${symbol}${p.price.toFixed(2)}`,
        source: `${p.price_source} · ${type}`,
      };
    }
  }
  return { display: 'N/A', source: '' };
}

function formatScore(score) {
  if (score == null) return 'N/A';
  return `${Math.round(score * 100)}%`;
}
