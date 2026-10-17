"""Pad ambiental suave + arpegio discreto, 51 s, 48 kHz estéreo. Todo en Do mayor / La menor.

Uso: python3 make_music.py [salida.wav]   (por defecto: public/music.wav)
Determinista: con la misma versión de numpy/scipy produce el mismo archivo byte a byte.
"""
import math
import sys
import wave

import numpy as np

SR, DUR = 48000, 51.0
n = int(SR * DUR)
t = np.arange(n) / SR
f = {"F2": 87.31, "G2": 98.0, "A2": 110.0, "B2": 123.47, "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61,
     "G3": 196.0, "A3": 220.0, "B3": 246.94, "C4": 261.63, "D4": 293.66, "E4": 329.63, "G4": 392.0, "A4": 440.0,
     "B4": 493.88, "C5": 523.25, "E5": 659.25, "D5": 587.33}
chords = [["C3", "E3", "G3", "B3"], ["A2", "C3", "E3", "G3"], ["F2", "A2", "C3", "E3"], ["G2", "B2", "D3", "A3"]] * 2
arps = [["C4", "E4", "G4", "B4"], ["A3", "C4", "E4", "G4"], ["F3", "A3", "C4", "E4"], ["G3", "B3", "D4", "A4"]] * 2
seg = DUR / len(chords)
L = np.zeros(n)
R = np.zeros(n)
for i, ch in enumerate(chords):
    start, end = i * seg, (i + 1) * seg
    env = np.clip((t - (start - 0.8)) / 1.6, 0, 1) * np.clip(((end + 0.8) - t) / 1.6, 0, 1)
    env = env ** 1.5
    for j, note in enumerate(ch):
        fr = f[note]
        for det, pan in ((0.9985, 0.3), (1.0015, 0.7)):
            ph = 2 * math.pi * fr * det * t
            v = (np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)) * env * (0.11 / (1 + 0.15 * j))
            L += v * (1 - pan)
            R += v * pan
    bass = np.sin(2 * math.pi * f[ch[0]] * t) * env * 0.10
    L += bass
    R += bass
# Arpegio: una nota cada 0.5 s, decaimiento rápido y suave, alternando paneo.
step = 0.5
for k in range(int(DUR / step)):
    t0 = k * step
    if t0 < 2.0 or t0 > DUR - 3.0:
        continue
    ci = min(int(t0 / seg), len(arps) - 1)
    note = arps[ci][k % 4]
    a, b = int(t0 * SR), min(n, int((t0 + 1.6) * SR))
    tt = t[a:b] - t0
    v = np.sin(2 * math.pi * f[note] * tt) * np.exp(-tt / 0.32) * (1 - np.exp(-tt / 0.004)) * 0.045
    pan = 0.35 if k % 2 else 0.65
    L[a:b] += v * (1 - pan)
    R[a:b] += v * pan
# Suavizado (paso bajo de un polo, ~3 kHz).
alpha = 1 - math.exp(-2 * math.pi * 3000 / SR)


def lp(x):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc)
        y[i] = acc
    return y


try:
    from scipy.signal import lfilter

    L = lfilter([alpha], [1, alpha - 1], L)
    R = lfilter([alpha], [1, alpha - 1], R)
except Exception:
    L = lp(L)
    R = lp(R)
fade = np.clip(t / 1.5, 0, 1) * np.clip((DUR - t) / 2.5, 0, 1)
L *= fade
R *= fade
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = L / peak * 0.5, R / peak * 0.5  # pico en -6 dBFS
rms = math.sqrt(float(np.mean(L ** 2 + R ** 2) / 2))
print(f"pico -6 dBFS, RMS {20 * math.log10(rms):.1f} dBFS")
pcm = (np.stack([L, R], axis=1) * 32767).astype("<i2")
out = sys.argv[1] if len(sys.argv) > 1 else "public/music.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
