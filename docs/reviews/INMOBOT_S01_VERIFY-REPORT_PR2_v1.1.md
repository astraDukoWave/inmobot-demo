# Verify Report — PR #2 (CS-1, agente) · v1.1 (actualizado tras live-smoke 6)
**Spec:** `docs/specs/INMOBOT_S01_DESIGN-SPEC_v1.0_APPROVED.md` (ajustes A1–A8)
**Código verificado:** `feat/agent-core` @ `7be5400f5a9c66cb1e5dcbfbd7444cf901998ab7` (HEAD remoto, comprobado por API)
**Fecha:** 2026-10-14 · **Verificador:** Claude (implementador del PR; no es independiente, ver §5)

## 0. Sustitución DV-02
La skill `verify` solo se puede invocar con `/verify`, y el agente no puede hacerlo.

- **Sustitución:** verify manual hecho por el agente, con el mismo criterio de la skill: comparación contra el spec aprobado y evidencia ejecutable en lugar de releer el diff.
- **Aprobación:** Jonathan, 2026-10-14 (respuesta al pedido de merge del PR #2).
- **Alcance:** este reporte no aprueba nada; entrega un dictamen.

## 1. Dictamen
**GO para merge sobre `7be5400`** (v1.1).

- La v1.0 de este reporte dio NO-GO porque faltaba REQ-32 sobre el SHA final.
- Jonathan autorizó la corrida 6, que pasó sobre `7be5400`: 3/3 críticos y 0 errores del proveedor.
- El dictamen no aprueba el merge. La firma es de Jonathan ("OK merge #2").

## 2. Evidencia ejecutada en esta sesión [verified-this-session]
| Qué | Resultado |
|---|---|
| CI (`ruff` + `pytest`) sobre `7be5400` | ✅ success: https://github.com/astraDukoWave/inmobot-demo/actions/runs/38573239643 |
| `pytest` local | 88 passed, sin red ni keys |
| Pruebas de reloj real (`tests/test_deadline.py`) repetidas 6 veces | 6/6 verdes |
| Turno con proveedor colgado (medición directa) | límite 1 s → 0.976 s · límite 2 s → 1.953 s. Escala lineal: con 20 s cierra en ~19.5 s |
| `live-smoke` 5/5 sobre `1e2f722` (Gemini real) | ✅ 3/3 críticos, 0 errores del proveedor, 1.5–6.2 s por turno, $0.0202 USD |
| **`live-smoke` 6 sobre `7be5400` (SHA final, Gemini real)** | ✅ **3/3 críticos**, 0 errores del proveedor, 3.0–5.7 s por turno, $0.0184 USD ≈ 0.34 MXN: https://github.com/astraDukoWave/inmobot-demo/actions/runs/38574474904 |
| Costo acumulado de las corridas 1–6 | $0.1122 USD ≈ 2.08 MXN (tipo de cambio supuesto 18.5) |

## 3. Requisito por requisito
Leyenda: ✅ verificado · ⚠️ parcial o limitado · ⏳ pendiente · ⛔ fuera de este PR

| ID | Estado | Evidencia |
|---|---|---|
| REQ-01 tool use nativo | ✅ | Adaptadores sin etiquetas de texto. live-smoke: `search_properties`, `save_lead`, `request_visit`, `handoff_to_human` con Gemini real. `get_property` solo en pruebas |
| REQ-02 / AC-02a grounding | ✅ | `test_cards_come_only_from_tool_results` (nombre inventado en el texto → sin tarjeta) y la aserción de grounding de live-smoke |
| REQ-03 calificación, una pregunta a la vez | ⚠️ | Revisión humana de las respuestas de live-smoke 5 y 6 (una pregunta por turno). Sin aserción automática |
| REQ-04 upsert + teléfono MX | ✅ | `test_upsert_merges_one_lead_per_session`, `test_phone_normalization`, `test_save_lead_rejects_invalid_phone`. live-smoke: `+522221234567` |
| REQ-05 / AC-05a puntaje determinista | ✅ | `test_ac05a_full_qualification_is_hot`, `test_no_phone_is_always_cold`, `test_visit_rescores_and_stats` |
| REQ-06 visita solicitada | ✅ | `test_visit_requires_contact_first`, `test_visit_records_request_and_action`, `test_visit_to_unknown_property_fails`. live-smoke: visita a la propiedad 4 |
| REQ-07 wa.me | ✅ | `test_handoff_builds_wa_me_link_or_declines` (sin número no inventa uno). live-smoke: acción `whatsapp` |
| REQ-08 proveedor por entorno; historial Gemini intacto | ✅ Gemini · ⚠️ Anthropic | `test_gemini_replays_model_content_intact_with_thought_signature` y live-smoke multi-turno. Anthropic: solo objetos simulados del SDK, **pendiente de validación real** (A2/NFR-06) |
| REQ-10 1,000 caracteres + 12 turnos | ✅ | `test_message_too_long_and_empty`, `test_trim_history_starts_on_a_user_message` |
| REQ-11 rate limit por IP (último valor de XFF) | ✅ código · ⏳ Heroku | `test_rate_limit`, `test_client_ip_uses_last_forwarded_hop_only_when_trusted`. En Heroku hace falta `TRUST_PROXY=true` (runbook CS-2) |
| REQ-12 presupuesto diario | ✅ | `test_budget_exhausted_skips_the_model` |
| REQ-13 `textContent` + CSP | ✅ | `test_static_ui_never_uses_innerhtml`, `test_index_has_strict_csp` |
| REQ-14 UUID4 del servidor | ✅ | `test_chat_creates_server_side_uuid_session` |
| REQ-15 admin con token; sin CORS abierto | ✅ | `test_admin_requires_token`, `test_admin_disabled_without_token`, `test_admin_usage_requires_token`. CORS: solo con `ALLOWED_ORIGINS` (lectura de `app/main.py`) |
| REQ-16 rechazo de temas ajenos / revelar instrucciones; canary | ⚠️ | **Capa 1 determinista:** `test_obvious_injection_is_caught`, `test_real_estate_messages_pass`, `test_guard_answers_without_calling_the_model` y live-smoke 5/5. **Canary:** `test_canary_leak_is_replaced`. **No verificado:** la negativa del propio modelo sobre el SHA final (solo en la corrida 1/3, en 4.4 s; ver LB-12) y el **rechazo de temas ajenos** (ninguna prueba) |
| REQ-17 fallo del proveedor → mensaje amable + WhatsApp | ✅ · ⛔ circuit breaker | `test_provider_failure_returns_friendly_reply_with_whatsapp`, `test_retryable_error_is_retried_once`. Visto con fallas reales en las corridas 2–4. Circuit breaker pospuesto por A4 (LB-10) |
| REQ-18 sin urgencia ni promesas de crédito | ⚠️ | Reglas en `app/prompts.py` (sofia-2.1). Revisión humana de 5 y 6: el crédito se remite a un asesor y no hay urgencia. Sin aserción automática |
| REQ-19 límite de ~20 s del turno completo | ✅ | Ver detalle en §3.1 |
| REQ-20 endpoints | ✅ | `test_health`, `test_chat_*`, `test_public_properties_endpoint`, pruebas de admin |
| EDGE-01 zona fuera del catálogo | ✅ | `test_search_unknown_zone_returns_available_zones_and_no_cards` |
| EDGE-02 alternativas declaradas | ✅ | `test_no_exact_match_returns_declared_alternatives`. Etiqueta en la UI: lectura de `static/app.js` |
| EDGE-03 monto ambiguo | ✅ tool · ⚠️ modelo | `test_ambiguous_amounts_are_rejected`, `test_search_ambiguous_amount_asks_to_confirm`. Que el modelo confirme "¿3 millones?" no se probó en vivo |
| EDGE-04 teléfono inválido | ✅ | `test_save_lead_rejects_invalid_phone` |
| EDGE-05 visita sin contacto | ✅ tool · ⚠️ modelo | `test_visit_requires_contact_first`. En live-smoke el modelo pidió los datos antes de la visita |
| EDGE-06 injection directa | ✅ capa 1 | Ver REQ-16: valida la capa determinista, **no** la resistencia general del modelo |
| EDGE-07 mensajes simultáneos | ✅ | `test_busy_session_returns_409`. La UI deshabilita el envío mientras espera (lectura de `static/app.js`) |
| EDGE-08 más de 4 rondas | ✅ | `test_max_rounds_closes_without_tools` |
| NFR-01 pruebas sin red + CI por PR | ✅ | CI en el PR, verde |
| NFR-02 contenedor | ⛔ CS-2 (PR #3) | Dependencias fijadas: ✅ (`requirements.txt`) |
| NFR-03 logs sin contenido ni PII | ✅ | `test_logs_carry_no_user_text_name_or_phone` (nombre, teléfono y texto ausentes de los logs) |
| NFR-04 p95 ≤ 8 s | ⚠️ no verificado | Muestra chica: 5/5 tuvo como máximo 6.2 s, pero 4/5 tuvo un turno de 9.8 s. Sigue siendo [hipótesis] |
| NFR-05 README honesto | ⛔ CS-3 | — |
| NFR-06 Anthropic etiquetado | ✅ código | Docstring y `validated_against_real_api = False` con prueba. README en CS-3 |
| REQ-30 MCP / REQ-31 evals | ⛔ cancelados esta noche | Regla del checkpoint de las 00:30 (Jonathan) |
| REQ-32 live-smoke real | ✅ | Corrida 6 sobre `7be5400` (SHA final): demo → tarjetas [4, 5]; lead + visita a la 4 + WhatsApp; injection rechazada por la capa determinista |

### 3.1 Detalle de REQ-19 / A5 (corrección pedida por Jonathan)
- **Espera dura de reloj por llamada.** El modelo corre en un pool de hilos y el turno lo espera con un tope (`Agent._call`). El timeout de httpx, que es por fase, ya no define el total.
- **El límite cuenta desde que llega la petición** (`request.state.received_at`).
- **Primer intento:** ≤ 45 % del turno (9 s). El reintento usa lo que queda menos un margen de cierre.
- **Respuestas tardías.**
  - Se considera tardía una respuesta con tools cuando quedan < 10 % del turno (2 s), o cualquier respuesta después del límite.
  - Se descarta completa: no entra al historial y no empieza ninguna tool. Pruebas: `test_late_response_with_tool_calls_starts_no_tool` (ni `save_lead` ni `request_visit`), `test_text_arriving_after_deadline_is_discarded` y `test_late_tool_response_is_discarded_before_any_tool_runs`.
- **Cada tool revisa el límite antes de empezar.** Prueba: `test_no_tool_starts_once_the_deadline_passes_mid_round` (`request_visit` nunca empieza).
- **Llamada que excede el turno entero:** `test_hung_call_cannot_exceed_turn_budget` (reloj real, ≤ 1.15 s con límite de 1 s).
- **Candado de sesión.**
  - `test_api_turn_with_hung_provider_answers_in_budget_and_releases_the_lock`: un segundo mensaje recibe 200, no 409.
  - `test_session_lock_is_released_when_the_turn_crashes`: después de un 500, el siguiente recibe 200.
- **Nota de trazabilidad.** El texto de REQ-19 dice "cada llamada recibe el tiempo restante". La implementación es más estricta: primer intento con tope y espera dura. La intención del requisito (≤ ~20 s en total) se cumple.

## 4. Hallazgos de la revisión independiente (sobre `cc9d100`)
| Hallazgo | Estado |
|---|---|
| H1 llamadas paralelas sin respuesta | ✅ corregido, con `test_h1_every_function_call_gets_a_response` |
| H2 excepciones que dejaban el historial inválido | ✅ corregido, con `test_h2_*` |
| H3 continuación automática del SDK | ✅ corregido, con `test_h3_*` |
| H4 `finish_reason` | ⚠️ parcial: un reintento ante respuesta vacía. `MAX_TOKENS` sin recorte (LB-13) |
| H5 timeout por fase | ✅ cerrado con la espera dura (LB-11 cerrado: no se pospone) |
| H6 configuración | ✅ `GEMINI_THINKING_LEVEL` validado y comando local corregido. `TRUST_PROXY` y Dockerfile van en CS-2 |
| H7 diferencias con el spec | ⚠️ Circuit breaker → LB-10 (A4). Los eventos `admin_denied` y `rejected:too_long` no se registran. Los criterios por sesión de `ToolExecutor` no se limpian (crecimiento acotado por el uso) |

## 5. Limitaciones (conocidas y declaradas)
- **El verificador no es independiente:** el agente verifica su propio PR. La revisión independiente se hizo sobre `cc9d100`, no sobre el SHA final.
- **El escenario `prompt_injection` de live-smoke valida la capa determinista, no la resistencia general del modelo.** La injection indirecta queda en LB-12.
- **No se ha probado contra el modelo real:** el rechazo de temas ajenos, la confirmación de montos ambiguos y la calificación "una pregunta a la vez".
- **Tokens de llamadas abandonadas:** no se cuentan en el presupuesto diario, porque nunca llega su `usage`. El riesgo queda acotado por el rate limit.
- **Pool saturado:** si las 16 llamadas del pool quedan ocupadas, las nuevas esperan en cola y caen en el mensaje amable. Es degradación acotada, no una falla del turno.
- **El límite cuenta desde que la app recibe la petición:** no cubre la cola del router de Heroku, que tiene su propio corte de 30 s.
- **Latencia p95:** desconocida (muestra de 6 corridas; máximo observado 9.8 s en la corrida 4).

## 6. Pendiente
1. **Firma de Jonathan:** "OK merge #2" sobre `7be5400`.
2. CS-2 (PR #3): cambiar la base a `main`, CI verde, merge, deploy de Jonathan y prueba en el celular.
3. CS-3: README honesto, LICENSE, DEMO.md, FAQ y WORKFLOW.md. Este reporte se commitea en `docs/reviews/` dentro de CS-3, para no cambiar el SHA verificado del PR #2.
