# Video de presentación — InmoBot · Sofía

Aquí están las fuentes del video de 51 s (1920×1080, 30 fps, H.264 + AAC) que se generó y se entregó el 2026-10-14.

Se hizo con [Remotion](https://www.remotion.dev/) 4.0.535. Así funciona:
- Cada frame es un componente de React.
- Chromium dibuja ese componente.
- Remotion junta los frames y el audio en un MP4.

> Este directorio no es parte de la app. Ni el servidor ni las pruebas lo usan.

## Qué hay aquí
| Archivo | Para qué sirve |
|---|---|
| `src/Main.tsx` | Las 7 escenas, con su duración en frames: gancho 120 · presentación 105 · producto 510 · cómo funciona 270 · prueba 270 · cómo se construyó 135 · cierre 120. Total: 1530 frames = 51 s. |
| `src/Root.tsx`, `src/index.ts` | Registran la composición `InmoBot`. |
| `make_music.py` | Genera `public/music.wav`: pad y arpegio en Do mayor / La menor, 51 s, 48 kHz. Es determinista. |
| `stills.mjs` | Renderiza frames sueltos para revisarlos antes del render completo. |
| `render.mjs` | Hace el render completo → `out/inmobot-raw.mp4`. |
| `finish.sh` | Toma el frame de 12.5 s como póster y lo pone como frame 0, sin cambiar la duración ni el audio. Deja `out/InmoBot-Sofia-demo.mp4` y `out/InmoBot-Sofia-poster.jpg`. |
| `brag-plan.md` | Ángulo, storyboard y notas de honestidad del video. |
| `share-copy.txt` | Texto para acompañar la publicación. |

`node_modules/`, `public/` y `out/` no se versionan. Los pasos de abajo los regeneran.

## Requisitos
- Node.js 22 y npm.
- Python 3 con `numpy`. Si `scipy` está instalado, el script lo usa.
- `ffmpeg`, solo para `finish.sh`.
- Las fuentes **Inter**, **Noto Color Emoji** y **DejaVu Sans Mono** instaladas en el sistema. El video no las incrusta: si faltan, el navegador usa otras y el resultado cambia.
- Un Chrome o Chromium headless para Remotion. La variable `REMOTION_BROWSER_EXECUTABLE` indica cuál usar. Si no se define, Remotion usa su propio Chrome Headless Shell y lo descarga la primera vez. Esto último no se verificó aquí; viene de la documentación de Remotion.

## Reproducir el video
```bash
cd video
npm ci            # instala las versiones exactas de package-lock.json
npm run music     # → public/music.wav

# Opcional: revisar frames sueltos → out/still-<frame>.png
REMOTION_BROWSER_EXECUTABLE=/ruta/a/headless_shell node stills.mjs 95 375 935 1205

REMOTION_BROWSER_EXECUTABLE=/ruta/a/headless_shell npm run render   # → out/inmobot-raw.mp4
npm run finish    # → out/InmoBot-Sofia-demo.mp4 y out/InmoBot-Sofia-poster.jpg
```
En el contenedor donde se hizo el video, la ruta del navegador era `/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell`.

## Verificación de la reproducción
**Fecha:** 2026-10-17.

**Qué se hizo:** se clonó esta rama en limpio (commit `b6eb4c7`) y se siguieron los pasos de arriba en el contenedor donde se hizo el video original.
- Node 22.22.0, numpy 2.5.3, scipy 1.18.1, ffmpeg 6.1.1.
- Chromium headless shell 1194.

**Resultado:** los tres archivos salieron **idénticos byte a byte** a los del 2026-10-14.

| Archivo | sha256 (original y reproducido) |
|---|---|
| `public/music.wav` | `ec3c9bcbbaf5647e155b3fc29c53acaa277dd60f6efb696ec864432dbc7f95de` |
| `out/inmobot-raw.mp4` | `ae3f4cfcd4cdd1d0b955c3f032e732246bf8e9a5b5ecd096ddf0039acd322929` |
| `out/InmoBot-Sofia-demo.mp4` (el que se entregó) | `d08c0b8d6abfe9a6ca2c015e6cfd68740858c1222404341c69b66f06ef2ef6ea` |

- Con `ffmpeg -f framemd5` también coinciden, uno por uno, los 1530 frames de video y los 2391 paquetes de audio decodificados.
- Duración: 51.008 s.
- El proceso completo tardó unos 3.5 minutos.

**No verificado:** reproducirlo en otra máquina, por ejemplo macOS. Con otras fuentes, otro navegador u otra versión de ffmpeg, el archivo puede no salir idéntico.

## Honestidad: qué muestra el video
- **Mensajes:** los del prospecto y las respuestas de Sofía son reales. Vienen del escenario `lead_visita_whatsapp` de la corrida 6 de `live-smoke` (`7be5400`, Gemini). Las respuestas largas están abreviadas con "…".
- **Interfaz:** el teléfono es una recreación con los estilos de `static/styles.css`. Las imágenes de las tarjetas reproducen los placeholders del catálogo ficticio.
- **Datos de prueba:** "Ana Prueba, 222 123 4567". No aparece ningún número real.

### Cifras en pantalla y cómo leerlas
| En pantalla | Fuente | Cómo leerla |
|---|---|---|
| 88 pruebas en CI | `pytest -q` en CI al 2026-10-14 | Pruebas sin red ni keys. |
| 6 corridas: 3 fallaron, 3 se corrigieron | [`INMOBOT_S01_LIVE-SMOKE_LOG.md`](../docs/reviews/INMOBOT_S01_LIVE-SMOKE_LOG.md) | Cada falla tiene causa y corrección. |
| ≈0.3 MXN por conversación de 5 turnos "(medido)" | [`docs/FAQ.md`](../docs/FAQ.md), corrida 6 | Es una **estimación** del consumo del modelo en esa conversación: tokens medidos (~18,450 de entrada, ~450 de salida) × precio de lista × tipo de cambio supuesto de 18.5. No incluye hosting. Lo medido son los tokens, no el costo, así que la etiqueta "(medido)" del video es imprecisa. |
| 3.0–5.7 s por turno en la corrida final | Bitácora de `live-smoke`, corrida 6 | Rango observado en una sola corrida. No es un p95. |
