'use strict';

const _browser = typeof browser !== 'undefined' ? browser : chrome;

_browser.runtime.onInstalled.addListener(() => {
  console.log('[LiveComp] Extension installed');
});

_browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CAPTURE_TAB') {
    _browser.tabs.captureVisibleTab(null, { format: 'jpeg', quality: 85 })
      .then(dataUrl => sendResponse({ ok: true, dataUrl }))
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message.type === 'GET_BACKEND_URL') {
    _browser.storage.local.get('backendUrl').then(result => {
      sendResponse({ url: result.backendUrl || 'http://localhost:8000' });
    });
    return true;
  }

  if (message.type === 'SET_BACKEND_URL') {
    _browser.storage.local.set({ backendUrl: message.url }).then(() => {
      sendResponse({ ok: true });
    });
    return true;
  }
});
