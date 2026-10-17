# Plan: InmoBot S02 — evals y estados de la key
plan_id: INMOBOT-S02-PLAN-01 · estado: **PENDIENTE DE APROBACIÓN**
- **Spec:** `docs/specs/INMOBOT_S02_DESIGN-SPEC_v1.0_PENDING-APPROVAL.md`, en la rama `docs/s02-sdd-bootstrap`.
- **Lane:** High-risk, con el riesgo clasificado por acción · ventana única.

> **Orden de aprobación.** Jonathan pidió el spec y el plan juntos (2026-10-17).
> - El plan se aprueba **después** del spec.
> - Si el spec cambia al aprobarse, el plan se ajusta antes de pedir su firma.
> - Nada de lo de abajo se ejecuta antes de esas dos firmas.

## Contexto de dominio (con procedencia)
- **A6 · ningún crítico se aprueba por mayoría.** Un crítico fallado en cualquier repetición hace fallar la corrida.
  Fuente: spec S01, ajustes de la aprobación (Jonathan, 2026-10-13); confirmado para S02 el 2026-10-17.
- **A7 · montos ambiguos.** Se confirman antes de buscar. La tool rechaza montos < 100,000 MXN.
  Fuente: spec S01 (A7, EDGE-03) y `app/catalog.py` (`MIN_PLAUSIBLE_PRICE_MXN`) @ `1d75dd3`.
- **NFR-04 · latencia.** p95 ≤ 8 s por turno; si se supera, se revisa el modelo.
  Fuente: spec S01 (NFR-04 y Métricas de resultado).
- **Errores del proveedor.** `LLMError.kind` toma los valores `auth`, `bad_request`, `rate_limited`, `server_error`, `timeout`, `network` y `bad_response`. El deadline del servidor nunca baja de 10 s.
  Fuente: `app/llm/gemini.py` @ `1d75dd3`.
- **Tokens y precios.**
  - La corrida 6 midió 21,883 tokens de entrada y 540 de salida en total; `lead_visita_whatsapp` usó 18,450 de entrada y 447 de salida.
  - Precio de lista de `gemini-3.8-flash`: $0.75 por millón de tokens de entrada y $3.75 por millón de salida.
  Fuente: anotaciones del check-run `smoke` de `7be5400` (leídas el 2026-10-17) y `app/config.py` (pricing consultado el 2026-10-13).
- **Dónde vive el workflow.** `workflow_dispatch` solo aparece si el workflow existe en `main`, pero puede correr sobre cualquier rama.
  Fuente: plan S01, CS-0 (2026-10-13).
- **Runners.** `ubuntu-latest` migra a Ubuntu 26 desde el 2026-10-19.
  Fuente: anotación de GitHub Actions en los runs del 2026-10-14 (leída el 2026-10-17).
- **Heroku.** Cambiar una config var reinicia la app. Un rollback regresa también las config vars.
  Fuente: Heroku Dev Center (config-vars, releases), citado en `docs/DEPLOY.md`.
- **Reglas de system design aplicadas.** Vienen del checklist de `system-design-spec` v0.2 y de los trade-offs del spec S02.
  - Resiliencia (regla 6): timeout de 10 s y sin reintentos en `provider-check`; tope de tokens y aborto temprano en evals.
  - Caché (regla 4): TTL de 60 s.
  - Autorización (regla 9): solo admin y solo POST.

## Capacidades de esta ventana (comprobadas en S01 y hoy)
| Capacidad | Estado |
|---|---|
| Push al repo | Sí |
| API REST de GitHub: PRs, check-runs, anotaciones, `workflow_dispatch` | Sí. GraphQL no está disponible |
| Pruebas locales | Sí. venv con pytest y ruff; actionlint para workflows |
| Descargar artifacts | Puede que no: el almacenamiento de artifacts no está en la lista de red permitida. Por eso el resumen va en anotaciones |
| Heroku CLI y secretos | No: son **[HUMANO]** |
| Revisión independiente | Subagente con contexto fresco: solo spec, diff y evidencia |

## Cumplimiento de proceso (obligatoria)
- **Ramas:** se crea la rama antes de tocar archivos. Todo entra a `main` por PR, también docs y workflows. Un commit por tarea, con Conventional Commits.
- **Checks requeridos:**
  - **CI:** `ruff check .` + `pytest -q`.
  - **Local:** `actionlint` si cambia un workflow.
