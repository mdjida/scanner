# Live Comp Overlay - Chrome/Edge Extension

A browser extension that detects cards in livestreams (Whatnot, Twitch, YouTube) and shows live market prices from your local backend.

## How it works

1. The extension injects a [scan] scan button onto supported livestream sites.
2. You click the button to open the scan controls.
3. **Tap Scan** sends one video frame to your backend `POST /identify`.
4. **Auto Scan** repeatedly captures frames, compares them with a dHash, and only sends changed frames.
5. You can draw a scan area over the part of the video where cards appear.
6. The backend returns the detected card + prices; the extension renders a floating panel.

## Install

1. Open Edge or Chrome and go to the extensions page:
   - Edge: `edge://extensions/`
   - Chrome: `chrome://extensions/`
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select this `chrome-extension` folder.
5. The extension icon will appear in your toolbar.

## Configure

1. Click the extension icon in the toolbar.
2. Set the **Backend URL** to your local backend:
   - PC only: `http://localhost:8000`
   - Network/phone use: `http://YOUR_PC_IP:8000`
3. Click **Test Connection**.

## Start the backend

```powershell
cd C:\Users\M\LiveCompOverlay\backend
.\start_server.ps1
```

## Use

1. Open [Whatnot](https://www.whatnot.com), [Twitch](https://www.twitch.tv), or [YouTube](https://www.youtube.com) and start a stream.
2. Click the [scan] Live Comp button that appears on the page.
3. Optional: click **Set Area** and drag a box over where cards are shown.
4. Click **Tap Scan** for one shot, or **Auto** for continuous scanning.
5. The floating panel shows the detected card and price.

## Supported sites

- whatnot.com
- twitch.tv
- youtube.com
- ebay.com (search/listing overlays are planned)

## Files

- `manifest.json` - extension config
- `background.js` - service worker, tab capture, storage
- `content/capture.js` - video element + tab screenshot capture
- `content/hash.js` - dHash + Hamming distance for frame diffing
- `content/ui.js` - floating result panel
- `content/session.js` - FAB, region selector, tap/auto scan logic
- `content/livestream.js` - bootstrap + SPA navigation watcher
- `popup/popup.html` + `popup/popup.js` - settings popup
- `styles/panel.css` - all UI styling

## Troubleshooting

### "Could not capture frame"

- Make sure the video is playing.
- Try drawing a smaller/larger scan area.
- On Twitch/YouTube, the extension may fall back to tab screenshots which require the tab to be visible.

### Backend test fails

- Make sure the backend is running.
- Check Windows Firewall is not blocking port 8000.
- If using a PC IP, make sure the browser is on the same network as the backend PC.

### Extension does not appear on the page

- Refresh the page after loading the extension.
- Check the browser console for CSP or injection errors.
