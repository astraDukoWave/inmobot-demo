# Plan: InmoBot S01
plan_id: INMOBOT-S01-PLAN-01 · estado: APPROVED (Jonathan, 2026-10-13) · Spec: `docs/specs/INMOBOT_S01_DESIGN-SPEC_v1.0_APPROVED.md` @ `2202980`
Lane: High-risk · Ventana única (Claude Code en la nube) · Revisión 00:30 · corte 01:30

## Contexto de dominio (con procedencia)
- Tool use con historial propio: el agente es un bucle sin estado en el proveedor (generate → tools → generate).
  Gemini exige reenviar el contenido del modelo **intacto** (thought signatures). Fuente: docs oficiales de Gemini
  (ai.google.dev, *Thinking* y *Function calling*), consultadas 2026-10-13.
- Modelos vigentes: `gemini-3.8-flash` (estable, thinking por defecto `medium`, niveles low/medium/high) y
  `gemini-3.5-flash-lite` (estable, default `minimal`). Precios por 1M tokens: $0.75/$3.75 y $0.30/$2.50.
  Fuente: ai.google.dev/gemini-api/docs/pricing y /models, consultadas 2026-10-13.
- SDK `google-genai` 2.30.1 (`client.models.generate_content`, `types.FunctionDeclaration(parameters_json_schema=…)`,
  `AutomaticFunctionCallingConfig(disable=True)`, `ThinkingConfig(thinking_level=…)`). Fuente: introspección del
  paquete en esta sesión, 2026-10-13.
- Heroku: Basic $7/mes siempre encendido; Eco $5/mes se duerme a los 30 min. Fuente: heroku.com/pricing, 2026-10-13.
- Resiliencia, costo y seguridad: reglas del spec §Trade-offs (system-design-spec, reglas 6 y 7; Regla 0 de escala).

## Cumplimiento de proceso (obligatoria)
- Rama antes de tocar archivos; todo entra a `main` vía PR, también docs. Un commit por tarea, Conventional Commits.
- Checks requeridos: `ruff check .` + `pytest -q` en CI (desde CS-1). CS-0 no tiene CI todavía → **DV-01**.
- Merge: merge commit con el SHA fijado (`PUT /pulls/{n}/merge` con `sha`), solo con CI verde + verify + firma de Jonathan.
- Desviación → se detiene, se registra con disposición `pending-human`.

## Change sets
### CS-0 · `docs/s01-sdd-bootstrap` — artefactos SDD + workflow manual
**Archivos:** `docs/specs/…APPROVED.md`, `docs/plans/…`, `docs/reviews/INMOBOT_S01_BASELINE-AUDIT_v1.0.md`,
`docs/BACKLOG.md`, `CLAUDE.md`, `HANDOFF.md`, `.github/workflows/live-smoke.yml`.
**Por qué el workflow aquí:** `workflow_dispatch` solo aparece si el archivo existe en `main`; así se puede correr la
prueba real contra la rama de CS-1 **antes** de mergearla.
**Verificación:** archivos presentes en el PR (esta ventana). **Commit:** `docs(...)`, `ci(...)`.

### CS-1 · `feat/agent-core` — agente con tools, guards, UI arreglada, pruebas y CI (el PR grande)
**Archivos:** `app/{config,catalog,leads,tools,prompts,agent,guards,sessions,main}.py`,
`app/llm/{base,fake,gemini,anthropic,__init__}.py`, `static/{index.html,app.js,styles.css}`, `tests/*`,
`scripts/live_smoke.py`, `pyproject.toml`, `requirements*.txt`, `.github/workflows/ci.yml`; se borra `main.py`.
**Qué hacer:** `Agent.run_turn()` con deadline de 20 s y máximo 4 rondas; tools `search_properties`,
`get_property`, `save_lead` (upsert + teléfono MX + `score_lead()`), `request_visit`, `handoff_to_human`;
`LLMClient` neutral con `FakeLLM`, `GeminiLLM` (reenvío intacto) y `AnthropicLLM` (pendiente de validación real);
`RateLimiter`, `TokenBudget`, cabeceras de seguridad; sesiones UUID4 con candado; UI con `textContent`.
**Verificación:** `pytest -q` y `ruff check .` verdes aquí y en CI · revisión independiente de un subagente ·
`live-smoke` contra Gemini en verde **[HUMANO: secret + Run workflow]**.

### CS-2 · `chore/heroku-deploy` — contenedor y runbook
**Archivos:** `Dockerfile` (`$PORT`, no-root, `DB_PATH=/tmp`), `.dockerignore`, `heroku.yml`, `docs/DEPLOY.md`.
**Verificación:** CI verde · cto-review en `docs/reviews/` · `/health` 200 y flujo en el celular **[HUMANO]**.

### CS-3 · `docs/honest-readme` — README, LICENSE, FAQ, DEMO, WORKFLOW
**Archivos:** `README.md` (Mermaid, origen Workana tal cual, límites), `LICENSE` (MIT), `docs/FAQ.md`,
`docs/DEMO.md`, `docs/WORKFLOW.md`, `docs/archive/QA_REPORT_2026-04.md` (con nota de inexactitud).
**Verificación:** CI verde; cada afirmación del README apunta a código, prueba o evidencia.

### — Revisión 00:30 — SHOULD solo si: desplegado + probado en celular + CI verde
### CS-4 · `feat/mcp-server` — MCP mínimo (primero `lead_stats`, luego `list_leads`, `search_properties`)
**Verificación:** pruebas de contrato sin red · `lead_stats` en Claude Desktop **[HUMANO]**.
### CS-5 · `feat/evals` — 6-8 escenarios con críticos marcados; tabla en README
**Verificación:** run de `evals` en Actions **[HUMANO: Run workflow]**.

## Tareas [HUMANO]
1. Firmar cada merge (o autorizarme a ejecutarlo por API con SHA fijado tras CI verde + verify).
2. Poner `GEMINI_API_KEY` como secret del repo y correr `live-smoke` (pasos exactos en el Loop humano).
3. Crear la app `inmobot-sofia` (o `inmobot-sofia-jg`), dyno Basic, config vars y deploy (`docs/DEPLOY.md`).
4. Probar desde el celular y devolver captura o descripción del flujo.

## Orden y dependencias
CS-0 → CS-1 → (live-smoke) → CS-2 → deploy → CS-3 → **00:30** → CS-4 → CS-5. CS-3 puede escribirse mientras corre CI.

## Tests requeridos
Unitarios: catálogo, puntaje, validación de teléfono, monto ambiguo, rate limit, presupuesto. Agente con `FakeLLM`:
tarjetas solo desde tools, rondas máximas, deadline, fallback. API con `TestClient`: `/health`, chat, admin 401,
409 concurrente, 422 largo. Adaptadores: conversión de mensajes con objetos del SDK simulados. Real: `live-smoke`.

## Riesgos → mitigación
| Riesgo | Mitigación |
|---|---|
| El adaptador Gemini falla con la API real (no la alcanzo desde aquí) | `live-smoke` antes del deploy; reenvío intacto del contenido; tests con objetos reales del SDK |
| CI tarda o falla por versiones | dependencias fijadas, Python 3.12, cache de pip |
| Heroku construye distinto que local | contenedor mínimo, `CMD` con `$PORT`, `/health` |
| Se acaba el tiempo | orden MUST-first; revisión 00:30; SHOULD a la mañana (06:00) |
