# Run BioGuard locally

Use the **private beta** instructions below for the current app. They work without
publishing anything or creating an APK. The laptop runs the model and dashboard;
Android and iPhone connect to it through Expo Go.

## 1. Open the project on the laptop

Open PowerShell and go to the BioGuard folder:

```powershell
cd "D:\SCHOLARSHIPS\My Items\Degree Project\BioGuard"
```

This is the **BioGuard** folder beside SDHackathon, not inside SDHackathon.
Dependencies and the model are already prepared on this laptop. On a new computer,
follow README.md first: Python 3.12, the backend environment/model and mobile packages
must be installed. Use Node 24 LTS; the launchers prefer Codex's bundled Node when available.

## 2. Start the private beta

### Android or iPhone, with the laptop dashboard

Run this **one command** from BioGuard:

```powershell
.\Start-PrivateBeta.ps1 -Mode Expo
```

It builds the browser app, starts the model/report server on **8001**, and starts
Expo Go's development server on **8383**. Keep this terminal open and the laptop awake.
The first build/model startup can take a little time.

Do not also start Start-Backend.ps1 or Start-Mobile.ps1 for this beta. The beta
launcher already starts the services it needs.

### Laptop browser only

If you do not need Expo Go, run this instead:

```powershell
.\Start-PrivateBeta.ps1 -Mode Web
```

