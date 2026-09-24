# Live Comp Overlay

An iOS app (in progress) that detects Pokémon cards shown in livestreams (Whatnot/Twitch/YouTube) and overlays live market comps in the Dynamic Island / Lock Screen Live Activity.

## Quick start: Web demo

The fastest way to try the detection pipeline is the new browser demo. It uses the same Python backend as the iOS app.

```powershell
cd C:\Users\M\LiveCompOverlay\backend
.\start_server.ps1
start C:\Users\M\LiveCompOverlay\web\index.html
```

Drag a card image into the web page, click **Scan Card**, and watch the Dynamic Island mockup show the detected card + TCGdex prices.

For phone-browser testing, see [web/README.md](web/README.md).

## Android app

A native Android scanner is included in [`android/`](android/). It can run in two modes:

1. **Screen capture mode** — detects cards shown on your phone screen (Whatnot, Twitch, YouTube livestreams) and shows a floating overlay with the card + prices.
2. **Camera mode** — point the phone camera at a physical card.

Both modes send images to the same Python backend for identification. For now the backend runs on your PC; a cloud-hosted version can be added later.

### Run the backend on your PC

Double-click `start_backend.ps1` in this folder, or run from PowerShell:

```powershell
cd C:\Users\M\LiveCompOverlay
.\start_backend.ps1
```

The terminal prints the exact LAN URL, e.g. `http://192.168.1.119:8000`.

### Android setup

1. Open `android/` in Android Studio.
2. Build/run on your phone (phone must be on same Wi-Fi as PC).
3. In the app, go to **Settings** and enter the PC URL (or scan the QR code at `http://<pc-ip>:8000/pair.html`).
4. Tap **Start Screen Capture**, then switch to your streaming app.
5. A floating card overlay appears whenever a Pokémon card is recognized.

### Notes

- The backend unloads RapidOCR after each scan by default (`LCO_UNLOAD_OCR_AFTER_SCAN=1`) to keep 8 GB PCs from freezing under back-to-back scans. If you have more RAM, set `$env:LCO_UNLOAD_OCR_AFTER_SCAN="0"`.
- Screen capture requires Android 10+ and a foreground-service notification.
- Protected DRM streams may show a black screen and cannot be captured.

## Architecture

- **iOS / Android app** detects cards from screen-capture frames or camera and sends cropped images to the backend.
- **Backend** (Python/FastAPI) runs on your local PC for free. It identifies cards using CLIP + FAISS and returns TCGdex pricing.
- **Dynamic Island / Lock Screen Live Activity / floating overlay** shows the detected card, market price, and alternative candidates.
- **Web demo** runs in any browser for quick PC or phone testing.

## Data sources

- **Pokémon**: [TCGdex](https://tcgdex.dev) (free, no-key API for card data, images, and TCGplayer/Cardmarket pricing).
- **Sports**: SportsCardsPro + eBay sold listings (planned).

## Backend setup

See [backend/README.md](backend/README.md) for one-command setup and run instructions.

## iOS build

See [BUILD.md](BUILD.md) for the GitHub Actions + XcodeGen workflow and real-device instructions.

## Roadmap

1. ✅ Screen capture pipeline (ReplayKit extension → host app)
2. ✅ Card rectangle detection + normalization (Vision)
3. ✅ Pokémon card recognition via local backend (CLIP + FAISS + TCGdex)
4. ✅ Dynamic Island / Lock Screen Live Activity UI
5. ✅ Manual + auto scan modes with quota tracking
6. ✅ Web demo for browser-based testing
7. ✅ Android camera scanner
8. ⏳ Sports card support
9. ⏳ Subscription + App Store release

