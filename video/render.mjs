import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

// Navegador: REMOTION_BROWSER_EXECUTABLE si está definido; si no, Remotion usa su Chrome Headless Shell.
const BROWSER = process.env.REMOTION_BROWSER_EXECUTABLE || null;
fs.mkdirSync('out', {recursive: true});
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const composition = await selectComposition({serveUrl, id: 'InmoBot', browserExecutable: BROWSER});
let last = -1;
await renderMedia({
  serveUrl, composition, codec: 'h264', crf: 18, pixelFormat: 'yuv420p', audioCodec: 'aac',
  outputLocation: path.resolve('out/inmobot-raw.mp4'), browserExecutable: BROWSER, concurrency: 2,
  onProgress: ({progress}) => { const p = Math.floor(progress * 10); if (p !== last) { last = p; console.log(`progreso ${p * 10}%`); } },
});
console.log('listo');