Then open **[BioGuard](http://localhost:8001/)** and sign in. Your account opens
the appropriate workspace: ground team, ecology field team or management.

Choose **one mode**. To switch, stop the current launcher with Ctrl+C, then run
the other command. Rebuilding does not erase the beta's saved reports.

## 3. Open on Android

1. Put Android and the laptop on the same private Wi-Fi.
2. Install/open **Expo Go**. Signing in with the same Expo account as the laptop is recommended.
3. In Expo Go, use **Scan QR code** and scan the current code shown by Expo.
4. If the terminal does not show a QR, use the development server listed in Expo Go,
   or enter `exp://LAPTOP_IP:8383` if your app offers manual URL entry.
5. At BioGuard's shared sign-in screen, use your **BioGuard staff account**.
   Ground staff submit sightings; ecology staff open My jobs; management opens the dashboard.
6. Try camera and gallery, identify a photo, then send a clearly labelled test report.

Android testing is still pending in this project; these are startup instructions,
not a claim that a physical Android phone has passed the checklist.

## 4. Open on iPhone

1. Put iPhone and the laptop on the same private Wi-Fi.
2. Open **Expo Go → Home**. Tap the **avatar in the upper-right corner** and sign in.
3. Use the **same Expo account that is signed in on the laptop**. Signing into
   expo.dev in Safari alone does not sign into the Expo Go app.
4. Use the iPhone's Camera app to scan the current Expo QR, then tap **Open in Expo Go**.
   Alternatively, tap the matching development server on Expo Go's Home screen.
5. Sign into BioGuard with your staff account. Ground staff submit sightings;
   ecology staff open My jobs; management opens the dashboard.
6. For the ground-team flow, try camera/gallery.

If the laptop needs Expo sign-in again, open a second PowerShell terminal in BioGuard:

```powershell
cd mobile
npx expo login --browser
cd ..
```

If automatic browser opening fails, set `$env:BROWSER='none'` in that terminal and
rerun the login command. Open the exact login link printed by Expo, complete sign-in,
and wait for success. Do not share passwords or that temporary sign-in link.

Expo Go supports this project's SDK 57 on iPhone when both sides use the same
account. No paid Apple Developer membership is needed for this Expo Go test;
standalone signed iOS distribution is a separate step.
[Expo's sign-in instructions](https://expo.dev/changelog/expo-go-57-login).

## 5. Open management on the laptop

While either beta mode is running, open:

**[http://localhost:8001/](http://localhost:8001/)**

Use the same sign-in screen for all three roles. **management** opens the dashboard;
**ecology** opens assigned field jobs; **grounds** opens sightings. You do not need to choose a role or remember
a different link. `/officer` remains a direct shortcut and also routes signed-in
field staff to their workspace. These BioGuard accounts are separate from Expo.

Current local test access is recorded privately in
`backend/data/private-beta/local-accounts.json`. Passwords are intentionally not
copied into this versioned guide. If an account was later reset by management, use
its newly issued password instead. A new beta installation generates temporary
passwords and asks staff to change them.

The phone and dashboard must use the same beta server to see the same reports.

## 6. Links available after startup

### Current private beta — use these

- [BioGuard shared sign-in](http://localhost:8001/) — automatically opens your
  ground, ecology field or management workspace after sign-in.
- [Management shortcut](http://localhost:8001/officer) — management workspace;
  ground and ecology accounts are routed to their own app.
- [Team reports](http://localhost:8001/team) — sightings for ground staff; assigned jobs for ecology staff.
- [Drafts and uploads](http://localhost:8001/drafts) — drafts on that browser/device.
- [Updates](http://localhost:8001/updates) — staff notices.
- [About this beta](http://localhost:8001/beta-information) — test/privacy information.
- [Server health](http://localhost:8001/health) — model availability and beta status.
- `exp://LAPTOP_IP:8383` — open the native app in Expo Go; **Expo mode only**.
- [Expo development server](http://localhost:8383/) — **Expo mode only**; use 8001
  for the normal laptop browser app and dashboard.

A report form normally opens from a selected photo or a saved draft. Opening
`/report` directly without either returns to the photo screen. API documentation
at `/docs`, `/redoc` and `/openapi.json` is deliberately disabled in private beta.

### Original prototype and optional photo-review tool

These are **separate launchers**, not additional beta services:

- [Original management dashboard](http://localhost:8000/officer) and
  [original API health](http://localhost:8000/health): start `.\Start-Backend.ps1`.
  It uses `backend/data/`, with its own accounts and original reports.
- [Original browser preview](http://localhost:8082/): start `.\Start-Preview.ps1`.
  It serves the existing `mobile/dist/` export; it may be older than current source.
  It also needs the original API on 8000. For current testing, prefer the beta launcher,
  which rebuilds the browser app each time.
- Original phone development: `.\Start-Mobile.ps1`, alongside Start-Backend.ps1.
  Expo normally starts on **8081** here; read the terminal for the actual address.
  Prefer the private-beta launcher for the current Android/iPhone test.
- [Dataset photo-review page](http://localhost:8084/): start `.\Start-Review.ps1`.
  This is a separate training-photo review tool, not the management dashboard.
  Windows may reserve 8084. If it cannot bind, an alternative is:

  ```powershell
  .\backend\.venv\Scripts\python.exe -m http.server 8384 --bind 127.0.0.1 --directory review
  ```

  Then open [http://localhost:8384/](http://localhost:8384/).

A link works only while its corresponding server is running. `localhost` and
`127.0.0.1` refer to the device on which the browser is open.

## 7. Phone addresses and common problems

**On a phone, localhost means the phone, not this laptop.** Use the laptop's Wi-Fi
IPv4 address instead. The beta launcher prints it in its Phone browser and Ecology
desk links. Replace `LAPTOP_IP` below with that current address:

```text
Phone browser: http://LAPTOP_IP:8001/
Management:    http://LAPTOP_IP:8001/officer
Expo Go:       exp://LAPTOP_IP:8383
```

An old QR image may point to a previous Wi-Fi address or port. Use the current
terminal/server address after reconnecting to Wi-Fi. If needed, `ipconfig` shows
the laptop's Wi-Fi IPv4 address.

- **Sign-in fails:** either staff role can use the main beta link. Check the
  port and password first. Beta uses **8001**;
  original uses **8000**. Their accounts and databases are separate. Several failed
  attempts can temporarily block sign-in for five minutes.
- **Expo says the phone is not signed in:** return to Expo Go Home, tap the avatar,
  sign into the laptop's Expo account, then reopen the project.
- **Connection refused:** confirm the launcher is still running and use its current
  address. Laptop sleep or closing the terminal stops access.
- **Phone cannot reach the laptop:** check both are on the same network. Guest Wi-Fi
  can isolate devices. Allow the required Python/Node access on your trusted private
  network if Windows prompts; these launchers do not change firewall rules.
- **Error 10048 / port already in use:** another server is already using that port.
  Check [the beta dashboard](http://localhost:8001/officer) first; it may already be
  running. To restart, press Ctrl+C in the original server terminal, then run the
  launcher again. The launcher now checks the socket before rebuilding. It does not
  automatically stop another process.
- **Port reserved by Windows or needed by another app:** choose different available ports:

  ```powershell
  .\Start-PrivateBeta.ps1 -Mode Expo -ApiPort 8002 -ExpoPort 8385
  ```

  Then use **8002** for every app/dashboard link and **8385** for Expo Go.
- **Phone shows old screens:** stop the beta, rerun its launcher, and reopen the
  project. It clears the build cache and includes current source changes.
- **A report or draft seems missing:** confirm the port, staff account and device.
  Submitted reports live on the server; drafts remain local to their browser/device
  and account. A draft on the laptop does not appear automatically on the iPhone.

## 8. Stop and restart

Press **Ctrl+C** in the launcher terminal. Re-run the same command to restart.
Reports remain in `backend/data/private-beta/`; original prototype reports remain
in `backend/data/`. Do not delete either directory to fix a connection problem.

This setup is for private local testing. Phones depend on the laptop and network;
it is not an independently installed APK, a TestFlight release or public hosting.
See [PRIVATE_BETA.md](PRIVATE_BETA.md) for the beta checklist and
[PILOT_GUIDE.md](PILOT_GUIDE.md) for the full workflow.

## Three-role ticket flow

1. Grounds submits a sighting with a photo and location.
2. Management reviews it and assigns an ecology team an inspection, removal or replanting job.
3. Ecology accepts the job, records findings or completed work, and sends photo evidence for review.
4. Management requests changes, approves and assigns the next step, or approves and closes the ticket.

Removal requires management confirmation of the species and invasive status plus approved instructions.
Replacement planting uses the approved species and instructions. Evidence upload never closes a ticket automatically.
Existing visits and evidence remain in history. Older assignments to ground teams require explicit reassignment; retired visit types are read-only.

After a role update, stop the beta launcher with Ctrl+C, restart it and sign in again. Local testing account details remain in the ignored local-accounts.json file.
