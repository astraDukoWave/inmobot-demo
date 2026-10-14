# CLAUDE.md — InmoBot

Instrucciones para Claude Code en este repo. Fuente de verdad del ciclo: `HANDOFF.md`.

## Qué es
Agente "Sofía" para inmobiliarias: FastAPI + tool use (Gemini por defecto; adaptador Anthropic pendiente de
validación real) + UI estática. Catálogo **ficticio** en `properties.json`.

## Comandos
- Instalar: `python -m pip install -r requirements-dev.txt`
- Pruebas (sin red ni keys): `pytest -q`
- Lint: `ruff check .`
- Correr local: `LLM_PROVIDER=fake uvicorn app.main:create_app --factory --reload`
  (o con Gemini: `uvicorn app.main:create_app --factory --env-file .env`)
- Prueba real (cuesta tokens): `python scripts/live_smoke.py`

## Reglas
- Flujo SDD: spec → plan → PR por change set → verify → merge con SHA fijado. Artefactos en `docs/`.
- Conventional Commits, un commit por tarea, CI verde antes de mergear.
- Repo público: solo placeholders. Nunca keys, tokens ni teléfonos reales en código, tests, logs o docs.
- Las tarjetas salen solo de resultados de tools; nunca parsear texto del modelo para crear propiedades.
- Ninguna afirmación en README/docs sin evidencia (código, prueba o run).
- Deploy y secretos: solo Jonathan.
