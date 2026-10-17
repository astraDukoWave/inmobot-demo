#!/usr/bin/env bash
# Paso final: toma el frame de 12.5 s como póster, lo hornea como frame 0 (sin cambiar duración ni audio)
# y extrae el JPG. Requiere ffmpeg y out/inmobot-raw.mp4 (salida de render.mjs).
set -euo pipefail
cd "$(dirname "$0")"
ffmpeg -v error -y -ss 12.5 -i out/inmobot-raw.mp4 -frames:v 1 out/poster.png
ffmpeg -v error -y -i out/inmobot-raw.mp4 -i out/poster.png \
  -filter_complex "[0:v][1:v]overlay=enable='eq(n,0)'[v]" -map "[v]" -map 0:a \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -c:a copy -movflags +faststart \
  out/InmoBot-Sofia-demo.mp4
ffmpeg -v error -y -i out/InmoBot-Sofia-demo.mp4 -frames:v 1 -q:v 2 out/InmoBot-Sofia-poster.jpg
echo "listo: out/InmoBot-Sofia-demo.mp4 y out/InmoBot-Sofia-poster.jpg"
