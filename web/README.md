# Live Comp Overlay — Web Demo

A browser-based demo of the card-detection overlay. Upload a screenshot and see the detected Pokémon card + market prices in both a result panel and a Dynamic Island-style phone mockup.

## Run the backend

Make sure the Python backend is running on your PC:

```powershell
cd C:\Users\M\LiveCompOverlay\backend
.\start_server.ps1
```

The backend will be available at `http://localhost:8000`.

## Run the web demo

### Option 1: Open directly (recommended)

1. Open `web/index.html` in any browser:
   ```powershell
   start C:\Users\M\LiveCompOverlay\web\index.html
   ```
   Or double-click the file.
2. Keep the backend running.
3. Drag a card image onto the page, or click **Choose Image**.
4. Click **Scan Card**.

### Option 2: Serve via a tiny HTTP server

If your browser blocks local file access to the backend, run a small server from the `web` folder:

```powershell
cd C:\Users\M\LiveCompOverlay\web
python -m http.server 8080
```

Then open http://localhost:8080.

## Test from a phone

1. Find your PC's local IP address:
   ```powershell
   ipconfig
   ```
   Example: `192.168.1.100`
2. In the web demo, change the **Backend URL** to:
   ```
   http://192.168.1.100:8000
   ```
3. Open `http://192.168.1.100:8080` (or wherever you served the web demo) in Safari or Chrome on your phone.
   Make sure the phone is on the same Wi-Fi as your PC.
4. Tap **Test Connection**.
5. Upload or take a photo of a card and tap **Scan Card**.

## Expected behavior

- The left panel shows the uploaded image.
- The middle panel shows the best matched card, price, confidence, and up to 3 alternate candidates.
- The right panel shows a phone mockup with a Dynamic Island that expands to display the detected card.

## Troubleshooting

### "Unreachable" when testing backend

- Make sure the backend is running.
- Check Windows Firewall is not blocking port `8000`.
- If testing from a phone, make sure both devices are on the same Wi-Fi.
- Try visiting `http://YOUR_PC_IP:8000/health` from the phone browser.

### CORS error in browser console

The backend should already allow all origins. If you still see CORS errors, restart the backend.
