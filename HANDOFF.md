# HANDOFF — InmoBot

## Estado del ciclo — INMOBOT-S01 (2026-10-14)
- **Spec:** `docs/specs/INMOBOT_S01_DESIGN-SPEC_v1.0_APPROVED.md` (aprobado con A1–A8).
- **Plan:** `docs/plans/INMOBOT_S01_PLAN_v1.0_APPROVED.md`.
- **Mergeado a `main`:**
  - PR #1 (docs) → `7555332`.
  - PR #2 (agente, verificado sobre `7be5400`) → `d74b514`.
  - PR #3 (contenedor y runbook) → `dcce6ff`.
- **En curso:** PR #4 (CS-3: README honesto, LICENSE, DEMO, FAQ, WORKFLOW y reviews).
- **Evidencia:** `docs/reviews/` contiene la línea base, la revisión independiente, la bitácora de live-smoke, el Verify Report y el cto-review.

## Pendiente (humano)
- Deploy en Heroku y prueba en el celular, siguiendo `docs/DEPLOY.md` (pasos 1–6).
- Spend cap mensual en AI Studio y alerta de presupuesto en Google Cloud.
- Grabar el video de respaldo de 2 minutos (`docs/DEMO.md`, plan B).
- Después de la entrevista: `heroku config:unset WHATSAPP_NUMBER`, y apagar o bajar el tope si ya no se usa.

## Desviaciones
- **DV-01:** el PR #1 se mergeó sin CI. Disposición: ratify-with-reason (Jonathan, 2026-10-13), solo para el PR #1.
- **DV-02:** la skill `verify` no la puede invocar el agente. Disposición: sustitución por verify manual documentado (Jonathan, 2026-10-14).

## Autorizaciones vigentes
- **Merges:** Claude los ejecuta por API (merge commit, SHA fijado) después de presentar PR, SHA, verify y CI, y de recibir "OK merge #N".
- **`live-smoke`:** las 6 corridas autorizadas ya se consumieron. Cualquier corrida adicional necesita autorización nueva.
- **Secretos y deploy:** solo Jonathan.

## Siguiente ciclo (propuesta, no aprobada)
Ver `docs/BACKLOG.md`. Candidatos:
- Servidor MCP (REQ-30).
- Suite de evals con injection indirecta y temas ajenos (LB-12).
- Circuit breaker (LB-10).
- Validación real del adaptador de Claude.
