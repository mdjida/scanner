'use strict';

const _browser = typeof browser !== 'undefined' ? browser : chrome;

const urlInput = document.getElementById('backend-url');
const saveBtn = document.getElementById('save');
const testBtn = document.getElementById('test');
const statusEl = document.getElementById('status');

_browser.storage.local.get('backendUrl', result => {
  if (result.backendUrl) urlInput.value = result.backendUrl;
});

saveBtn.addEventListener('click', () => {
  const url = urlInput.value.trim().replace(/\/$/, '');
  _browser.storage.local.set({ backendUrl: url }, () => {
    statusEl.textContent = 'Saved';
    statusEl.className = 'ok';
  });
});

testBtn.addEventListener('click', () => {
  const url = urlInput.value.trim().replace(/\/$/, '');
  statusEl.textContent = 'Checking...';
  statusEl.className = '';
  fetch(`${url}/health`, { method: 'GET' })
    .then(r => {
      if (r.ok) {
        statusEl.textContent = 'Connected';
        statusEl.className = 'ok';
      } else {
        throw new Error(`HTTP ${r.status}`);
      }
    })
    .catch(err => {
      statusEl.textContent = err.message;
      statusEl.className = 'err';
    });
});
