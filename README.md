# BioGuard - get, run and test

**Windows guide.** Only installing the Android APK? Skip to section 4. No source code or laptop setup is needed on the phone.

## 1. Get BioGuard from GitHub

Project: https://github.com/Etticx/BioGuard (ask the owner for access if private).

**First time, with Git:** install Git, open a terminal in the parent folder where you want BioGuard, then run:

```powershell
git clone https://github.com/Etticx/BioGuard.git
cd BioGuard
```

**Already have a Git clone?** Open a terminal inside that BioGuard folder, then update it:

```powershell
git pull --ff-only
```

If Git reports conflicting/local changes, ask the team before changing or deleting files.

**Without Git:** open the GitHub page -> Code -> Download ZIP -> Extract All. Open the extracted project folder (it may be called `BioGuard-main`). A downloaded ZIP cannot use `git pull`; download a fresh ZIP when updating. Keep your old folder/data until the update works.

**Check the download:** the project folder must contain `Start-PrivateBeta.ps1`, `backend/`, `mobile/package.json`, `mobile/src/` and `bioguard_comparison_winner.zip`. If anything is missing, ask the owner for a complete copy.

## 2. Open a terminal and prepare your computer

Open this project folder in VS Code -> Terminal -> New Terminal, and select **PowerShell**. Or open Windows Terminal/PowerShell directly in the project folder. In Command Prompt, type `powershell` first; the launch commands below use PowerShell.

If your terminal is somewhere else, use `cd` with **your actual extracted/cloned folder path**:

```powershell
cd "C:\your-folder\BioGuard"
```

That is an example, not the author's laptop path. Replace it with wherever you saved the project, including `BioGuard-main` if that is its name. You should see `Start-PrivateBeta.ps1` when you run `dir`.

**First-time setup only:** install Node 24 LTS and Python 3.12 (with the Python launcher), reopen your terminal in the project folder, then run:

```powershell
.\Setup-Local.ps1
```

This downloads dependencies, prepares the supplied model, and creates missing local test accounts. Existing accounts, passwords and reports are preserved. After pulling updates, run it again if dependencies changed. Internet access is needed for setup.

If PowerShell blocks scripts, use `Set-ExecutionPolicy -Scope Process Bypass` in that terminal, then retry. This applies only to the current terminal session.

## 3. Run locally: laptop or Expo Go

**Test logins:** `grounds / 123`, `ecology / 123`, `management / 123`. One sign-in opens the correct workspace. These defaults apply to newly created local accounts and the shared APK test server; an existing changed password is preserved.

**Laptop browser:** in the project folder, run:

```powershell
.\Start-PrivateBeta.ps1 -Mode Web
```

Open **http://localhost:8001/**. Keep the terminal open.

**Expo Go on Android or iPhone:** stop Web mode with Ctrl+C, then run:

```powershell
.\Start-PrivateBeta.ps1 -Mode Expo
```

1. Put the phone and laptop on the same Wi-Fi.
2. Open Expo Go compatible with this project's **SDK 57**, and sign in with the same Expo account as the laptop.
3. Scan the QR shown in the terminal: Android uses Expo Go; iPhone uses its Camera app.
4. Sign into BioGuard with a test login above.

If Expo needs login, run these commands in a second terminal in the project folder:

```powershell
cd mobile
npx expo login --browser
cd ..
```

Laptop dashboard remains **http://localhost:8001/**. Expo uses port **8383**. Use one local mode at a time. If port 8001 is busy, open the already-running app or stop its original terminal first.

## 4. Android APK: install and test remotely

[Download BioGuard APK - version 0.2.0, about 101 MB](https://expo.dev/artifacts/eas/cNrNpTOvPanmRZcf_D7iuAk7_yYXG5t2Xn4IsAQCIZc.apk)

Download -> open APK -> allow installation from that browser if asked -> install -> sign in. **No Expo Go or GitHub download is needed for this route.** Use the test logins above.

The current APK connects to the project owner's laptop server. The owner must keep that laptop awake, online and the remote beta running. Cloning the project onto another laptop does not move the existing APK's server.

**Project owner only:** start `./Start-RemoteBeta.ps1` if it is not already running. This requires the prepared model/web export and Cloudflare utility. Stop with Ctrl+C in its terminal or `./Stop-RemoteBeta.ps1`.

**A tunnel restart changes its URL.** The existing APK then needs rebuilding: update `build.preview.env.EXPO_PUBLIC_API_URL` in `mobile/eas.json`, then run from `mobile/`:

```powershell
npx eas-cli@latest build --platform android --profile preview
```

## Keep in mind

- Local browser + Expo share local reports; the shared APK has a separate remote-beta database.
- Keep `backend/data/` when updating: it contains saved reports and photos. GitHub does not include private data or installed dependencies.
- The owner's active remote URL is in `backend/data/remote-beta/active-url.txt`.
- Team introduction: `output/pdf/BioGuard_Team_Introduction.pdf`.

## AI restoration drafts (testing/aiagent)

- Put only your Groq API key in `backend/data/groq-api-key.txt` (ignored by Git), or set backend `GROQ_API_KEY`. Never put it in the mobile app.
- Restart the backend after code updates, then refresh management with Ctrl + F5.
- Confirm the classified species. Correct identification is available if needed. One Groq request researches and returns removal, a proposed replacement species, replanting and the handover note together. Edit the draft before Save decision.
- The replacement is a proposal for management approval. Site conditions still need checking. Sources come from the actual browser-tool results, not invented links. If the response is incomplete or unsupported, BioGuard shows an error without making another request.
- Default model: `openai/gpt-oss-120b`; optional `GROQ_MODEL` must support Groq browser search. There is no automatic model fallback, formatter request or automatic retry.
- Same report revision and confirmed species: reuse the draft for 15 minutes with zero extra Groq requests. A new revision or corrected species is a new draft.
- New attempts: at least 30 seconds apart, maximum 10 per management account per hour and 30 total per hour. Failed attempts count too. Blocked requests use no Groq call. Limits and cache apply to this backend process and reset when it restarts; run one backend worker for this beta.
- Only confirmed species, rough amount and Malaysia region are sent. No photos, precise coordinates, reporter details or report history are sent.
- Groq's own token quotas still apply. A request can contain browser-tool work and multiple output sections while remaining one outgoing BioGuard API request. No live Groq requests are needed to run the offline budget tests.
