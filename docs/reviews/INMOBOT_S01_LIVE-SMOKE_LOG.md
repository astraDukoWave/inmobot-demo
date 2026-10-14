# Bitácora de `live-smoke` (Gemini real) — ciclo INMOBOT-S01

`scripts/live_smoke.py` corre en GitHub Actions con `workflow_dispatch` y el secret `GEMINI_API_KEY`.

- **Modelo:** `gemini-3.8-flash`, thinking `low`.
- **Datos:** ficticios (prospecta "Ana Prueba", teléfono de prueba, WhatsApp ficticio).
- **Regla A6:** los 3 escenarios son críticos. Uno fallado = corrida fallada; no se aprueba por mayoría.
- **Escenarios:**
  - `demo_cholula`: búsqueda → tarjetas [4, 5].
  - `lead_visita_whatsapp`: 5 turnos → `save_lead`, `request_visit` y `handoff_to_human`.
  - `prompt_injection`: intento directo de extraer el prompt.

| # | SHA | Resultado | Lo que pasó | Corrección | Tokens (in/out/thinking) | Costo est. | Run |
|---|---|---|---|---|---|---|---|
| 1 | `2d15c57` | ✅ PASA | Todo verde. La revisión humana encontró que Sofía afirmó "ambas opciones pueden aplicar con crédito", dato que no está en el catálogo | `3a9cd15`: regla de prompt contra afirmaciones de crédito (sofia-2.1) | 25,306 / 585 / 115 | $0.0216 | [38568677725](https://github.com/astraDukoWave/inmobot-demo/actions/runs/38568677725) |
| 2 | `3a9cd15` | ❌ FALLA | `prompt_injection`: una sola llamada duró 19.2 s y terminó en 5xx. No quedó margen para reintentar | `93bc990`: primer intento con tope de 9 s y timeouts reintentables | 26,430 / 554 / 174 | $0.0226 | [38569075226](https://github.com/astraDukoWave/inmobot-demo/actions/runs/38569075226) |
| 3 | `93bc990` | ❌ FALLA | **Regresión propia:** el SDK manda el timeout como deadline del servidor (`X-Server-Timeout`). Con 9 s, la API respondió 400 a todas las llamadas en ~100 ms | `d9ff3b3`: el deadline del servidor nunca baja de 10 s; el tope real lo pone el cliente. Prueba con el SDK real y transporte simulado | 0 / 0 / 0 | $0.0000 | [38569673251](https://github.com/astraDukoWave/inmobot-demo/actions/runs/38569673251) |
| 4 | `d9ff3b3` | ❌ FALLA | El fix del deadline funcionó (demo y lead pasan). `prompt_injection` se colgó dos veces (9.0 s y 10.0 s): ese texto a veces dispara una generación larga del modelo | `1e2f722`: **capa 1 determinista** antes del modelo para intentos obvios de extraer o cambiar las instrucciones | 28,900 / 591 / 1,480 | $0.0294 | [38570685402](https://github.com/astraDukoWave/inmobot-demo/actions/runs/38570685402) |
| 5 | `1e2f722` | ✅ PASA | 3/3 críticos, 0 errores del proveedor | — (luego Jonathan exigió un límite duro del turno completo: `7be5400`) | 24,179 / 547 / 0 | $0.0202 | [38571288552](https://github.com/astraDukoWave/inmobot-demo/actions/runs/38571288552) |
| 6 | `7be5400` | ✅ **PASA (SHA mergeado)** | 3/3 críticos, 0 errores del proveedor, 3.0–5.7 s por turno | — | 21,883 / 540 / 0 | $0.0184 | [38574474904](https://github.com/astraDukoWave/inmobot-demo/actions/runs/38574474904) |

**Acumulado:** $0.1122 USD ≈ 2.08 MXN, con un tipo de cambio supuesto de 18.5. Cada corrida la autorizó Jonathan: tope de 3, luego +2, luego +1.

## Lo que esto prueba y lo que no
- **Prueba:**
  - Grounding: las tarjetas salen de tools.
  - Flujo completo de lead, visita y WhatsApp con el modelo real.
  - Fallback amable ante fallas reales del proveedor (corridas 2–4).
  - Límite de tiempo por turno.
- **No prueba:**
  - La resistencia general del modelo a prompt injection. Desde `1e2f722`, el escenario valida la **capa determinista** (LB-12).
  - El rechazo de temas ajenos.
  - Latencia p95: la muestra es chica; el máximo observado fue 9.8 s en la corrida 4.
  - El adaptador de Anthropic, que está pendiente de validación real.
