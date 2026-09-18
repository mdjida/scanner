'use strict';

(function () {
  if (window.LiveCompCapture) return;

  const _browser = typeof browser !== 'undefined' ? browser : chrome;

  // captureVisibleTab quota is ~2 calls/sec per tab; stay safely under it.
  const TAB_CAPTURE_MIN_INTERVAL_MS = 600;
  let _lastTabCaptureMs = 0;

  function findVideo() {
    const usable = (v) => v && v.videoWidth > 0 && v.readyState >= 2;
    try {
      const v = document.querySelector('video');
      if (usable(v)) return { video: v, offset: { x: 0, y: 0 } };
    } catch (e) {}
    const frames = document.querySelectorAll('iframe');
    for (const frame of frames) {
      try {
        const doc = frame.contentDocument || frame.contentWindow?.document;
        if (!doc) continue;
        const v = doc.querySelector('video');
        if (usable(v)) {
          const r = frame.getBoundingClientRect();
          return { video: v, offset: { x: r.left, y: r.top } };
        }
      } catch (e) {
        // Cross-origin iframe ? skip
      }
    }
    return null;
  }

  function videoContentRect(video, offset) {
    const r = video.getBoundingClientRect();
    if (!r.width || !r.height || !video.videoWidth || !video.videoHeight) return null;
    const left = r.left + (offset?.x || 0);
    const top = r.top + (offset?.y || 0);
    const ar = video.videoWidth / video.videoHeight;
    const ea = r.width / r.height;
    let fit = 'contain';
    try {
      const win = video.ownerDocument.defaultView || window;
      fit = win.getComputedStyle(video).objectFit || 'contain';
    } catch (e) {}

    let w = r.width, h = r.height, ox = 0, oy = 0;
    if (fit === 'cover') {
      if (ea > ar) { h = r.width / ar; oy = (r.height - h) / 2; }
      else { w = r.height * ar; ox = (r.width - w) / 2; }
    } else if (fit !== 'fill') {
      if (ea > ar) { w = r.height * ar; ox = (r.width - w) / 2; }
      else { h = r.width / ar; oy = (r.height - h) / 2; }
    }
    return { left: left + ox, top: top + oy, width: w, height: h };
  }

  function captureFromVideo(video, crop, maxWidth, quality) {
    const scale = Math.min(1, maxWidth / Math.max(crop.w, 1));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(crop.w * scale));
    canvas.height = Math.max(1, Math.round(crop.h * scale));
    canvas.getContext('2d').drawImage(
      video,
      crop.x, crop.y, crop.w, crop.h,
      0, 0, canvas.width, canvas.height
    );
    const dataUrl = canvas.toDataURL('image/jpeg', quality);
    const jpeg = dataUrl.split(',')[1] || null;
    return jpeg ? { jpeg, canvas } : null;
  }

  function captureFromTab(viewportRect, maxWidth, quality) {
    return new Promise((resolve) => {
      const now = Date.now();
      if (now - _lastTabCaptureMs < TAB_CAPTURE_MIN_INTERVAL_MS) return resolve(null);
      _lastTabCaptureMs = now;
      try {
        _browser.runtime.sendMessage({ type: 'CAPTURE_TAB' }, (resp) => {
          if (_browser.runtime.lastError || !resp?.ok) return resolve(null);
          const img = new Image();
          img.onload = () => {
            try {
              const dpr = window.devicePixelRatio || 1;
              const vw = window.innerWidth, vh = window.innerHeight;
              let r = viewportRect || { x1: 0, y1: 0, x2: vw, y2: vh };
              r = {
                x1: Math.max(0, Math.min(r.x1, vw)),
                y1: Math.max(0, Math.min(r.y1, vh)),
                x2: Math.max(0, Math.min(r.x2, vw)),
                y2: Math.max(0, Math.min(r.y2, vh)),
              };
              const sw = (r.x2 - r.x1) * dpr, sh = (r.y2 - r.y1) * dpr;
              if (sw < 8 || sh < 8) return resolve(null);
              const scale = Math.min(1, maxWidth / Math.max(sw, 1));
              const canvas = document.createElement('canvas');
              canvas.width = Math.max(1, Math.round(sw * scale));
              canvas.height = Math.max(1, Math.round(sh * scale));
              canvas.getContext('2d').drawImage(
                img, r.x1 * dpr, r.y1 * dpr, sw, sh, 0, 0, canvas.width, canvas.height
              );
              const jpeg = canvas.toDataURL('image/jpeg', quality).split(',')[1] || null;
              resolve(jpeg ? { jpeg, canvas } : null);
            } catch { resolve(null); }
          };
          img.onerror = () => resolve(null);
          img.src = resp.dataUrl;
        });
      } catch { resolve(null); }
    });
  }

  async function captureRegion(opts = {}) {
    const maxWidth = opts.maxWidth || 800;
    const quality = opts.jpegQuality || 0.85;

    const found = findVideo();
    if (found) {
      const video = found.video;
      const srcW = video.videoWidth, srcH = video.videoHeight;
      let crop;
      if (opts.region) {
        crop = {
          x: opts.region.x * srcW, y: opts.region.y * srcH,
          w: opts.region.w * srcW, h: opts.region.h * srcH,
        };
      } else if (opts.centerCrop) {
        const w = srcW * (opts.centerCrop.w || 0.80);
        const h = srcH * (opts.centerCrop.h || 0.90);
        crop = { x: (srcW - w) / 2, y: (srcH - h) / 2, w, h };
      } else {
        crop = { x: 0, y: 0, w: srcW, h: srcH };
      }
      try {
        const out = captureFromVideo(video, crop, maxWidth, quality);
        if (out) return out;
      } catch (e) {
        console.warn('[LiveComp] video capture failed:', e?.name, e?.message);
        // SecurityError ? tainted canvas. Fall through to tab capture.
      }
      const content = videoContentRect(video, found.offset);
      if (content) {
        let r = {
          x1: content.left, y1: content.top,
          x2: content.left + content.width, y2: content.top + content.height,
        };
        if (opts.region) {
          r = {
            x1: content.left + opts.region.x * content.width,
            y1: content.top + opts.region.y * content.height,
            x2: content.left + (opts.region.x + opts.region.w) * content.width,
            y2: content.top + (opts.region.y + opts.region.h) * content.height,
          };
        } else if (opts.centerCrop) {
          const cw = content.width * (opts.centerCrop.w || 0.80);
          const ch = content.height * (opts.centerCrop.h || 0.90);
          r = {
            x1: content.left + (content.width - cw) / 2,
            y1: content.top + (content.height - ch) / 2,
            x2: content.left + (content.width + cw) / 2,
            y2: content.top + (content.height + ch) / 2,
          };
        }
        return captureFromTab(r, maxWidth, quality);
      }
    }

    console.warn('[LiveComp] no usable video found, falling back to tab capture');
    return captureFromTab(opts.viewportRegion || null, maxWidth, quality);
  }

  function hasDirectVideo() {
    return !!findVideo();
  }

  window.LiveCompCapture = { findVideo, videoContentRect, captureRegion, hasDirectVideo };
})();
