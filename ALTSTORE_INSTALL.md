# Install on iPhone with AltStore (Free Apple ID)

This guide uses **AltStore** and a free Apple ID to install the app on your iPhone without paying the Apple Developer fee.

## What works with a free Apple ID

- The main app UI and backend connection work.
- You can manually scan cards from the app.
- The ReplayKit screen-capture extension and Dynamic Island Live Activity may fail or require extra entitlements. We will test after install.

## What you need

- Windows PC with AltServer installed (https://altstore.io)
- iPhone connected to the same Wi-Fi as your PC
- USB cable for the first install
- Free Apple ID

## Step 1: Create a free Apple Developer account

1. Go to https://developer.apple.com/account/
2. Sign in with your Apple ID.
3. Agree to the developer terms.
4. No payment is required for a free account.

## Step 2: Install AltStore on your iPhone

1. Open **AltServer** on your Windows PC.
2. Connect your iPhone to the PC with a USB cable.
3. Make sure iTunes/Finder recognizes the device and you tap **Trust This Computer** on the iPhone.
4. In AltServer, click the tray icon → **Install AltStore** → select your iPhone.
5. Enter your Apple ID and password when prompted.
6. After AltStore installs on your iPhone, open it and trust the developer profile in:
   **Settings → General → VPN & Device Management**.

## Step 3: Download the unsigned IPA

1. Go to https://github.com/mdjida/scanner/actions
2. Click the latest successful **iOS Build** run on the `main` branch.
3. Scroll down to **Artifacts**.
4. Download `LiveCompOverlay-unsigned-ipa`.
5. Unzip it on your PC to get `LiveCompOverlay-unsigned.ipa`.

## Step 4: Install the IPA with AltStore

### Option A: From your PC (AltServer)

1. Make sure your iPhone is on the same Wi-Fi as your PC.
2. Open AltStore on your iPhone.
3. In AltServer tray menu → **Sideload .ipa** → select `LiveCompOverlay-unsigned.ipa`.
4. AltStore will re-sign it with your free Apple ID and install it.

### Option B: Directly on your iPhone

1. Transfer the IPA to your iPhone (AirDrop, Files app, or cloud storage).
2. Open AltStore on your iPhone.
3. Go to **My Apps** → tap **+** in the top-left.
4. Select the IPA file.
5. AltStore will sign and install it.

## Step 5: Trust the app

After install:

1. Open **Settings → General → VPN & Device Management**.
2. Tap your Apple ID under **Developer App**.
3. Tap **Trust**.

## Step 6: Point the app to your PC backend

1. Start the backend on your PC:
   ```powershell
   cd C:\Users\M\LiveCompOverlay\backend
   .\start_server.ps1
   ```
2. Find your PC's local IP address:
   ```powershell
   ipconfig
   ```
   Look for something like `192.168.1.100`.
3. Open the **Live Comp Overlay** app on your iPhone.
4. Tap the menu → **Backend**.
5. Enter `http://YOUR_PC_IP:8000` (e.g. `http://192.168.1.100:8000`).
6. Tap **Test Connection**.

## Step 7: Refresh every 7 days

Because you are using a free Apple ID, the app expires after 7 days.

- With AltServer running on the same Wi-Fi, AltStore on your iPhone will auto-refresh when opened.
- Or connect via USB and refresh manually in AltStore.

## Troubleshooting

### "Failed to sign" / provisioning error
- Make sure your free Apple ID is enrolled at developer.apple.com.
- Try restarting AltServer and your iPhone.
- Some Apple IDs need 2FA; accept the prompt on your trusted device.

### App opens then closes immediately
- This can happen if the broadcast extension entitlement is rejected for free accounts.
- Try deleting the app and reinstalling with only the main app IPA (remove extensions).

### Backend test fails
- Make sure iPhone and PC are on the same Wi-Fi.
- Check Windows Firewall is not blocking port 8000.
- Try visiting `http://YOUR_PC_IP:8000/health` from Safari on your iPhone.
