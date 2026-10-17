# Cierre del ciclo INMOBOT-S01
- **Ciclo:** 13 y 14 de octubre de 2026. **Fecha de este documento:** 2026-10-17.
- **Spec:** [`INMOBOT_S01_DESIGN-SPEC_v1.0_APPROVED.md`](../specs/INMOBOT_S01_DESIGN-SPEC_v1.0_APPROVED.md), aprobado con los ajustes A1–A8.
- **Plan:** [`INMOBOT_S01_PLAN_v1.0_APPROVED.md`](../plans/INMOBOT_S01_PLAN_v1.0_APPROVED.md).
- **Estado:** propuesta de cierre, **pendiente de la firma de Jonathan**.
  - El MUST está cumplido y en producción.
  - Los 2 SHOULD se difirieron por la regla del checkpoint. **No están construidos.**
  - Quedan 3 tareas humanas en curso, con resultados pendientes.

**Leyenda de estados:**
- **Cumplido:** hay evidencia en el repo, en CI o de Jonathan.
- **Cumplido con excepción aceptada:** cumplido, salvo una excepción que Jonathan dispuso por escrito.
- **Diferido por aprobación:** no se hizo porque una regla aprobada de antemano lo dejó fuera. No existe en el repo.
- **Pendiente:** falta hacerlo o falta su evidencia.

**Etiquetas de la evidencia:**
- `[verified-this-session]`: comprobado el 2026-10-17 contra el repo, CI o la API de GitHub.
- "Jonathan": lo reportó él.

