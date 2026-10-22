# BioGuard - AI, maps and inspection notes

For first-time setup and updates, start with [README.md](../README.md). These notes explain optional AI and the inspection workflow.

## AI restoration drafts

- Put only your Groq API key in `backend/data/groq-api-key.txt` (ignored by Git), or set backend `GROQ_API_KEY`. Never put it in the mobile app.
- Restart the backend after code updates, then refresh management with Ctrl + F5.
- Confirm the classified species. Correct identification is available if needed. BioGuard downloads selected official botanical profiles itself and caches readable pages for six hours. Then one plain Groq request returns removal, a proposed replacement species, replanting and the handover note together. Groq browser tools are disabled. Edit the draft before Save decision.
- The replacement is a proposal for management approval. Site conditions still need checking. Sources come from the reference pages BioGuard actually retrieved, not invented links. The reference pool covers two herbaceous options and one woody option; these are provisional choices, not an exhaustive search for the best plant. If the response is incomplete or unsupported, BioGuard shows an error without making another request.
- Default model: `openai/gpt-oss-120b`; optional `GROQ_MODEL` must support strict structured outputs. There is no formatter request or automatic Groq retry. If Groq fails and the local backup is configured, BioGuard automatically tries Qwen once.
- Same report revision and confirmed species: reuse the draft for 15 minutes with zero extra Groq requests. A new revision or corrected species is a new draft.
- New attempts: at least 30 seconds apart, maximum 10 per management account per hour and 30 total per hour. Failed attempts count too. Blocked requests use no Groq call. Limits and cache apply to this backend process and reset when it restarts; run one backend worker for this beta.
- For restoration drafting, only confirmed species, rough amount and Malaysia region are sent. No photos, precise coordinates, reporter details or report history are sent.
- Groq's own token quotas still apply. The draft shows a usage receipt with the actual number of outgoing Groq requests and the provider request ID when available. Receipts are also saved in the active beta data folder as `ai-usage.jsonl`; they contain no API keys, photos or report text. The active pipeline is `inspection-independent-v5` (`/ai/status`, management login required). No live Groq requests are needed to run the offline budget tests.

### Local Qwen backup (optional)

- Groq stays primary. If it fails and a local model is configured, Qwen automatically prepares all four sections with one local request and **zero extra Groq requests**. No backup button is needed. If Qwen also fails, generation stops; Retry draft retries locally.
- Install/start Ollama on the same laptop as the backend. Run `ollama list` to find your installed Qwen model name.
- Put that exact name (for example `qwen3:8b`, only if installed) in `backend/data/ollama-model.txt`, or set `OLLAMA_MODEL` in the terminal before starting BioGuard. Restart the backend and refresh management with Ctrl + F5.
- Ollama must listen on its normal local address `http://127.0.0.1:11434`. No model is downloaded automatically, and its port does not need to be exposed to friends.
- The backup uses the same botanical reference checks and editable sections. Internet is still needed for uncached reference pages. Speed and quality depend on the installed model and laptop; management must review the result.
- Groq and local drafts have separate 15-minute caches and per-account cooldowns, so a Groq quota error does not delay the first local attempt. The shared hourly cap and in-flight protection still apply. Usage receipts record Groq and local request counts separately.

## Elmina live map

- New reports require **Pin plant location** on the OpenStreetMap map near Elmina Lakeside Mall. Drag the map beneath the red pin, scroll/pinch to zoom, then tap **Done**. No device GPS permission is requested.
- The approximate pilot rectangle is 3.17790–3.18343 latitude and 101.50485–101.51333 longitude. Centre: 3.180661, 101.509091. It is a prototype boundary, not a surveyed SDP property boundary.
- Reports save real latitude/longitude with map version `elmina-lakeside-v1`. The server rejects new live-map reports outside the boundary. Management shows the same map and saved point.
- Internet and a reachable backend are required. Map tiles load directly from OpenStreetMap with visible attribution and normal browser caching; no offline tile downloads or background prefetch are provided. Leaflet 1.9.4 is bundled locally under `web/vendor/leaflet/` with its licence.
- Older image-map reports remain readable on their original illustration. An old draft must be pinned again before sending from the updated app; no coordinates are guessed from the picture.
- Restart `./Start-PrivateBeta.ps1 -Mode Web` after this update, then refresh the browser. The browser export has also been rebuilt. Expo Go users reload the project after restarting its backend; installed APKs need a new build.
- The shared map route is `/maps/elmina`; other application pages retain their existing frame restrictions. No spread prediction or automatic identification of drains is included.

Management location maps now highlight the report's prototype inspection block (B01–B20). A shared boundary shows both IDs; mapped water shows its name instead of selecting a land block. Orange shading identifies the location block, not predicted spread or confirmed infestation. Block data comes from `web/elmina-inspection-blocks.geojson`; it uses OSM features with merged fragments and artificial subdivisions, not official SDP boundaries. Grounds pinning and AI generation are unchanged. Refresh the management page to load the overlay; no Expo rebuild is required for these backend-served map assets.


Inspection guidance automatically loads below the management map when a report opens. It uses a separate single Groq attempt, cached per report revision/species, with one local-Qwen backup attempt and a source-based template if needed. The card shows a short paragraph and source link without dropdowns. Before review, species is labelled as suggested. Removal/replanting generation remains behind management confirmation and makes its own single Groq attempt; confirming does not regenerate inspection. Rules live in `backend/inspection_rules.json`. Management can edit the guidance and save it with the job; the approved species, block, point and source are retained. Ecology sees the approved map and brief and can submit found/none/unable results. Additional findings require a photo and pin, remain linked to the original job, and need management review before any separate removal approval. Restart the backend and refresh management after updating.

Inspection results: accept the job, record the inspection, and submit its result before restoration evidence. Management reviews inspection results before closing the job. Saving, opening and reviewing a saved inspection does not call AI. Up to five additional plant photo/pin findings can be submitted per inspection; a later inspection can be recorded separately. Inspection submissions currently send online; keep the form open to retry a failed submission. Existing restoration evidence drafts/outbox remain unchanged. The browser export has been rebuilt; Expo Go needs a reload and an existing APK needs rebuilding for the new ecology screen.

## Standalone Android APK and backend address

The browser/Expo quick start in the README is the recommended way to test on a new computer. A previously installed APK continues to contact the address embedded when it was built.

To make a new standalone build, first arrange a reachable HTTPS backend. Update `mobile/eas.json` → `build.preview.env.EXPO_PUBLIC_API_URL` to that backend (the current checked-in temporary tunnel address is not a stable service). From `mobile/`, run:

```powershell
npx eas-cli@latest build --platform android --profile preview
```

This requires an Expo account and may be subject to its build quota. It is not part of local setup. Do not put provider API keys in this file or any `EXPO_PUBLIC_` value.

The owner-only `Start-RemoteBeta.ps1` / `Stop-RemoteBeta.ps1` route requires its own tunnel utility and prepared server. Restarting a temporary tunnel can change its address, requiring a rebuilt APK. No remote server, tunnel or account is started by these documentation changes.

Inspection drafting sends the sourced species-rule bundle and block/water labels plus report site, landmark, notes and extent to the configured AI provider. Do not put private personal details in report notes. Photos and precise latitude/longitude are not included in that inspection prompt.
