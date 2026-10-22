# Final demo release - version 1.0.0

This is BioGuard's final demo release, not a claim of production or field validation.

## Source and APK are separate

Pulling GitHub updates the source code. It does not update an APK already installed on a phone. The APK embeds its backend address and must be rebuilt and reinstalled when its code or backend address changes. The backend must also run the matching source and dependencies.

## Another computer

Follow the root README: clone (or pull with a clean working tree), run Setup-Local.ps1, run Check-Setup.ps1, then Start-PrivateBeta.ps1 -Mode Web or -Mode Expo. Setup includes the PDF dependency, trained model and new local demo accounts. Do not copy the original computer's environments, private data or API keys.

For browser-only updates use `npm run build:web:beta` from mobile/. This preserves private-beta sign-in and same-origin cookies. Restart the backend after Python changes or dependency updates.

## Final Android APK

1. Decide the HTTPS backend address first. The old temporary Cloudflare address no longer resolves and has been removed. The final profile intentionally has no baked-in backend address yet. Expo Go and browser mode can still run against the laptop using the launcher.
2. Set `build.preview.env.EXPO_PUBLIC_API_URL` in mobile/eas.json to the chosen address. Never put AI keys or signing credentials in public Expo variables.
3. Commit the final source and release configuration. The same commit must identify the build.
4. From mobile/, run `npx eas-cli@latest build --platform android --profile preview`. Use the existing Expo project and signing key so it can update an installed copy.
5. Record the EAS build ID, source commit, app version, Android build number, backend address, APK URL and APK SHA-256. Preview auto-increments the remotely managed Android build number.
6. Install that exact APK on a physical Android phone. Check sign-in for all three roles, camera/gallery, map pinning, report submission, restoration review, scheduled-day follow-up restrictions, logout/login, and completed-case PDF downloading in Management.
7. Publish a private GitHub Release or privately share the verified APK and recorded build details. Keep APK binaries and signing files out of the source checkout.

The production profile creates an AAB for store distribution, not an installable APK. It also requires a real HTTPS backend environment variable. This task does not authorise store submission or public deployment.

## Current APK status

The existing finished EAS preview APK was built on 18 October 2026 from commit 0e2f4ec992a69aa99ee53dbfe64856806410359b, version 0.2.0, Android build 1. It predates the final features and must not be described as the final 1.0.0 APK. A new signed APK and physical-device verification are still required.

## Release checks performed on 23 October 2026

- Full isolated backend suite: 184 passed.
- Full mobile suite: 67 passed; TypeScript and lint passed.
- Android JavaScript/Hermes bundle export passed. This is not a signed APK or a physical-device test.
- Python dependency consistency check passed, including ReportLab 5.1.0.
- Setup checks passed for required model, map and PDF resources.
- Tracked-file check found no private database/configuration files or signing credentials.
- Existing source on GitHub was synced at be5ac02 before these release-preparation edits. The release edits must still be committed and pushed.
- A fresh source-only checkout completed setup, including new dependency installation, model extraction and demo account preparation. Check-Setup.ps1 and pip check passed there. Final browser export passed. Signing, installing and testing a new APK remain pending.


## Dependency advisories

The mobile install reports 18 high-severity npm audit entries propagated through Expo/Metro dependencies. The two advisory roots are braces 3.0.3 (GHSA-vfj7-8cjw-p6xm) and node-forge 1.4.0 (GHSA-86w9-cpqp-85rv). On 23 October 2026 these were still the latest registry versions. The proposed automatic fixes include incompatible framework version changes; no forced framework downgrade was applied. These are unresolved advisories, so the demo checks are not a production security clearance.
