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

## Architecture

- **iOS app** detects cards from screen-capture frames and sends cropped images to the backend.
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
7. ⏳ Sports card support
8. ⏳ Subscription + App Store release