- **Merge:** con merge commit y el SHA fijado (`PUT /pulls/{n}/merge` con `sha`). Solo con CI verde, verify manual documentado (DV-02) y **"OK merge #N"** de Jonathan.
- **Corridas pagadas:** solo con un presupuesto aprobado **por corrida**, sobre un SHA fijo, y con registro en la bitácora.
- **Desviaciones:** si aparece una, se detiene el trabajo y se registra con disposición `pending-human`. Opciones: `correct`, `ratify-with-reason` o `rollback`.

## Change sets

### CS-0 · `docs/s02-sdd-bootstrap` — spec y plan aprobados + workflow `evals`
- **Alcance:** congelar el spec y el plan aprobados, y dejar el workflow manual en `main` para poder dispararlo sobre ramas.
- **Archivos:**
  - `docs/specs/INMOBOT_S02_DESIGN-SPEC_v1.0_APPROVED.md` y `docs/plans/INMOBOT_S02_PLAN_v1.0_APPROVED.md` (los PENDING se renombran);
  - `.github/workflows/evals.yml`;
  - `HANDOFF.md`.
  - Si Jonathan lo aprueba: `ci.yml` y `live-smoke.yml` fijados a `ubuntu-24.04`.
- **Qué hacer:** `evals.yml` lleva:
  - `workflow_dispatch` con los inputs `model`, `repetitions` (choice: 1, 3, 5) y `only`;
  - `runs-on: ubuntu-24.04`, `timeout-minutes: 30`, `permissions: contents: read` y `concurrency: evals`;
  - el secret `GEMINI_API_KEY`;
  - `python scripts/evals.py`, que existirá desde CS-2;
  - la publicación del resumen como anotaciones (máximo 10 × 2,000 caracteres) y el reporte completo como artifact.
- **Verificación:** `actionlint` limpio (esta ventana) y CI verde (CI).
- **Commits:** `docs(specs): …`, `docs(plans): …`, `ci(evals): …` y, si se aprueba, `ci: …`.

### CS-1 · `feat/key-states` — LB-14
- **Alcance:** los tres estados de la key, sin llamadas de pago en `/health`.
- **Archivos:**
  - `app/keycheck.py`, nuevo;
  - `app/main.py`;
  - `tests/test_key_states.py`;
  - `docs/DEPLOY.md` (REQ-55).
- **Qué hacer:**
  - **`classify_key(provider, key) -> str`:** devuelve `missing`, `invalid_chars`, `unexpected_shape`, `ok` o `not_checked`.
  - **Arranque:** `create_app` lo calcula una vez y registra `{"event": "llm_key", …}`.
  - **`/health`:** agrega `llm_key_format` y conserva `llm_configured`.
  - **`POST /api/admin/provider-check`** (`require_admin`):
    - una llamada mínima `llm.generate(...)` sin tools, con `timeout_s=10` y sin reintentos;
    - `threading.Lock`, caché de 60 s con reloj inyectable y `TokenBudget` (consume tokens; si está agotado, responde `skipped`);
    - el resultado se guarda en `app.state.provider_check`.
  - **`/api/admin/usage`:** agrega el bloque `llm_key`.
- **Paso acotado de evidencia:** confirmar en documentación oficial de Google la forma de las API keys (`AIza` + 35). Si no se confirma, se deja como supuesto en el código y en el spec; `unexpected_shape` sigue sin bloquear.
- **Verificación:**
  - pytest y ruff, en esta ventana y en CI;
  - verify manual contra REQ-50 a REQ-55;
  - revisión independiente por un subagente.
- **Commits:** `feat(health): …`, `feat(admin): …` y `docs(deploy): …`.

### CS-2 · `feat/evals` — runner, 10 escenarios e instrumentación
- **Alcance:** la suite completa sin red, más su disparo real.
- **Archivos:**
  - `evals/__init__.py`;
  - `evals/scenarios.py`: los 10 escenarios con `critical`, `turns` y aserciones;
  - `evals/harness.py`: el runner;
  - `evals/report.py`: markdown y JSON;
  - `scripts/evals.py`: la CLI;
  - `scripts/live_smoke.py`: pasa a delegar en el runner, con suite `smoke` y N = 1;
  - `tests/test_evals_harness.py` y `tests/test_evals_scenarios.py`;
  - `.dockerignore`: se agrega `evals/`.
