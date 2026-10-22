# BioGuard - frontend-only judges' demo

This folder is a ready-built static website. It reuses BioGuard's exported Grounds/Ecology screens and original Management frontend. There is no backend server, database service, Groq, Ollama, model inference or API key required.

## Host and share

Publish the CONTENTS of this folder at the root of a static website. Select demoapp as the publish/output directory if importing the parent repository. Leave the build command empty: these files are already built.

Static hosts such as Netlify Drop, Cloudflare Pages or Vercel can serve it. Routing files for Netlify/Cloudflare Pages and Vercel are included. Use HTTPS. You do not need to start BioGuard, Python, Expo or a tunnel for judges.

Upload all files and folders, especially _expo, assets, officer-assets and samples. Open the resulting homepage and check it before sharing the URL. Project-subfolder hosting (for example github.io/repository-name/) is not supported by this exported build; use a root-domain static deployment.

To test locally without deploying: from this folder run `python -m http.server 8127`, then open http://localhost:8127/. This is only a static file server, not the BioGuard backend. Double-clicking index.html (file://) is not supported.

## Walkthrough

1. Sign in with grounds / 123. Or use Fill example fields on the login screen, then Sign in.
2. Use sample photo, then Identify and Report sighting. The identification is a fixed Mimosa pudica example for every uploaded image.
3. Fill example fields, pin the plant location on the actual map and click Done, then Submit report.
4. Use the Management shortcut. Open the report, review the sourced inspection guidance, fill the example fields, and confirm invasive status. Review/edit the prewritten restoration plan, then Save decision.
5. Use the Ecology shortcut. Open and Accept the job. Choose No more plants found, fill the inspection note and send the inspection result.
6. Fill example fields again, confirm removal completion, and use Use sample photo twice: first for removal, then replanting. Send to management. You can also choose your own photos normally.
7. Switch to Management. Review the inspection result above the evidence, then approve and schedule the follow-up inspection.
8. Switch to Ecology and open Upcoming inspections. It is locked before the scheduled date. Use Advance to inspection date in the demo toolbar to simulate the visit date, then open and Accept the inspection.
9. Choose Not observed, Healthy and No for the successful example. Fill the note, add the sample evidence photo and submit.
10. Return to Management, review the findings and Approve and close. Download PDF exports a client-generated DEMO summary. The real product's server-generated PDF includes its complete evidence appendix.

The top toolbar gives one precise action at a time. An amber outline highlights the next control, with a pointer arrow for controls in the product screen. Click Show next step to scroll directly to that control. Hide guide / Resume guide lets visitors explore freely. The guide updates after inputs, photo selection, role changes and approvals. The toolbar also provides role switches, example field filling, sample photos, the simulated date and Reset demo. Role switches wait for pending local saves. Normal login/logout is also available.

## What is simulated

- Login is a public demonstration role selector, not secure authentication. Demo passwords are 123.
- AI plans and the classification result are prewritten. No live identification, web research or AI generation occurs.
- The replacement planting name is an illustrative placeholder requiring Ecology/site review, not a species recommendation.
- Submitted photos are stored in this browser's IndexedDB; reports and demo progress are stored locally. Visitors do not share reports with one another. Reset clears demo progress and sample photos.
- Sample photos demonstrate the upload flow; they are not real before/after restoration evidence.
- The demo date can advance to the follow-up. It does not alter your computer clock.
- Staff/account/password changes and backend backups are outside this guided demo and are disabled.
- The original interactive map uses public OpenStreetMap tiles and needs internet access. It requires no BioGuard backend. Inspection blocks organise the inspection; they are not spread predictions.
- This is a showcase, not a replacement for the working product, a security boundary or a field-management system. Do not enter private reports or personal information.

## Image and map credits

Sample Mimosa photo: CC0, iNaturalist observation https://www.inaturalist.org/observations/367696078 ; original https://inaturalist-open-data.s3.amazonaws.com/photos/671514869/medium.jpg . Attribution metadata is in samples/photo-attributions.csv. Only the Mimosa sample is included from that manifest.

Map tiles: OpenStreetMap contributors; attribution remains visible. Leaflet and existing product asset licenses remain in officer-assets/vendor.

## Maintenance

This is a frozen frontend snapshot. It does not automatically update when the main product changes. To incorporate future product UI changes, export the main app with its private-beta browser build command, refresh the corresponding compiled assets here, and recheck the demo adapters and full walkthrough. Do not replace demo-api.js or demo-bar.js with production files.
