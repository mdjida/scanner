# Browser extension end-to-end test

This test loads the unpacked Chrome/Edge extension into Playwright Chromium,
opens a local test page with a live video element, and verifies both
**Tap Scan** and **Auto Scan** hit the backend `POST /identify` endpoint.

## Prerequisites

1. Start the backend:
   ```powershell
   cd C:\Users\M\LiveCompOverlay\backend
   .\start_server.ps1
   ```
2. Serve the test page:
   ```powershell
   cd C:\Users\M\LiveCompOverlay\backend
   .\venv\Scripts\Activate.ps1
   python -m http.server 9000 --directory C:\Users\M\LiveCompOverlay\web
   ```
3. Install Playwright in a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install playwright
   python -m playwright install chromium
   ```

## Run

```powershell
cd C:\Users\M\LiveCompOverlay\tests\browser-extension
python test_ext.py
```

## What it checks

- The `[scan]` FAB appears on the test page.
- Clicking it reveals the **Tap Scan** control.
- Tap Scan sends a video frame to `POST /identify` and gets a result.
- The floating result panel renders the detected card.
- **Auto Scan** repeatedly triggers `/identify` requests.
- No console errors occur.

## Notes

- The test uses `http://localhost:9000/test-card.html`, which is why
  `*://localhost:*/*` is included in `chrome-extension/manifest.json`.
- You can remove the localhost match before publishing to the Chrome Web Store.
