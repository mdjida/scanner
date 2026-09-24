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

A native Android scanner is included in [`android/`](android/). It connects to the same Python backend running on your local PC (recommended for heavy CLIP/OCR inference on low-RAM devices).

### 1. Start the PC backend

```powershell
cd C:\Users\M\LiveCompOverlay\backend
.\venv\Scripts\Activate.ps1
$env:HOST="0.0.0.0"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Pair your phone

Open `http://<pc-ip>:8000/mobile.html` in any browser on the same Wi-Fi; it shows a QR code. In the Android app tap **Settings → Scan QR**.

### 3. Scan cards

Tap **Scan Card** in the app. The PC backend returns the exact card, set, collector number, confidence, and TCGdex prices by condition.

### Notes

- The backend now unloads the RapidOCR ONNX session after each scan by default (`LCO_UNLOAD_OCR_AFTER_SCAN=1`) to keep 8 GB PCs from freezing under back-to-back scans.
- If you have more RAM, set `$env:LCO_UNLOAD_OCR_AFTER_SCAN="0"` for faster repeat scans.

## Architecture

- **iOS / Android app** detects cards from screen-capture frames or camera and sends cropped images to the backend.
- **Backend** (Python/FastAPI) runs on your local PC for free. It identifies cards using CLIP + FAISS and returns TCGdex pricing.
- **Dynamic Island / Lock Screen Live Activity** shows the detected card, market price, and alternative candidates.
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

