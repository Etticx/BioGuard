# Android team testing

This private beta can be installed as an APK without Expo Go or Google Play. Friends download the APK link, open the file, allow installation from that browser if prompted, then sign in. No paid Google developer account is needed for this route.

## First Android beta build — 18 October 2026

- Version: **0.2.0**, Android build **1**.
- [Download the APK](https://expo.dev/artifacts/eas/cNrNpTOvPanmRZcf_D7iuAk7_yYXG5t2Xn4IsAQCIZc.apk)
- [Open the browser beta / management sign-in](https://stickers-turbo-tank-hand.trycloudflare.com)
- Local APK copy: `backend/data/remote-beta/builds/BioGuard-0.2.0-build1.apk`.
- [Build details](https://expo.dev/accounts/alifasyraf461/projects/bioguard/builds/623449b3-ad34-400a-b854-7f361d9e8b25)

This APK connects to `https://stickers-turbo-tank-hand.trycloudflare.com`. That tunnel must remain running for this build to work. Keep the local APK copy if the Expo download link later expires. Real Android installation and camera/gallery acceptance still need a tester.

## Current free setup

The app connects to an HTTPS tunnel that forwards to the model and report server on this laptop. Keep the laptop awake, connected to the Internet, and the remote-beta launcher running while friends test. This is a temporary test arrangement, not an always-online hosting service.

Remote beta data is separate: `backend/data/remote-beta/`. Original local beta reports remain in `backend/data/private-beta/`. Do not copy or commit private data.

Initial usernames are `grounds`, `ecology`, and `management`. Their generated temporary passwords are in `backend/data/remote-beta/local-accounts.json`, which is ignored by Git. Share credentials privately, separately from the APK. Each account must change its temporary password at first sign-in. Management can create individual tester accounts in its dashboard. Local-only `123` passwords are not copied to this remote workspace.

## Start and stop

From the BioGuard folder:

```powershell
.\Start-RemoteBeta.ps1
```

Prerequisites on this laptop: the prepared backend virtual environment/model, a current private-beta web export in `mobile/.beta-dist`, and the official Windows `cloudflared.exe` at `backend/data/tools/cloudflared.exe`. The launcher waits for the real model, binds the API to loopback port 8481, opens the temporary HTTPS link, and prints its URL. Existing local servers are not stopped. The active URL is also saved in `backend/data/remote-beta/active-url.txt`.

Stop with Ctrl+C in the launcher terminal, or from a second terminal:

```powershell
.\Stop-RemoteBeta.ps1
```

The stop script verifies the recorded tunnel executable and process start time before stopping it. The launcher then cleans up its own server. `-WhatIf` checks the target without stopping it.

**A new tunnel has a different URL.** An APK points to the URL used when it was built. If the tunnel is stopped or the laptop restarts, make a new build for the new URL and share that APK. Existing remote-beta records remain on disk. Browser testers can immediately use the new URL.

## Build another APK

Sign in to the same Expo account and start the remote beta first. Set `build.preview.env.EXPO_PUBLIC_API_URL` in `mobile/eas.json` to the newly printed HTTPS URL, preserving the other settings. Keep `EXPO_PUBLIC_PRIVATE_BETA` set to `1`.

From `mobile/`, using Node 24:

```powershell
npx eas-cli@latest build --platform android --profile preview
```

The project is linked to the owner's Expo account. Signing is managed by EAS; do not replace the signing key when making updates for existing testers. Stay on the free plan; do not accept paid upgrades. The first build was requested using the free allocation.

EAS supplies an installation/download link once the build finishes. One APK can be shared with multiple testers. A successful cloud build is not proof of device compatibility: first verify installation, camera/gallery permissions, identification, report submission, role routing, and two-photo restoration evidence on a real Android phone.

## References

- [Expo APK builds](https://docs.expo.dev/build-reference/apk/)
- [Expo free-plan limits](https://expo.dev/pricing)
- [Cloudflare Quick Tunnels and limitations](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
