# HANDOFF — InmoBot

## Estado (2026-10-17)
- **S01:** la propuesta de cierre está en `docs/reviews/INMOBOT_S01_CLOSEOUT_v1.0.md`, **pendiente de la firma de Jonathan**.
  - El MUST está cumplido y en producción.
  - SHOULD-1 (MCP) y SHOULD-2 (evals) se difirieron por la regla del checkpoint. **No están construidos.**
- **Spec S01:** `docs/specs/INMOBOT_S01_DESIGN-SPEC_v1.0_APPROVED.md`, aprobado con A1–A8.
- **Plan S01:** `docs/plans/INMOBOT_S01_PLAN_v1.0_APPROVED.md`.
- **Mergeado a `main`:**
  - PR #1 (docs) → `7555332`.
  - PR #2 (agente, verificado sobre `7be5400`) → `d74b514`.
  - PR #3 (contenedor y runbook) → `dcce6ff`.
  - PR #4 (CS-3, documentación) → `1d75dd3`.
- **En revisión:**
  - PR #5: incidente 01 y runbook con Config Vars.
  - PR de cierre de S01 (rama `docs/s01-closeout`, apilado sobre el PR #5).
- **Producción:** Heroku `inmobot-sofia`, dyno Basic, release del código `dcce6ff`.
  - Jonathan la validó desde el celular el 2026-10-14, después del incidente 01 (key con caracteres extra, corregida sin cambiar código).
  - El estado actual del dyno depende de una decisión de Jonathan que está en curso.
- **Evidencia:** `docs/reviews/` contiene la línea base, la revisión independiente, la bitácora de live-smoke, el Verify Report, el cto-review, el incidente 01 y el cierre de S01.
- **Fuentes del video de presentación:** rama `chore/video-source`, sin PR. El 2026-10-17 se reprodujo desde un clon limpio y salió idéntico byte a byte.

## Pendiente (humano, resultados por recibir)
- Quitar `WHATSAPP_NUMBER` en Heroku.
- Decidir qué pasa con el dyno.
- Configurar el spend cap mensual en AI Studio y la alerta de presupuesto en Google Cloud.
- Video de respaldo de 2 minutos (`docs/DEMO.md`, plan B): decidir si todavía aplica.

## Desviaciones
- **DV-01:** el PR #1 se mergeó sin CI. Disposición: ratify-with-reason (Jonathan, 2026-10-13), solo para el PR #1.
- **DV-02:** el agente no puede invocar la skill `verify`. Disposición: sustitución por un verify manual documentado (Jonathan, 2026-10-14).

## Autorizaciones vigentes
- **Merges:** Claude los ejecuta por API (merge commit, SHA fijado) después de presentar PR, SHA, verify y CI, y de recibir "OK merge #N".
- **Corridas de pago contra el modelo** (`live-smoke` o evals): las 6 autorizadas en S01 ya se consumieron. Toda corrida nueva necesita un presupuesto aprobado.
- **Secretos y deploy:** solo Jonathan.

## Siguiente ciclo
- **S02**, acordado con Jonathan el 2026-10-17:
  - Suite de evals: los 3 escenarios de `live-smoke` más 7 casos nuevos.
  - LB-14.
  - El spec y el plan están en pausa de aprobación.
- **S03:** servidor MCP (REQ-30).
- **Resto:** `docs/BACKLOG.md`.
