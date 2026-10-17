# BioGuard staff pilot

## Working flow

Ground team submits a sighting → management reviews and assigns an ecology team → ecology accepts and submits findings/evidence → management requests changes, assigns the next approved step or closes the ticket.

New jobs have three types: **inspection**, **removal**, **replanting**. Inspection findings include species and a recommended next action. Recommendations do not authorize removal. Management confirms species/invasive status and approves removal instructions; replanting requires an approved replacement species and planting instructions. Each completed step needs management evidence approval. No follow-up visit is compulsory to close.

Existing retired visit types remain read-only in history. Older ground-team assignments require explicit reassignment to ecology where supported; retired active jobs can be cancelled and replaced through a reopened ticket. Photos and previous evidence are retained.

## Staff, locations and access

One sign-in opens the appropriate workspace: grounds → sightings, ecology → My jobs, management → dashboard. The management dashboard's Staff & sites creates typed ground/ecology teams and individual accounts. New/reset accounts receive a temporary password and must change it before working. Changes/resets revoke sessions. The last active manager cannot be disabled; active ecology jobs must be reassigned/cancelled before disabling the team's last ecology member.

Add sites and blocks to standardize locations. Reports also need a landmark; coordinates are optional. No GPS permission is requested.

Ground staff see their team's sightings and information requests. Ecology staff see their own current and historical jobs/evidence, without other teams' private plans or photos. Management reviews all tickets. Notice read states and drafts are individual. Native sessions use SecureStore; browsers use an HTTP-only cookie. Drafts include private evidence and are separated by account on the device.

## Drafts, retry and updates

Report forms automatically save locally after sign-in. Save & finish later opens Drafts. Native photo copies live in app documents; browser copies use IndexedDB. Gallery originals are never removed. Work evidence has Save evidence draft; submitting also saves a copy first.

Uploads remain queued until acknowledged. Stable keys prevent duplicate records after lost responses. Retries run about every 30 seconds while the app is open and the staff member is signed in. Expired sessions retain drafts. Validation/stale-instruction failures move to Needs attention: check My jobs or My sightings, refresh instructions and resolve the issue before submitting again. Discard obsolete drafts after checking receipts.

Updates are in-app notices: assignments, revisions, information requests, corrections, evidence awaiting verification and overdue visits. These refresh every 30 seconds. OS push/background delivery is not implemented. Offline support covers local drafts and queued uploads; sign-in and fresh assignments require connectivity. The browser preview is not an offline PWA.

## Backups and restoration

Snapshots contain accounts, private photos and report/visit history. They run daily while the backend is running. Management → Backups creates/downloads one. Copy snapshots securely off the server; local snapshots alone do not survive disk loss. The operator must set retention rules; the app does not automatically delete reports/backups.

Inspect a backup:

```powershell
backend/.venv/Scripts/python.exe backend/backup_tool.py inspect --source PATH_TO_BACKUP.sqlite3
```

Stop the backend before restoring. A restoration snapshots the existing database and revokes restored sessions:

```powershell
backend/.venv/Scripts/python.exe backend/backup_tool.py restore --source PATH_TO_BACKUP.sqlite3 --data-dir backend/data --backend-stopped
```

Restart, sign in, check counts and open an evidence image. Automated tests restore into a separate temporary data directory; the live database has not been restored.

## HTTPS hosting preparation

Dockerfile/compose.yaml prepare one server: phone web app `/`, management `/officer`, Caddy HTTPS, and persistent reports in a named volume. No hosting has been published. Docker is installed here, but its engine fails while opening a Windows runtime socket. Both Compose configurations validate; image builds and certificates remain unverified. Do not reset Docker volumes to bypass this.

On a Docker host, set BIOGUARD_DOMAIN to a domain pointing at that host, then run `docker compose up --build -d`. Ports 80/443 are required for HTTPS. Privately read seed access using `docker compose exec api cat /data/local-accounts.json`; change those passwords before inviting staff. Keep a small controlled staff pilot behind organizational access/network controls: the hosting profile enables BIOGUARD_PRIVATE_BETA=1, requiring staff authentication even for identification and a password change for new seed accounts. This is not an unrestricted public service.

Preserve the data volume. Set capacity monitoring, access/retention policies and off-host encrypted backups. Assess remaining dependency-audit findings before public release. Original model packages and report model provenance are preserved.

