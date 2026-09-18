# Build & Run Guide

## 1. Backend (run on your Windows PC)

### Setup (one time)

```powershell
cd C:\Users\M\LiveCompOverlay\backend
.\setup.ps1
```

### Start the backend

```powershell
.\start_server.ps1
```

Server runs at `http://0.0.0.0:8000`. Find your PC's local IP and enter it in the iOS app's **Backend** settings, e.g. `http://192.168.1.100:8000`.

### Ingest cards for testing

```powershell
# Fast smoke test — just Charizard
venv\Scripts\Activate.ps1
python cli.py --smoke-test

# A few sets
python cli.py 3

# All sets (takes a long time)
python cli.py
```

## 2. iOS app (requires a Mac)

### Install dependencies

```bash
# On Mac
brew install xcodegen
```

### Generate Xcode project

```bash
cd /path/to/LiveCompOverlay
xcodegen generate
```

### Configure signing & capabilities

1. Open `LiveCompOverlay.xcodeproj` in Xcode 15+.
2. Select each target and set your **Team** and unique **Bundle Identifier**.
3. Add the **App Groups** capability to all three targets:
   - `LiveCompOverlay`
   - `LiveCompOverlayBroadcast`
   - `LiveCompOverlayWidget`
   Use the group `group.com.livecompoverlay.shared`.
4. Add the **Broadcast Upload Extension** capability to `LiveCompOverlayBroadcast` (should already be in Info.plist).
5. Add the **Live Activities** capability to `LiveCompOverlay` and `LiveCompOverlayWidget`.

### Build & run

1. Select a real iOS device (screen-capture extensions don't work well on the simulator).
2. Build and run.
3. Grant screen-recording permission when prompted.
4. Switch to Whatnot/Twitch/YouTube and watch a stream.
5. The Dynamic Island or Lock Screen shows detected cards + TCGdex prices.

### If the app can't reach the backend

- Make sure iPhone and PC are on the **same Wi-Fi**.
- In the iOS app, go to **Backend** settings and set the URL to your PC's local IP.
- Tap **Test Connection**.
- Check Windows Firewall is not blocking port `8000`.

## 3. Pre-flight verification (before using a Mac)

You can verify the backend end-to-end from Windows:

```powershell
cd C:\Users\M\LiveCompOverlay\backend
.\venv\Scripts\Activate.ps1
python cli.py --smoke-test  # ingests Charizard
python - <<'PY'
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app
client = TestClient(app)
print(client.get('/health').json())
print(client.get('/catalog/status').json())
img = Path('smoke_card.png').read_bytes()
resp = client.post('/identify', files={'file': ('card.png', img, 'image/png')})
print(resp.status_code)
print(resp.json())
PY
```

## 4. Known limitations / likely iOS compile fixes

- **Sports cards**: not implemented yet.
- **Full catalog ingestion**: can take hours for all Pokémon sets; use `--smoke-test` or `cli.py 3` for quick testing.
- **Subscription / paywall**: stubbed; integrate StoreKit or RevenueCat later.
- **SwiftUI `.foregroundStyle(.green)`**: converted to `Color.green` for iOS 16 compatibility.
- **ForEach over `.prefix()`**: converted to `Array(...)` so SwiftUI gets `RandomAccessCollection` conformance.
