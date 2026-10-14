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
