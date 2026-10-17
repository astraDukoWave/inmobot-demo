import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

// Uso: node stills.mjs 95 375 935   (frames a 30 fps; salida en out/still-<frame>.png)
// Navegador: REMOTION_BROWSER_EXECUTABLE si está definido; si no, Remotion usa su Chrome Headless Shell.
const BROWSER = process.env.REMOTION_BROWSER_EXECUTABLE || null;
fs.mkdirSync('out', {recursive: true});
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const composition = await selectComposition({serveUrl, id: 'InmoBot', browserExecutable: BROWSER});
for (const frame of process.argv.slice(2).map(Number)) {
  await renderStill({serveUrl, composition, frame, output: path.resolve(`out/still-${frame}.png`), browserExecutable: BROWSER});
  console.log('still', frame);
}