- **Qué hacer:**
  - **Escenarios:** una `Scenario(name, critical, turns, check)` por cada fila de REQ-40. Las aserciones leen `TurnResult` y los argumentos de las tools desde `session.history`.
  - **Runner:** construye el `Agent` como `live_smoke` y le pasa el tope con `TokenBudget(max_tokens)`.
    - **Rondas:** intercaladas. La sesión `"{escenario}-r{k}"` es nueva en cada repetición.
    - **Aserciones globales:** las de REQ-41.
    - **Aborto:** con `auth`/`not_configured` o con 3 errores seguidos del proveedor.
  - **Instrumentación (métricas del spec):**
    - p50/p95/máximo por rango más cercano, solo con turnos que llamaron al modelo;
    - n de turnos;
    - tokens y costo estimado por escenario y en total;
    - costo por conversación de `lead_visita_whatsapp` (promedio y máximo).
  - **Veredicto:**
    - FALLA si cualquier crítico falla en cualquier repetición.
    - REVISAR si los no críticos quedan por debajo de 75 %, si p95 > 8 s o si la conversación cuesta más de 2 MXN.
    - ABORTADA si se cumplen las condiciones de aborto.
  - **CLI:** `--repetitions`, `--only`, `--max-tokens` (450,000 por defecto), `--report` y `--json`. El código de salida es distinto de 0 si la corrida falla o se aborta.
- **Verificación sin red** (esta ventana y CI), con las pruebas de la sección "Tests requeridos".
- **Verificación real [HUMANO: presupuesto]:** Claude dispara `evals` por la API sobre el **SHA de la cabeza del PR** con N = 5, lee las anotaciones y registra la corrida en la bitácora.
  - **Si FALLA:** diagnóstico → propuesta de corrección acotada con prueba sin red → nuevo presupuesto → nueva corrida.
- **Revisión independiente:** un subagente revisa el diff y las aserciones antes del verify.
- **Commits:** `feat(evals): …`, `refactor(smoke): …`, `test(evals): …` y `build: …` (`.dockerignore`).

### CS-3 · `docs/s02-evals-results` — resultados publicados
- **Alcance:** los resultados en la documentación, en un PR aparte, para que el PR de evals se mergee **exactamente** en el SHA que se evaluó.
- **Archivos:**
  - `docs/reviews/INMOBOT_S02_EVALS-LOG.md`: cada corrida con su SHA, resultado, tokens, costo y enlace;
  - `README.md`: la tabla de evals con su corrida enlazada y sus límites;
  - `docs/FAQ.md`: costo y latencia medidos;
  - `docs/BACKLOG.md`: LB-14 resuelto y LB-12 con su resultado;
  - `HANDOFF.md`.
- **Verificación:** cada cifra coincide con las anotaciones de la corrida enlazada (esta ventana) y CI está verde.
- **Commits:** `docs(reviews): …`, `docs: …`.

### Gate de deploy · cto-review → deploy de LB-14 [HUMANO]
- **Qué:** después de CS-3, Claude escribe `docs/reviews/INMOBOT_S02_CTO-REVIEW_G-DEPLOY-02.md`, con rollback, blast radius, dueño y observabilidad.
- **Quién despliega:** Jonathan, siguiendo `docs/DEPLOY.md`.
- **Por qué un solo deploy al final:** si los evals obligan a corregir algo del agente, esa corrección sale en el mismo deploy.
- **Si Jonathan prefiere tener LB-14 antes:** se puede desplegar después de CS-1. Basta con que lo pida.

## Tareas [HUMANO]
1. **Aprobar el spec**, con tres decisiones: la criticidad de los escenarios, N y el presupuesto, y si se fijan los runners.
2. **Aprobar el plan.**
3. **Firmar cada merge:** "OK merge #N sobre `<SHA>`".
4. **Aprobar el presupuesto de cada corrida pagada.** Por ejemplo: "OK evals N=5 sobre `<SHA>`, tope 450k tokens". Claude la dispara por la API.
5. **Spend cap** (lo estás haciendo ahora): deja margen para los evals, porque comparten el proyecto de Google con producción.
6. **Deploy de LB-14** después del cto-review, con los pasos exactos que se entregan en ese momento. Evidencia que necesito de vuelta:
   - el JSON de `/health` con `llm_key_format`;
   - la respuesta de `provider-check`;
   - el resultado de la prueba en el celular.
