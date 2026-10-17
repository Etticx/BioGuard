# BioGuard — private beta preparation

**Local startup and links:** [LOCAL_START.md](LOCAL_START.md) covers Android, iPhone, the laptop dashboard and every local service.

Choose a plant photo, identify it with the supplied model, and see a suggested species.
Identification stays temporary. Opening a report form after staff sign-in saves a local draft; submitting explicitly stores the report on the server.

All three roles use one sign-in: ground staff submit sightings, ecology staff open assigned jobs, and management opens the dashboard. `/officer` remains an optional direct shortcut.

## Project

- **mobile/** — Expo SDK 57 / React Native, React Native Paper, light theme, system fonts.
- **backend/** — FastAPI, the Keras model, protected local report storage and role accounts.
- **web/** — local ecology management inbox and review dashboard.
- **bioguard_comparison_winner.zip** — active EfficientNetV2B0 model package.
- **bioguard_model_package.zip** — original MobileNetV2 package, preserved unchanged.

The opening splash uses BioGuard's original leaf mark. Camera and gallery actions use
labelled outline icons. Results show a common name, scientific name, model confidence,
and invasive status from the package's **SDP species list**. Below the package's
review threshold (**0.56**), the screen leads with **Not confident**, labels the
species as a **Possible match**, and makes invasive status conditional on confirmation.
The threshold is a validation-selected review cue; it does not detect unsupported species.

The selected EfficientNetV2B0 achieved **85.79% accuracy (326/380)** and **0.8551 macro
F1** on the historical test set. It was selected using validation macro F1 before
test results were opened. This is not fresh phone/field validation.

The backend launcher checks the ZIP fingerprint on each start and installs a changed
package, so an existing installation cannot silently keep using the original model.
`GET /health` reports the running architecture and review threshold. Restart the backend
after changing the package. Neither source ZIP is modified.

Common names and reference links live in [backend/species_catalog.json](backend/species_catalog.json).
They were checked against botanical/government references including
[NParks Flora & Fauna Web](https://www.nparks.gov.sg/florafaunaweb/flora/2/3/2374),
[Royal Botanic Gardens Victoria](https://hortflora.rbg.vic.gov.au/taxon/ad979e90-5340-11e7-b82b-005056b0018f),
[IRRI's spreading dayflower factsheet](https://keyserver.lucidcentral.org/key-server/data/08050103-0a0e-4e01-8a03-040d0c020e0a/media/Html/Commelina_diffusa.htm),
and the [US Fish & Wildlife Service](https://www.fws.gov/species/parasol-leaf-tree-macaranga-tanarius).
Invasive status comes from the supplied `species_policy.json` (SDP report pages
157–160), not from a universal worldwide classification. An uncertain match never
becomes a confirmed invasive identification; comparison species are shown as
**Not listed as invasive**, rather than a blanket claim about every location.


## Grounds, ecology and management

1. **Ground team** identifies or photographs a plant and submits a sighting with location and notes. My sightings shows its progress and any requests for more information.
2. **Management** reviews the sighting and confirms the invasive plant and assigns one **restoration job** covering removal and approved replacement planting.
3. **Ecology field team** accepts the job, records removal and replanting with dated evidence photos, and submits the complete job for management review. Evidence can be saved locally as a draft.
4. **Management** requests changes, approves both parts and closes the ticket. No extra follow-up visit is compulsory.

Removal requires confirmed species, invasive status and management-approved instructions. Replanting uses an approved replacement species and instructions. The model suggests identification; it never authorizes removal or chooses replacements.

If replanting is delayed, the ecology team records a reason and removal progress; the same job stays active until planting is finished. Existing individual-step assignments remain readable and can be completed using their original instructions.

New installations generate random temporary credentials for `grounds`, `ecology` and `management`. Read the ignored `backend/data/local-accounts.json`, or `backend/data/private-beta/local-accounts.json` for the beta. Native tokens use SecureStore; browsers use an HTTP-only cookie. Management controls staff accounts, typed teams, sites and resets.

Submitted reports and photos persist in the ignored SQLite data directory. Ground staff can read their team's sightings; ecology teams see their own assignments and evidence; management reviews all tickets. Other teams cannot read private work photos or notes. Revisions and upload keys prevent stale changes and duplicate submissions.

Existing officer roles migrate to management while keeping their IDs and history. Earlier ground-team jobs need explicit reassignment to ecology; retired work types remain readable in history. See LOCAL_START.md for the current local flow and PILOT_GUIDE.md for outstanding real-device and hosting checks. No website or signed build has been published.

For a browser preview, export the app from `mobile/` with `npx expo export --platform web`,
then run `./Start-Preview.ps1` from this folder. It serves http://localhost:8082/ with
routing fallback. The backend serves the officer dashboard directly; no separate web
installation is needed.

## Private beta on Android and iPhone

Use [PRIVATE_BETA.md](PRIVATE_BETA.md) and `./Start-PrivateBeta.ps1 -Mode Expo`
for the isolated, staff-only beta. Both phones use Expo Go; sign in with the same Expo
account on the laptop and iPhone. The launcher uses a separate database and local Wi-Fi.

## Original Android prototype

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

Current App Store Expo Go supports SDK 57. Sign in with the same Expo account on
this laptop and the iPhone, then open the local development server. See
[Expo's September 2026 update](https://expo.dev/changelog/expo-go-57-login).
Apple Developer membership is needed later for signed standalone iOS distribution.
Camera permissions, gallery, draft persistence and splash behavior still require
physical Android and iPhone checks.

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
./.venv/Scripts/python.exe -m pip install --upgrade pip==26.2.1
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
edge to 2048 pixels without cropping, for upload compatibility. Identification creates temporary
cache copies. Saving a draft also retains a durable local photo copy. The app deletes its copies when you change the photo,
start again, or close the screen normally; the OS may retain cache after a crash.
Original gallery photos are not deleted. The identification endpoint handles uploads in memory and does not save them.
Submitting a report explicitly saves its photos, location, model suggestion and review history. The local Wi-Fi demo uses HTTP;
use HTTPS when hosting or distributing the app.

The full extracted model package is preserved under `backend/model/`, including
its source/attribution manifest and evaluation files. Its reported training metrics
are the package author's figures; local smoke checks do not independently establish
field accuracy.

## Staff pilot workflow

See [PILOT_GUIDE.md](PILOT_GUIDE.md) for evidence, ecology verification, separate
follow-up visits, accounts, drafts, retries, restoration and hosting instructions.

Version 0.2 adds flexible visits, dates/priority, reassignment/cancellation/reopening,
duplicate links, completion photos, corrections, regrowth/survival and audit history.
Reports can be saved when identification is unavailable. The model and threshold
are unchanged. Local drafts keep photo copies; queued uploads use stable retry keys.
In-app updates refresh while open; OS push/background delivery remains future work.

Physical Android/iPhone tests, signed builds and HTTPS container deployment remain
pending. Bundle export does not establish native behavior or field accuracy.
Original model ZIPs and attribution files are preserved. The October 15 dependency
check reports zero known Python vulnerabilities after Keras/Pillow/installer updates.
npm audit reports 18 high findings inherited from braces and node-forge, for which
no patched package version is published; private testing does not establish public-release readiness.
The query-string decoder and xcode UUID dependency findings were fixed with explicit
overrides and a reproducible CommonJS import adjustment. See PRIVATE_BETA.md.
