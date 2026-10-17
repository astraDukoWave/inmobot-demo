# Learning Backlog (único)

Toda oportunidad fuera del ciclo en curso vive aquí, con su trigger o hipótesis. Ninguna entra a un ciclo sin spec.

| id | tipo | idea | trigger / hipótesis | origen |
|---|---|---|---|---|
| LB-01 | opportunity | Persistir leads en Heroku Postgres Essential-0 | Trigger T2: leads de un cliente real deben sobrevivir reinicios | S01 spec |
| LB-02 | opportunity | Sesiones y rate limit en Redis | Trigger T1: >1 dyno o >1 worker | S01 spec |
| LB-03 | opportunity | WhatsApp real (Meta Cloud API o Twilio) con el mismo agente | Hipótesis: el canal principal de los prospectos en MX es WhatsApp | S01 brainstorm |
| LB-04 | opportunity | Canal de voz | Hipótesis: agentes de voz para seguimiento de leads tibios | S01 brainstorm |
| LB-05 | opportunity | Dashboard admin (leads, embudo, costo) | Hipótesis: el asesor no usará la API ni MCP | S01 brainstorm |
| LB-06 | opportunity | Streaming de respuestas (SSE) | Trigger: p95 > 8 s por turno | S01 (COULD) |
| LB-07 | opportunity | Modo demo offline con LLM guionado | Hipótesis: demos sin internet | S01 brainstorm |
| LB-08 | opportunity | Multi-tenant (catálogo e identidad por inmobiliaria) | Trigger: segundo cliente | S01 spec |
| LB-09 | opportunity | Calendario real para confirmar visitas | Hipótesis: la confirmación humana es cuello de botella | S01 spec |
| LB-10 | opportunity | Circuit breaker del proveedor (REQ-17, pospuesto por A4) | Trigger: más de 3 fallos del proveedor por minuto en logs | Revisión independiente PR #2 |
| LB-11 | resuelto | ~~Timeout total por llamada~~ — no se pospone: A5/REQ-19 son obligatorios. Resuelto en PR #2 con espera dura de reloj por turno | — | Jonathan (rechazo del merge de PR #2, 2026-10-14) |
| LB-12 | opportunity | Escenario crítico de injection *indirecta* contra el modelo (la capa 1 no lo frena) | Hipótesis: el modelo rechaza sin filtrar el prompt; live-smoke 1/3 lo hizo en 4.4 s, 2/3 y 4/5 se colgaron con la variante directa | live-smoke 4/5 |
| LB-13 | opportunity | Bajar `max_output_tokens` y recortar respuestas con `MAX_TOKENS` | Trigger: un turno legítimo > 9 s por generación larga en logs | live-smoke 4/5 |
| LB-14 | opportunity (candidato a S02) | Separar tres estados de la key sin revelarla: **presente**, **formato válido** y **funcionamiento comprobado contra el proveedor**. Validar el formato no demuestra que la key tenga autorización ni que Gemini esté disponible. El healthcheck habitual (`/health`) no hace llamadas de pago; la comprobación contra el proveedor es explícita y restringida. Hoy `llm_configured` solo indica que hay key | Disparador: incidente 01, key con caracteres extra que daba 400 en producción | Incidente 01; alcance precisado por Jonathan (2026-10-17) |