7. **Solo si la primera corrida aborta por `auth`:** recargar el secret `GEMINI_API_KEY` de GitHub. Los pasos se entregan si hace falta.

## Orden y dependencias
1. Aprobación del spec y luego del plan.
2. CS-0 → merge.
3. CS-1 → merge.
4. CS-2 → corrida pagada sobre su cabeza. Si falla: corrección, nuevo presupuesto y otra corrida.
5. CS-2 → merge.
6. CS-3 → merge.
7. cto-review → deploy [HUMANO] → cierre de S02.

CS-1 y CS-2 pueden escribirse en paralelo, pero la corrida pagada se hace sobre una rama que ya incluye CS-1. Así lo evaluado es lo que se despliega.

## Tests requeridos
**Sin red (CI):**
- **Clasificación de la key:**
  - `None` → `missing`;
  - forma válida → `ok`;
  - con ESC, comillas o espacio interno → `invalid_chars`;
  - caracteres válidos con largo o prefijo distintos → `unexpected_shape`;
  - proveedor `anthropic` → `not_checked`.
- **`/health`:** 10 llamadas no producen ninguna llamada al LLM falso, y la key de prueba no aparece en la respuesta.
- **`provider-check`:**
  - responde 503 sin token configurado y 401 con token inválido;
  - con token válido hace exactamente 1 llamada;
  - dentro de 60 s devuelve `cached: true` sin nueva llamada (reloj inyectado);
  - después de 61 s hace la segunda llamada;
  - con `LLMError("auth")` responde `status: error`, `kind: auth`;
  - con el presupuesto agotado responde `skipped` sin llamar;
  - dos hilos simultáneos producen 1 sola llamada;
  - la key no aparece en `caplog`.
- **Evals:**
  - Para cada escenario, un guion **bueno** del LLM falso pasa y uno **malo** falla con la etiqueta esperada. Por ejemplo:
    - una búsqueda con 3,000,000 en t1 de `monto_ambiguo`;
    - el canary en la respuesta;
    - `request_visit` en `injection_indirecta`;
    - tarjetas en `zona_fuera_catalogo`;
    - dos "?" en `una_pregunta_a_la_vez`.
- **Sin compensación:** con N = 5, 1 crítico fallado en una sola ronda da FALLA.
- **No críticos:** 7 de 10 da REVISAR, no FALLA.
- **Precondición de la capa 1** en `injection_indirecta`.
- **Percentiles** con valores conocidos.
- **Tope de tokens:** termina en fallback y FALLA.
- **Aborto** por `auth` y por 3 errores seguidos.
- **`live_smoke` refactorizado:** produce el mismo veredicto y las mismas fallas que antes con los mismos guiones.

**Real (con presupuesto aprobado):** la corrida `evals` con N = 5 sobre la cabeza de CS-2.

## Riesgos → mitigación
| Riesgo | Mitigación |
|---|---|
| Aserciones heurísticas con falsos negativos o positivos | Un guion bueno y uno malo por escenario; respuestas en el reporte para revisión humana; un falso negativo se corrige en la aserción, con su prueba |
| El modelo no es determinista | N = 5 con rondas intercaladas y sin compensación. Una falla aislada se diagnostica, no se promedia |
| Gasto mayor al estimado | Tope de 450k tokens por corrida en código; `repetitions` como choice (1, 3, 5); presupuesto por corrida |
| Secret de GitHub vencido | Aborto en la primera llamada, sin costo (EDGE-20) |
| El spend cap se agota durante los evals y deja a producción sin modelo | Correr solo después de que el cap esté configurado con margen; el reporte muestra los tokens |
| Migración de runners a Ubuntu 26 | `evals.yml` fijado; propuesta de fijar `ci.yml` y `live-smoke.yml` |
| Las anotaciones tienen límite de tamaño | Resumen compacto con las fallas primero; el reporte completo va como artifact |
| El refactor rompe `live-smoke` | Prueba de equivalencia con el LLM falso; si se complica, `live_smoke.py` queda intacto y se duplica la definición de sus 3 escenarios, con una prueba de igualdad |
| El supuesto de forma de la key es incorrecto | `unexpected_shape` no bloquea (REQ-54) y se verifica con la documentación |
| Abuso de `provider-check` | Solo admin, 1 llamada real cada 60 s y `TokenBudget` |

## Prompt de respaldo
No aplica: todo lo ejecuta esta ventana. Lo humano está en Tareas [HUMANO].
