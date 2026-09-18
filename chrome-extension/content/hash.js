'use strict';

(function () {
  if (window.LiveCompHash) return;

  const _dhashCanvas = document.createElement('canvas');
  _dhashCanvas.width = 9;
  _dhashCanvas.height = 8;
  const _dhashCtx = _dhashCanvas.getContext('2d', { willReadFrequently: true });

  function dHashFromCanvas(sourceCanvas) {
    _dhashCtx.drawImage(sourceCanvas, 0, 0, 9, 8);
    const px = _dhashCtx.getImageData(0, 0, 9, 8).data;
    let hash = 0n;
    for (let row = 0; row < 8; row++) {
      for (let col = 0; col < 8; col++) {
        const i = (row * 9 + col) * 4;
        const gray = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];
        const grayNext = 0.299 * px[i + 4] + 0.587 * px[i + 5] + 0.114 * px[i + 6];
        hash = (hash << 1n) | (gray < grayNext ? 1n : 0n);
      }
    }
    return hash;
  }

  function hammingDistance(a, b) {
    let x = a ^ b;
    let dist = 0;
    while (x) { dist += Number(x & 1n); x >>= 1n; }
    return dist;
  }

  function base64ToArrayBuffer(b64) {
    const bin = atob(b64);
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    return buf.buffer;
  }

  window.LiveCompHash = { dHashFromCanvas, hammingDistance, base64ToArrayBuffer };
})();
