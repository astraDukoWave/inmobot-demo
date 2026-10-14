# HANDOFF — InmoBot

## Estado del ciclo — INMOBOT-S01
- Spec: `docs/specs/INMOBOT_S01_DESIGN-SPEC_v1.0_APPROVED.md` (aprobado 2026-10-13 con ajustes A1–A8)
- Plan: `docs/plans/INMOBOT_S01_PLAN_v1.0_APPROVED.md` (aprobado 2026-10-13)
- Línea base: `docs/reviews/INMOBOT_S01_BASELINE-AUDIT_v1.0.md`
- Backlog único: `docs/BACKLOG.md`

## Desviaciones
- DV-01 · PR #1 (CS-0) se mergea sin CI porque el CI nace en CS-1 · disposición: **ratify-with-reason** (Jonathan,
  2026-10-13): válido solo para PR #1, que trae documentación y el workflow manual `live-smoke`. Condiciones: diff
  completo revisado y sintaxis del workflow validada antes del merge; `live-smoke` no se ejecuta hasta que la rama
  objetivo incluya el script y sus dependencias. Desde CS-1, CI verde y verify son obligatorios.

## Autorizaciones vigentes
- Merges: Claude por API (merge commit, SHA fijado) tras presentar PR + SHA + verify + CI y recibir "OK merge #N".
- `live-smoke`: Claude puede dispararlo por API sobre código revisado con datos ficticios; máximo 3 corridas y
  ~10 MXN estimados en esta fase; registrar SHA, resultados, tokens y costo; sin reintentos ciegos.
- Secretos y deploy: solo Jonathan.

## Siguiente
CS-1 `feat/agent-core`.
