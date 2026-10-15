# BioGuard private beta — October 15, 2026

The core workflow is implemented. This is a local staff-only beta candidate;
physical-device acceptance, fresh field accuracy and hosted recovery are not certified.
Nothing is publicly published or submitted to an app store.

## Start on this laptop

1. Connect the laptop and both phones to the same trusted private Wi-Fi.
2. Sign into Expo CLI and Expo Go on the iPhone with the same Expo account.
   In Expo Go, return to Home, tap the avatar at the upper right, and log in.
   Sign-in on expo.dev in Safari does not also sign in the Expo Go app.
3. Run `./Start-PrivateBeta.ps1 -Mode Expo` in this folder. Keep the terminal open.
4. Open the printed `exp://LAPTOP_IP:8383` address in Expo Go, or scan its QR code.
   The browser fallback is `http://LAPTOP_IP:8001/`; the ecology desk adds `/officer`.
5. Privately open `backend/data/private-beta/local-accounts.json`. Use grounds in
   the app and ecology at the desk. These are BioGuard accounts, separate from Expo.
   Change both temporary passwords when prompted, then sign in again.
6. The officer can create individual testers and teams in Staff & sites. Share each
   person's temporary access privately; do not distribute the seed credentials file.

The current LAN IP can change after reconnecting. Restart the launcher to update it.
Use `-ApiPort` or `-ExpoPort` to choose alternatives; Windows reserves some ports.
The launcher clears build caches when changing from prototype to beta settings.
For browser-only tests use `./Start-PrivateBeta.ps1 -Mode Web` instead.
Do not run two beta launchers against the same ports. Ctrl+C stops this launcher.
Expo Go is for supervised development tests and requires the laptop to stay awake.
It is not an installed, independent APK or iOS beta binary.

## Private data

Beta storage is `backend/data/private-beta/`, separate from the original prototype
and ignored by Git. Beta tokens/cookies use a separate key. Identification requires
staff sign-in and keeps its input temporary. Only explicit reports are persisted.
Drafts retain local evidence copies and submitted reports retain the report/photos,
location, staff and review history. Coordinates are optional; no automatic training.
Use labelled test sightings and avoid people/private documents in photos.

This local setup uses HTTP on private Wi-Fi. Use test data. External testing needs
HTTPS, named individual accounts, an operator responsible for data requests, an
agreed retention period and off-host encrypted backups. The system does not silently
delete reports/backups. A test organizer must handle corrections/deletion requests
and review the data at the end of the trial. Nothing is uploaded to a backup service.

## Test both phones

Copy `beta/device-results.example.json` to the ignored `beta/device-results.json`.
Record device/OS, date, tester, expected/observed behavior and pass/fail. No passwords.
Start with camera permission/denial/cancel, gallery, rotated/large photos and one
labelled test report visible with matching photos at the ecology desk. Then run the
full ten-item checklist in PILOT_GUIDE.md, including force-close drafts, weak network,
account separation, evidence verification and regrowth follow-up. Failed cases stay open.
An exported Android/iOS bundle is not evidence of a real phone passing those checks.

## Fresh model evaluation

EfficientNetV2B0 and its 0.56 review threshold are unchanged. Historical results are
85.79% accuracy and 0.8551 macro F1, not phone-field accuracy. Collect independently
reviewed fresh cases using field-tests/manifest.example.json, including unsupported
plants/non-plants and poor photos. Keep plant groups/bursts together and outside
training. Run backend/evaluate_field.py as described in PILOT_GUIDE.md. Do not use
an unreviewed model suggestion as its own ground-truth label. No fresh results exist yet.

## Hosting, recovery and distribution

Dockerfile + compose.yaml prepare HTTPS hosting; compose.beta.yaml prepares a
separate local Docker beta. Both Compose files validate. The local Docker engine is
blocked by an inaccessible Windows runtime socket; container build/certificates are
unverified. A hosting account/domain has not been selected or configured.

Daily SQLite snapshots and officer backup downloads exist. Recovery was tested in
a temporary directory. Before remote testers, copy a snapshot to operator-approved
encrypted off-host storage and test restoration there; local snapshots alone do not
survive disk loss. Do not share plaintext backup files or temporary credentials.

EAS development/preview profiles are configured with private-beta mode; Android
preview produces APK. The build hook requires a real HTTPS API. Expo sign-in works.
A linked EAS project/hosted API and, for standalone iOS, Apple signing/registered
devices are still needed. No paid service, build upload or store submission was started.
Expo Go SDK 57 works on iPhone with matching account sign-in:
https://expo.dev/changelog/expo-go-57-login

## Security and software checks

- 65 backend tests and 16 client tests pass; typecheck/lint pass.
- Android/iOS/web bundles export and Expo doctor passes 21/21 checks.
- Keras 3.15.1, Pillow 12.3.0 and pip 26.2.1 applied; pip-audit finds no known
  vulnerabilities in this installed Python environment. Model file SHA is unchanged.
- npm audit reduced from 29 to 18 high inherited findings. Remaining roots are
  braces 3.0.3 and node-forge 1.4.0 with no published patched versions at this check.
  Do not use audit --force or hand-patch cryptography to hide the findings.
- decode-uri-component 0.5.0 and xcode's uuid 11.1.1 are pinned through overrides.
  postinstall adjusts query-string's CommonJS import for the fixed ESM decoder;
  tests cover malformed-input timing, URL round-trips and Xcode UUID generation.
- Automated checks use temporary records. Physical tests, field labels and real
  off-host restoration remain separately recorded acceptance work.

Private testing may start locally. All five readiness areas cannot be marked complete
until actual phone results, reviewed field cases, HTTPS/recovery and distribution
requirements have been checked. No claim of near-zero classification mistakes is made.
