# BioGuard staff pilot

## Working flow

Ground team: photograph → identify or report without identification → draft/queued upload → ecology review → assigned visit → completion evidence → officer verification → follow-up.

Reports can have separate inspection, monitoring, removal, replanting, combined removal/planting and follow-up visits. The officer sets the team, date, priority and site-specific instructions. Revisions, cancellation, reopening and duplicate linking preserve audit history. Removal requires a verified invasive species; the officer chooses replacement plants.

Combined visits can submit removal-only evidence. Acceptance then requires a date for the remaining planting visit. Accepted removal/planting needs a follow-up date or a recorded reason for waiving it. Follow-up records regrowth and optional surviving/checked plants. Regrowth requires another visit or a reopened action plan. Corrections preserve earlier evidence.

## Staff, locations and access

Ecology desk → Staff & sites: create teams, then individual staff accounts. New/reset accounts get a temporary password shown once; share it privately. Staff must change it before working. Password changes/resets revoke sessions. The last active officer cannot be disabled. Reassign/cancel work before disabling a team's last member.

Add sites and their blocks to standardize locations. Reports also need a landmark; manual coordinates are optional. Free-text locations remain available for other sites. No GPS permission is requested.

Members share team work; notice read states are individual. Reassignment removes the old team's access unless they are also the reporting team. Native tokens use SecureStore with eight-hour server expiry. Browser phone sessions stay in memory and require sign-in after reload. The client never stores passwords. Use locked staff devices: drafts contain private evidence and are separated by account in the app, rather than encrypted as a separate archive.

## Drafts, retry and updates

Report forms automatically save locally after sign-in. Save & finish later opens Drafts. Native photo copies live in app documents; browser copies use IndexedDB. Gallery originals are never removed. Work evidence has Save evidence draft; submitting also saves a copy first.

Uploads remain queued until acknowledged. Stable keys prevent duplicate records after lost responses. Retries run about every 30 seconds while the app is open and the staff member is signed in. Expired sessions retain drafts. Validation/stale-instruction failures move to Needs attention: check Team reports, refresh instructions and resolve the issue before submitting again. Discard obsolete drafts after checking receipts.

Updates are in-app notices: assignments, revisions, information requests, corrections, evidence awaiting verification and overdue visits. These refresh every 30 seconds. OS push/background delivery is not implemented. Offline support covers local drafts and queued uploads; sign-in and fresh assignments require connectivity. The browser preview is not an offline PWA.

## Backups and restoration

Snapshots contain accounts, private photos and report/visit history. They run daily while the backend is running. Ecology desk → Backups creates/downloads one. Copy snapshots securely off the server; local snapshots alone do not survive disk loss. The operator must set retention rules; the app does not automatically delete reports/backups.

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

Dockerfile/compose.yaml prepare one server: phone web app `/`, ecology desk `/officer`, Caddy HTTPS, and persistent reports in a named volume. No hosting has been published. Docker is unavailable in this workspace, so container builds and certificates remain unverified.

On a Docker host, set BIOGUARD_DOMAIN to a domain pointing at that host, then run `docker compose up --build -d`. Ports 80/443 are required for HTTPS. Privately read seed access using `docker compose exec api cat /data/local-accounts.json`; change those passwords before inviting staff. Keep a small controlled staff pilot behind organizational access/network controls: identification is unauthenticated, so this is not an unrestricted public service.

Preserve the data volume. Set capacity monitoring, access/retention policies and off-host encrypted backups. Assess remaining dependency-audit findings before public release. Original model packages and report model provenance are preserved.

## Signed phone builds

mobile/eas.json has preview Android APK and production app-bundle profiles. iOS requires Apple signing plus TestFlight or registered-device internal distribution. Set EXPO_PUBLIC_API_URL to the actual HTTPS API in the matching EAS preview/production environment. The build hook rejects missing/local HTTP addresses. Link your Expo project and sign in before building; never embed staff passwords/service secrets in EXPO_PUBLIC variables.

```powershell
cd mobile
npx eas-cli@latest build --platform android --profile preview
npx eas-cli@latest build --platform ios --profile preview
```

No APK, iOS signature or store submission has been created. Bundle export is not a physical-device test. For the development-client profile, install matching `expo-dev-client` using `npx expo install expo-dev-client` first.

## Real-device checklist — NOT RUN

Use at least one Android and one iPhone with separate test staff accounts:

1. Cold launch/splash; camera and gallery permissions, denial and cancellation.
2. Large/rotated photos; visible JPEG and model results.
3. Known species, similar unsupported species, non-plant and unclear image. Check tentative wording; a high score does not prove a supported species.
4. Send a labelled test sighting; compare landmark and photos in the ecology desk.
5. Start a visit, submit removal/planting or inspection evidence, verify, schedule follow-up, record regrowth/survival, close or reopen.
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

## Local verification for version 0.2

- Sixty backend checks cover workflow, privacy, accounts, restoration, startup failure and Malaysia date boundaries.
- Twelve client checks cover contracts, uncertainty, lost acknowledgements, account ownership and stopped retries after conflicts.
- Mobile typecheck and lint pass; Android, iPhone and browser bundles export.
- Browser demo BG-25BED477: visit revision/start, evidence photo upload, durable draft across reload/sign-in, officer verification and separate next planting visit were exercised. The software-only evidence is clearly labelled and is not a biological validation.
- Staff-management screens and live backup creation were checked. The other user-submitted sighting was left unchanged.
- Backend calendar rules use Malaysia time (UTC+8), including on a UTC hosting computer. Timestamps remain UTC and display in the viewer's local time.
- The field-evaluation tool, Docker deployment and physical camera/gallery behavior still require their respective real data/host/devices; no result is claimed for them.