## Definition of Done (sección DoD del spec)
| # | Punto | Estado | Evidencia |
|---|---|---|---|
| 1 | `pytest` verde sin red ni keys; CI verde en cada PR mergeado | **Cumplido con excepción aceptada** (DV-01) | **Pruebas:** 88 pasan con el LLM falso `[verified-this-session]`.<br>**CI:** el check `test` está en verde en el head del PR #2 (`7be5400`), del PR #3 (`913e021`), del PR #4 (`9cc5a03`) y en `main` (`1d75dd3`) `[verified-this-session]`.<br>**Excepción:** el PR #1 (`16f0e03`) no tiene checks porque se mergeó antes de que existiera CI (DV-01). |
| 2 | Cero `innerHTML` con datos en `static/`; CSP sin `unsafe-inline` en scripts | **Cumplido** | `grep innerHTML static/` da 0 coincidencias. La CSP de `app/guards.py` usa `script-src 'self'`. Pruebas: `test_static_ui_never_uses_innerhtml` y `test_index_has_strict_csp` `[verified-this-session]` |
| 3 | `/api/admin/*` responde 401 sin token | **Cumplido** | `test_admin_requires_token`: 401 sin token y con token incorrecto. `test_admin_disabled_without_token`: 503 si no hay `ADMIN_TOKEN` `[verified-this-session]` |
| 4 | Tarjetas solo desde resultados de tools (prueba automatizada) | **Cumplido** | `test_cards_come_only_from_tool_results` (AC-02a: un nombre de propiedad inventado en el texto no produce tarjeta) y `test_text_only_turn_has_no_cards` `[verified-this-session]` |
| 5 | La app corre en Heroku Basic con `/health` 200 | **Cumplido** | Jonathan, 2026-10-14: app `inmobot-sofia`, dyno Basic, `/health` 200. El estado actual del dyno depende de una decisión suya que está en curso (ver Pendientes) |
| 6 | Flujo demo completo en el celular | **Cumplido** | Jonathan, 2026-10-14: las pruebas del paso 6 del runbook pasaron después de corregir el [incidente 01](INMOBOT_S01_INCIDENT-01_GEMINI-400.md) |
| 7 | README sin afirmaciones no verificadas; LICENSE presente | **Cumplido** | `LICENSE` (MIT) presente. El README se revisó en el PR #4. Este PR precisa dos cifras: el costo pasa a decir "estimado" y el p95 de la versión actual, "sin medir" |
| 8 | (SHOULD-1) El servidor MCP responde `lead_stats` en Claude Desktop | **Diferido por aprobación** | **No se construyó:** `main` no tiene `mcp/`.<br>**Regla aplicada:** el time-box del spec aprobado solo habilitaba los SHOULD si a las 00:30 el flujo principal estaba desplegado, probado en el celular y con CI verde. No lo estaba.<br>**Destino:** S03 |
| 9 | `live-smoke` contra el modelo real en verde, sin críticos fallados (REQ-32) | **Cumplido** | **Corrida 6** sobre `7be5400`, el SHA mergeado: 3/3 críticos y 0 errores del proveedor ([run 38574474904](https://github.com/astraDukoWave/inmobot-demo/actions/runs/38574474904)). El check `smoke` está en `success` y el reporte se leyó de sus anotaciones `[verified-this-session]`.<br>**Corridas fallidas:** las 3 anteriores, con su causa y su corrección, están en la [bitácora](INMOBOT_S01_LIVE-SMOKE_LOG.md) |
| 10 | (SHOULD-2) Tabla de evals con resultados reales en el README | **Diferido por aprobación** | **No se construyó:** `main` no tiene `evals/`.<br>**Regla aplicada:** la misma del time-box.<br>**Destino:** propuesto para S02 |

## Excepciones aceptadas
| ID | Qué pasó | Disposición | Quién y cuándo |
|---|---|---|---|
| DV-01 | El PR #1 se mergeó sin CI porque el CI nacía en CS-1 | ratify-with-reason, solo para el PR #1 | Jonathan, 2026-10-13 |
| DV-02 | Solo el usuario puede invocar la skill `verify` | Sustitución por un verify manual documentado contra el spec ([Verify Report](INMOBOT_S01_VERIFY-REPORT_PR2_v1.1.md)) | Jonathan, 2026-10-14 |
| A4 | El circuit breaker de REQ-17 se pospuso; A4 lo permitía | Pasó al backlog como LB-10, con trigger escrito | Spec aprobado, ajuste A4 |

## Revisión de métricas de resultado
El spec programó dos revisiones para el 14-oct a las 09:30 y otras dos para el **15-oct**. Las del 15-oct (costo y p95) se hacen en este documento, el **2026-10-17**.

| Métrica | Programada | Revisada | Fuente usada | Valor | Regla del spec | Resultado |
|---|---|---|---|---|---|---|
| Flujo demo completo en vivo | 14-oct 09:30 | 14-oct (Jonathan) | Prueba en el celular, paso 6 del runbook | Sí | continuar / revisar / parar | Continuar |
| Escenarios críticos que pasan | 14-oct 09:30 | 14-oct | `live-smoke`, corrida 6 | 3/3 (100 %) | 100 % requerido | Continuar |
| Escenarios no críticos que pasan | 14-oct 09:30 | — | — | Sin dato | Informativo; < 75 % ⇒ revisar | No aplica en S01: los evals se difirieron (fila 10) |
| Tokens y costo por conversación | 15-oct | **2026-10-17** | `live-smoke`, corrida 6, escenario `lead_visita_whatsapp`. La fuente prevista (`/api/admin/usage` y evals) no se usó | 18,450 tokens de entrada y 447 de salida → **≈ $0.0155 USD ≈ 0.29 MXN**. Es una **estimación** del consumo del modelo en esa conversación, no un costo facturado (ver nota abajo) | > 2 MXN ⇒ revisar modelo | Por debajo del umbral. Es **una sola conversación**, así que el dato es indicativo, no un promedio. S02 lo mide con repeticiones |
| p95 de latencia por turno | 15-oct | **2026-10-17** | `live-smoke`, corrida 6 | **Pendiente.** La versión actual midió 6 turnos con modelo, de 2.96 a 5.69 s. Con 6 muestras no hay un p95 confiable | > 8 s ⇒ revisar modelo | Sin decisión hasta medirlo. S02 mide p50 y p95 con repeticiones |

**Nota sobre el costo:**
- **Cálculo:** tokens medidos × precio de lista de `gemini-3.8-flash` ($0.75 por millón de tokens de entrada y $3.75 por millón de salida) × un tipo de cambio supuesto de 18.5 MXN/USD.
- **No incluye** el hosting.
- **Fuente de los tokens:** el reporte de la corrida 6 `[verified-this-session]`.

**Nota sobre el máximo de 9.8 s:**
- Salió de la corrida 4 (`d9ff3b3`), una versión **anterior** a la desplegada.
- No demuestra que el p95 actual supere 8 s. Tampoco demuestra lo contrario.

## Lo que S01 no probó contra el modelo real
- **Rechazo de temas ajenos** (REQ-16).
- **Injection indirecta** (LB-12). El escenario de injection valida la capa determinista, no la resistencia del modelo.
- **Zona fuera del catálogo** (EDGE-01), **sin coincidencias y alternativas** (EDGE-02), **monto ambiguo** (EDGE-03) y **teléfono inválido** (EDGE-04). Tienen pruebas deterministas del catálogo y de las tools, pero falta probar contra Gemini que el modelo las use bien:
  - `test_search_unknown_zone_returns_available_zones_and_no_cards`
  - `test_no_exact_match_returns_declared_alternatives`
  - `test_search_ambiguous_amount_asks_to_confirm`
  - `test_save_lead_rejects_invalid_phone`
- **Una pregunta a la vez** (REQ-03). Es una regla del prompt y no tiene prueba automatizada.
- **Latencia p95** de la versión desplegada.
- **Que la key funcione más allá de estar presente:** `/health` solo indica que hay key (LB-14, [incidente 01](INMOBOT_S01_INCIDENT-01_GEMINI-400.md)).
- **El adaptador de Anthropic:** sigue pendiente de validación real.

Lo acordado para S02 cubre los primeros puntos: evals con los 3 escenarios de `live-smoke` y 7 casos nuevos, más LB-14. El spec y el plan de S02 se presentan aparte, en pausa de aprobación.

## Pendientes
| Pendiente | Dueño | Estado |
|---|---|---|
| Quitar `WHATSAPP_NUMBER` en Heroku | Jonathan | En curso; resultado pendiente |
| Decidir qué pasa con el dyno | Jonathan | En curso; resultado pendiente |
| Spend cap mensual en AI Studio y alerta de presupuesto en Google Cloud | Jonathan | En curso; resultado pendiente |
| Video de respaldo de 2 minutos (`docs/DEMO.md`, plan B) | Jonathan | Pendiente; falta decidir si todavía aplica |
| Merge del PR #5 (incidente 01 y runbook) | Jonathan firma | En espera de "OK merge #5" sobre el SHA presentado |

**Material de la demostración (fuera del DoD):** el video de presentación de 51 s.
- Sus fuentes están en la rama `chore/video-source`, sin PR.
- El 2026-10-17 se reprodujo desde un clon limpio y salió idéntico byte a byte (`video/README.md` en esa rama).

## Siguiente
- **S02**, acordado con Jonathan el 2026-10-17: suite de evals (los 3 escenarios de `live-smoke` + 7 casos) y LB-14. El spec y el plan están en pausa de aprobación, y toda corrida de pago necesita un presupuesto aprobado.
- **S03:** servidor MCP (REQ-30).
- **Backlog:** LB-12 (injection indirecta) entra en los evals de S02. Las demás entradas no cambian.
