// Rasterise our original vector mark for native app icons and the splash screen.
// To regenerate: npm install --no-save sharp, then node scripts/generate-assets.cjs.
const sharp = require('sharp');
const { Buffer } = require('node:buffer');
const fs = require('node:fs');
const path = require('node:path');
const assets = path.join(path.dirname(module.filename), '..', 'assets');
const leaf = '<g fill="none" stroke="#235B42" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 3.5C12 2 4.5 5.5 4.5 12.5c0 4.1 2.7 6.5 6.6 6.5 7.1 0 9.4-7.2 9.4-15.5Z"/><path d="M3 21c2-5 6.5-9.5 13-13M8.5 14.5l.1-4.5M11.5 11.5l4.5.1"/></g>';
const icon = '<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024"><rect width="1024" height="1024" fill="#F7F8F4"/><g transform="translate(236 220) scale(23)">' + leaf + '</g></svg>';
const adaptive = '<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024"><g transform="translate(320 310) scale(16)">' + leaf + '</g></svg>';
const splash = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><g transform="translate(216 138) scale(7)">' + leaf + '</g><text x="300" y="385" text-anchor="middle" fill="#1E2822" font-family="Arial,sans-serif" font-size="54" font-weight="600" letter-spacing="-1">BioGuard</text></svg>';
(async () => {
  for (const [name, svg] of [['bioguard-icon', icon], ['bioguard-adaptive', adaptive], ['bioguard-splash', splash]]) {
    fs.writeFileSync(path.join(assets, name + '.svg'), svg);
    await sharp(Buffer.from(svg)).png().toFile(path.join(assets, name + '.png'));
  }
  console.log('BioGuard icons and splash screen generated.');
})().catch(error => { console.error(error); process.exitCode = 1; });