## Signed phone builds

mobile/eas.json has preview Android APK and production app-bundle profiles. iOS requires Apple signing plus TestFlight or registered-device internal distribution. Set EXPO_PUBLIC_API_URL to the actual HTTPS API in the matching EAS preview/production environment. The build hook rejects missing/local HTTP addresses. Link your Expo project and sign in before building; never embed staff passwords/service secrets in EXPO_PUBLIC variables.

```powershell
cd mobile
npx eas-cli@latest build --platform android --profile preview
npx eas-cli@latest build --platform ios --profile preview
```

No APK, iOS signature or store submission has been created. Bundle export is not a physical-device test. The matching expo-dev-client dependency is installed. Expo Go is selected explicitly by the local launchers. Expo Go on iPhone uses the same signed-in Expo account as the laptop; paid Apple signing is only needed for standalone distribution.

## Real-device checklist — NOT RUN

Use at least one Android and one iPhone with separate test staff accounts:

1. Cold launch/splash; camera and gallery permissions, denial and cancellation.
2. Large/rotated photos; visible JPEG and model results.
3. Known species, similar unsupported species, non-plant and unclear image. Check tentative wording; a high score does not prove a supported species.
4. Send a labelled test sighting; compare landmark and photos in management.
5. Sign in as each role. Assign and accept inspection; submit findings, approve removal and replanting plans, review evidence and close. Check requested changes.
6. Save report/evidence drafts; force-close, reopen, sign in and verify copied photos survive.
7. Interrupt an upload on weak Wi-Fi; retry and verify one receipt/record. Resolve stale instructions without duplicate work.
8. Sign out and use another team account; confirm other accounts' drafts/private photos are hidden. Check expiry/reset.
9. Site/block/manual coordinates, large text, screen reader and keyboard scrolling on a small screen.
10. Download/inspect a backup and restore to a separate test directory; verify actual photos.

Record device, OS, build, date, tester, expected/observed results and pass/fail. Exclude credentials. Demo instructions and placeholder plants must never guide real field work.

## New field evaluation — no fresh results yet

Collect reviewed photos across sites, phones, lighting and viewpoints, including the nine species and unsupported/non-plant examples. Keep fresh holdout data separate from training. Bursts, near-duplicates and views of the same plant must remain in one evaluation group.

Copy field-tests/manifest.example.json, add photos, replace placeholders and use exact scientific labels from the model class list (`unsupported` for other inputs). Include a reviewer, date, site and unique capture/source ID.

```powershell
backend/.venv/Scripts/python.exe backend/evaluate_field.py field-tests/manifest.json --output field-tests/results.json
```

The tool rejects exact duplicate/training-folder images and reports known accuracy, F1 for represented classes, uncertainty, unsupported confident matches, per-case records and model SHA. It cannot detect all near-duplicates; audit labels/groups manually. Results evaluate supplied server-image bytes. Test the physical phone capture/compression path separately. Nothing is used for training automatically and no field accuracy is fabricated.

## Earlier prototype verification (before the three-role update)

- Sixty-five backend checks cover workflow, privacy, accounts, restoration, startup failure and Malaysia date boundaries.
- Sixteen client checks cover contracts, uncertainty, lost acknowledgements, account ownership and stopped retries after conflicts.
- Mobile typecheck and lint pass; Android, iPhone and browser bundles export.
- Browser demo BG-25BED477: visit revision/start, evidence photo upload, durable draft across reload/sign-in, officer verification and separate next planting visit were exercised. The software-only evidence is clearly labelled and is not a biological validation.
- Staff-management screens and live backup creation were checked. The other user-submitted sighting was left unchanged.
- Backend calendar rules use Malaysia time (UTC+8), including on a UTC hosting computer. Timestamps remain UTC and display in the viewer's local time.
- The field-evaluation tool, Docker deployment and physical camera/gallery behavior still require their respective real data/host/devices; no result is claimed for them.

## Isolated private beta

Follow [PRIVATE_BETA.md](PRIVATE_BETA.md). Start-PrivateBeta.ps1 uses API port 8001,
Expo port 8383 and backend/data/private-beta; original data remains separate.
Current status is preparation plus local testing, with physical-device, fresh field,
off-host backup and signed-distribution acceptance still pending.
