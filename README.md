# BioGuard — first working prototype

Choose a plant photo, identify it with the supplied model, and see a suggested species.
No accounts, database, or saved prediction history.

## Project

- **mobile/** — Expo SDK 57 / React Native, React Native Paper, light theme, system fonts.
- **backend/** — FastAPI and the supplied Keras model, running on the laptop.
- **bioguard_model_package.zip** — original package, preserved unchanged.

The opening splash uses BioGuard's original leaf mark. Camera and gallery actions use
labelled outline icons. The result shows the species, model confidence, and a low
confidence message when the package's review threshold (0.62) is not met.

## Run on an Android phone

The dependencies and model have already been prepared on this computer.

1. Put the laptop and phone on the same private Wi-Fi.
2. In a PowerShell terminal in this folder, run `./Start-Backend.ps1`. Keep it running.
3. In another terminal, run `./Start-Mobile.ps1`. Keep it running.
4. Install Expo Go on Android, then scan the QR code printed by Expo.
5. Take a photo or choose one, tap **Identify**, and try another photo.

Expo Go discovers the API using the same laptop LAN address as the Expo server.
If needed, copy `mobile/.env.example` to `mobile/.env` and set
`EXPO_PUBLIC_API_URL=http://YOUR_LAPTOP_LAN_IP:8000`, then restart Expo.

A tunnel for Expo alone does **not** make the local model API reachable. Keep this
first demo on the same Wi-Fi. Guest Wi-Fi may isolate devices. If the phone cannot
connect, check that the backend is running and that Windows permits Python/Node
on your private network. This project does not change firewall rules.

## iPhone testing

The app code supports iPhone. Current Expo SDK 57 physical-iPhone testing uses an
Expo/development build signed with Apple Developer credentials; follow the current
[Expo iOS setup guide](https://docs.expo.dev/get-started/set-up-your-environment/?platform=ios&device=physical&mode=expo-go).
A distributable beta can use TestFlight. Camera permissions, the native gallery,
and the native splash screen must still be checked on real Android and iPhone devices.

## APK / standalone builds

`mobile/eas.json` includes development, preview APK, and production profiles.

For a standalone build, host the model API at a reachable **HTTPS** address and
set `EXPO_PUBLIC_API_URL` before building. Native builds keep the platform's default
secure networking; the local HTTP API is for Expo Go/browser development.

From `mobile/`:

```powershell
npx eas-cli@latest build --platform android --profile preview
```

EAS sign-in, a linked Expo project, and (for iPhone) Apple signing credentials are
required. No build has been uploaded or published by the local setup.

## Setup on another computer

Use Node 24 LTS (or a Node version supported by Expo SDK 57) and Python 3.12.

```powershell
cd backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
./.venv/Scripts/python.exe setup_model.py
cd ../mobile
npm ci
```

## Verification

```powershell
cd backend
./.venv/Scripts/python.exe -m pytest -q
cd ../mobile
npm run typecheck
npm run lint
npm test
npx expo-doctor
```

## Model and privacy

The model covers **nine selected species**. A high softmax confidence does not
prove that a photo belongs to one of them. Results are suggestions, and the app
does not authorise ecological treatment or removal.

Server preprocessing matches the package: EXIF orientation, RGB, aspect-preserving
224 × 224 black padding with bilinear interpolation, float32 pixels in 0–255.
Normalisation is already embedded in the model.

The phone converts the selected image to JPEG (95% quality), limiting its longest
edge to 2048 pixels without cropping, for upload compatibility. Only temporary
cache copies are created. The app deletes its copies when you change the photo,
start again, or close the screen normally; the OS may retain cache after a crash.
Original gallery photos are not deleted. The server handles uploads entirely in
memory and does not save photos or predictions. The local Wi-Fi demo uses HTTP;
use HTTPS when hosting or distributing the app.

The full extracted model package is preserved under `backend/model/`, including
its source/attribution manifest and evaluation files. Its reported training metrics
are the package author's figures; local smoke checks do not independently establish
field accuracy.

## Current verification notes

- TypeScript, lint, all 3 client contract checks, and all 13 API/preprocessing checks pass.
- Expo Doctor passes all 18 checks; Android/iPhone/browser bundles export successfully.
- The browser gallery, JPEG preparation, loading state, real model response,
  low-confidence message, and reset were exercised end to end.
- Pixel preprocessing matches the original package exactly on the packaged evaluation figure.
- No physical phone test, signed APK, or TestFlight build has been completed yet.
- Expo's development server is started with --offline to skip external account checks;
  it still serves the app over the local Wi-Fi.
- npm audit reports 29 upstream dependency findings (11 moderate, 18 high), largely
  involving build/routing tools. Compatible fixes were attempted; npm proposes
  incompatible framework changes for the remaining findings. Review and resolve
  these before a public release rather than forcing SDK-incompatible versions.
