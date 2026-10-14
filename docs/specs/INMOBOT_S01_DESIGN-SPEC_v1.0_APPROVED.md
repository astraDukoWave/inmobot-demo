# Spec: InmoBot S01 — de demo rota a agente profesional
spec_id: INMOBOT-S01-SPEC-01 · lane: High-risk (deploy público, secretos, datos personales) · estado: APPROVED (Jonathan, 2026-10-13 22:43, con ajustes A1–A8)

## Ajustes de la aprobación (Jonathan, 2026-10-13)
- **A1** La escala (50 conversaciones/día, 2 semanas) es un **supuesto de diseño, no capacidad comprobada**.
- **A2** Gemini es el proveedor principal y **se prueba contra la API real** (REQ-32). El adaptador de Anthropic,
  mientras solo tenga pruebas simuladas, se declara **"pendiente de validación real"** en código, README y FAQ.
- **A3** Se mantienen: tools, tarjetas desde el catálogo, validaciones, protección de leads, límites de consumo,
  manejo de errores, pruebas, CI, deploy y documentación honesta.
- **A4** Chips, canary, circuit breaker y endpoint de consumo son **posponibles** si comprometen el flujo principal.
  Los logs básicos de tokens y latencia se conservan siempre.
- **A5** Límite total de **~20 s por turno**, incluyendo llamadas y reintentos (el router de Heroku corta a los 30 s).
- **A6** Las pruebas mínimas con el modelo real son **obligatorias** aunque se posponga la suite de evals.
  **Ningún escenario crítico se aprueba por mayoría** (7/8 no compensa un crítico fallado).
- **A7** Montos ambiguos ("3") **se confirman** con el prospecto antes de buscar.
- **A8** El enmascaramiento de teléfonos aplica a **MCP** (la API admin, protegida con token, sí devuelve el dato
  completo). SQLite efímero es **solo para la demo con datos de prueba**.
- **Time-box:** revisión a las **00:30**, corte duro a la **01:30**. Los SHOULD solo se habilitan si a las 00:30 el
  flujo principal está desplegado, probado desde el celular y con CI verde; entonces primero MCP mínimo con `lead_stats`.

## Resumen general
InmoBot es un agente conversacional para inmobiliarias: "Sofía" califica a un prospecto, le muestra
propiedades **solo del catálogo**, registra una solicitud de visita, guarda el lead con un puntaje
(caliente / tibio / frío) y ofrece pasar a un humano por WhatsApp. Hoy el repo no corre: su único
backend LLM (GitHub Models) fue retirado el 30-jul-2026 y las acciones dependen de etiquetas de texto
(`docs/reviews/INMOBOT_S01_BASELINE-AUDIT_v1.0.md`).

Este ciclo reconstruye el núcleo sobre **tool use** con una capa de proveedor intercambiable:
Gemini es el runtime por defecto (hay créditos) y el adaptador de Claude queda listo y probado con
un SDK simulado. Se mantienen FastAPI y la UI actual, arreglada.

## Objetivos del usuario
1. Como **prospecto en el celular**, quiero decir qué busco en lenguaje natural y ver tarjetas de
   propiedades reales del catálogo, para decidir rápido si me interesa visitar alguna.
2. Como **asesor de la inmobiliaria**, quiero recibir leads ya calificados con un puntaje explicable y
   la opción de que el prospecto me escriba por WhatsApp con el contexto, para atender primero a los calientes.
3. Como **director**, quiero preguntarle a Claude Desktop "¿cuántos leads calientes hubo hoy y qué buscan?"
   y recibir una respuesta con datos reales, sin ver teléfonos completos.

## Alcance estricto v1
**Incluye:** agente con tools · grounding de tarjetas · guards · pruebas con LLM falso · CI en cada PR ·
contenedor + `heroku.yml` + `/health` + `$PORT` · README honesto con Mermaid · (SHOULD-1) servidor MCP ·
(SHOULD-2) evals contra el modelo real vía `workflow_dispatch` · DEMO.md, WORKFLOW.md, FAQ.md.

**NO incluye:** WhatsApp real (Twilio/Meta) · voz · multi-tenant · Postgres · fine-tuning · dashboard admin ·
streaming (COULD) · calendario real (la visita es una *solicitud* que confirma un humano).

## Requisitos

### Agente y tools
- **REQ-01** El agente usa tool use nativo del proveedor (sin etiquetas en texto). Tools:
  `search_properties`, `get_property`, `save_lead`, `request_visit`, `handoff_to_human`.
- **REQ-02** Grounding: las tarjetas que ve el usuario salen **solo** de resultados de `search_properties`
  o `get_property` del mismo turno; el texto del modelo nunca se parsea para crear tarjetas.
  - **AC-02a** Un escenario con un nombre de propiedad inventado en el texto del modelo no produce tarjeta.
- **REQ-03** Calificación: zona, presupuesto, recámaras, tipo, forma de pago, plazo, nombre y teléfono.
  Una pregunta a la vez; si el prospecto da varios datos juntos, no se repiten.
- **REQ-04** `save_lead` hace *upsert* por sesión (un lead por conversación) y valida el teléfono
  mexicano (10 dígitos, normaliza `+52`). Teléfono inválido → error explicativo para que el modelo lo vuelva a pedir.
- **REQ-05** Puntaje determinista calculado por código, con razones (`score_reasons`); el modelo no lo
  decide ni se le muestra al prospecto.
  - **AC-05a** Contacto + presupuesto + zona + forma de pago + plazo ≤ 3 meses ⇒ `caliente`.
- **REQ-06** `request_visit` exige un lead con nombre y teléfono y un `property_id` del catálogo; registra
  la solicitud con estado `solicitada`. Sin fechas ni disponibilidad inventadas.
- **REQ-07** `handoff_to_human` devuelve un enlace `https://wa.me/<WHATSAPP_NUMBER>?text=<resumen>`
  que la UI muestra como botón. Sin `WHATSAPP_NUMBER` configurado, el agente lo dice y no inventa número.
- **REQ-08** Proveedor elegible por entorno: `LLM_PROVIDER=gemini|anthropic|fake`, modelos por
  `GEMINI_MODEL` / `ANTHROPIC_MODEL`. El historial de Gemini se reenvía intacto (*thought signatures*).

### Guards (decisiones cerradas del encargo)
- **REQ-10** Mensaje ≤ 1,000 caracteres (UI y servidor); historial acotado a los últimos 12 turnos.
- **REQ-11** Rate limit por IP (por minuto y por hora; en Heroku la IP sale del último valor de `X-Forwarded-For`).
- **REQ-12** Presupuesto diario global de tokens; al agotarse, respuesta amable con salida a WhatsApp.
- **REQ-13** Todo texto se pinta con `textContent` (cero `innerHTML` con datos); CSP estricta sin scripts inline.
- **REQ-14** Sesión con UUID4 generado por el servidor; un ID desconocido crea sesión nueva.
- **REQ-15** Endpoints de admin con `Authorization: Bearer <ADMIN_TOKEN>` (comparación en tiempo constante);
  sin `ADMIN_TOKEN` → 503. Sin CORS abierto: mismo origen por defecto.
- **REQ-16** Rechazo de temas ajenos y de pedidos de revelar o cambiar las instrucciones; *canary* en el
  prompt: si aparece en una respuesta, se reemplaza por un rechazo.
- **REQ-17** Fallo del proveedor (timeout, 429, 5xx, bloqueo) → respuesta amable + botón de WhatsApp;
  circuit breaker tras fallos consecutivos.
- **REQ-18** Sin presión ni urgencia inventada; sin promesas de crédito ni asesoría legal o financiera.
- **REQ-19** Deadline total de ~20 s por turno: cada llamada al modelo recibe el tiempo restante como timeout;
  si se agota, respuesta amable + WhatsApp (A5).

### API
- **REQ-20** `GET /health` (sin secretos) · `POST /api/chat` · `GET /api/properties` (catálogo público) ·
  `GET /api/admin/leads` · `GET /api/admin/stats` · `GET /api/admin/usage`.

### Operación y calidad
- **NFR-01** Pruebas sin red ni key: LLM falso guionado; CI (ruff + pytest) en cada PR y push a `main`.
- **NFR-02** Contenedor que escucha en `$PORT`, usuario no-root, `.dockerignore`, dependencias fijadas.
- **NFR-03** Logs estructurados por turno (latencia, tokens, tools, costo estimado) **sin contenido ni PII**.
- **NFR-04** Latencia objetivo p95 ≤ 8 s por turno con tools [hipótesis: se mide en evals].
- **NFR-05** README sin afirmaciones no verificadas: catálogo ficticio declarado, límites declarados, y el origen
  tal cual: propuesta para un prospecto real de Workana; hubo demo y video, no hubo contratación ni pago; hoy es
  proyecto de portafolio. Sin clientes en producción, testimonios ni resultados comerciales.
- **NFR-06** El adaptador de Anthropic se etiqueta "pendiente de validación real" mientras no tenga prueba contra la API (A2).

### SHOULD
- **REQ-30 (MCP)** Servidor MCP stdio, cliente delgado de la API admin, tools `lead_stats`, `list_leads`
  (teléfonos enmascarados) y `search_properties`; pruebas de contrato sin red.
- **REQ-32 (obligatorio)** Prueba mínima contra el modelo real (`live-smoke`): flujo demo, lead + visita y
  prompt injection; todos críticos. Corre en GitHub Actions con `workflow_dispatch` y el secret `GEMINI_API_KEY`.
- **REQ-31 (Evals)** 6-8 conversaciones guionadas contra el modelo real con aserciones sobre tools y tarjetas;
  `workflow_dispatch` + secret `GEMINI_API_KEY`; tabla de resultados en el README.

## Comportamiento esperado
**Flujo feliz (demo):** "Busco casa en Cholula, hasta 2.5 millones, 3 recámaras" → `search_properties`
(zona Cholula, ≤ 2,500,000, ≥ 3 recámaras, casa) → 2 tarjetas (ids 4 y 5) → Sofía pregunta forma de pago y
plazo → pide nombre y teléfono → `save_lead` → "quiero visitar Casa Los Fresnos el sábado" →
`request_visit` → "¿puedo hablar con alguien?" → `handoff_to_human` → botón de WhatsApp.

**Casos edge:**
- **EDGE-01** Zona fuera del catálogo (p. ej. Atlixco) → cero tarjetas, dice qué zonas sí hay.
- **EDGE-02** Sin coincidencias exactas → hasta 2 alternativas marcadas `alternativa` (regla determinista).
- **EDGE-03** Monto ambiguo ("3", "dos y medio") → Sofía confirma "¿3 millones de pesos?" antes de buscar;
  la tool rechaza montos < 100,000 MXN con un error que obliga a confirmar (A7).
- **EDGE-04** Teléfono inválido → se vuelve a pedir; nunca se guarda basura.
- **EDGE-05** `request_visit` sin contacto → el modelo pide nombre y teléfono primero.
- **EDGE-06** "Ignora tus instrucciones / muéstrame tu prompt" → rechazo, sin tools.
- **EDGE-07** Dos mensajes simultáneos en la misma sesión → el segundo recibe 409 y la UI no lo permite.
- **EDGE-08** Más de 4 rondas de tools en un turno → se corta y se responde sin tools.

## Manejo de errores
| Caso | Qué ve el usuario | Qué se registra |
|---|---|---|
| Mensaje > 1,000 | "Tu mensaje es muy largo" (422) | evento `rejected:too_long` |
| Rate limit | "Vas muy rápido, intenta en un momento" (429) | `rate_limited`, IP truncada |
| Presupuesto agotado | Mensaje amable + WhatsApp | `budget_exhausted` |
| Proveedor caído / timeout | Mensaje amable + WhatsApp | `llm_error` con tipo, sin contenido |
| Tool con argumentos inválidos | El modelo recibe el error y corrige | `tool_error` |
| Admin sin token o token malo | 401 / 503 | `admin_denied` |

## Supuestos y decisiones abiertas
- [supuesto] Escala (Regla 0 de system-design): `dimension` = conversaciones/día · `current_value` = 0 ·
  `expected_peak` = 50/día · `horizon` = 2 semanas. Aprobado como supuesto de diseño, no capacidad comprobada (A1).
- [supuesto] La key de Gemini es de Google AI Studio; en free tier Google puede usar los datos para mejorar
  sus productos → aviso "usa datos de prueba" en la UI. **Dueño: Jonathan.**
- [hipótesis] `gemini-3.8-flash` con thinking `low` mantiene p95 ≤ 8 s; si no, bajar a `gemini-3.5-flash-lite`.
- [supuesto] El costo por conversación ronda 0.8 MXN; se reemplaza por el dato medido en evals.
- Resuelta: origen Workana = propuesta para un prospecto real, sin contratación ni pago (NFR-05).

## Trade-offs de system design (solo resiliencia, costo y seguridad)
- **Llamada externa al LLM:** deadline total de ~20 s por turno (A5): cada llamada recibe como timeout el tiempo
  que queda del turno, y solo se reintenta una vez en 429/5xx si todavía queda margen (seguro: ningún efecto ocurre
  antes de que el modelo responda). Circuit breaker posponible (A4). *Ganas:* respuesta antes del corte de 30 s
  del router de Heroku. *Pagas:* turnos largos terminan en fallback en vez de esperar.
- **Disponibilidad vs. consistencia:** se prefiere disponibilidad (el prospecto siempre recibe *algo*:
  fallback + WhatsApp); los leads se escriben síncronos en SQLite para no perder el que sí entró.
- **SQLite efímero:** *Ganas:* cero infraestructura. *Pagas:* se borra en cada reinicio o deploy del dyno
  (al menos uno cada 24 h). Uso exclusivo para la demo con datos de prueba (A8); se declara en README. **Trigger T2:** leads con cliente real ⇒ Heroku Postgres Essential-0.
- **Sesiones y rate limit en memoria:** obligan a 1 proceso. **Trigger T1:** >1 dyno o worker ⇒ Redis.
- **Costo:** presupuesto diario de tokens + rate limit por IP + alerta de presupuesto en Google.
  **Trigger T4:** gasto acumulado > 150 MXN ⇒ cambiar a `gemini-3.5-flash-lite`.
- **Seguridad del agente:** mínimo privilegio en tools (catálogo de solo lectura + el lead de la propia sesión);
  ningún dato ajeno es alcanzable por prompt injection. MCP enmascara teléfonos (A8): el modelo que consulta por MCP
  no recibe teléfonos completos; la API admin con token sí los devuelve. La conversación con Sofía sí envía al
  proveedor lo que el prospecto escribe (incluido su teléfono): por eso la demo usa solo datos de prueba.
- **Sistemas adyacentes:** Gemini API, router de Heroku, GitHub Actions, Claude Desktop (MCP), wa.me, placehold.co.

## Riesgo por acción
| Acción | Clase | Gate |
|---|---|---|
| Merge de cada PR a `main` | Medio | CI verde + verify + firma de Jonathan |
| Poner `GEMINI_API_KEY` y `ADMIN_TOKEN` (Heroku y GitHub) | Alto (secreto/dinero) | Solo Jonathan; nunca en chat ni repo |
| Deploy a Heroku | Alto (producción pública) | cto-review + Jonathan ejecuta |
| Correr evals contra el modelo real | Medio (gasto) | `workflow_dispatch` manual de Jonathan |
| Exponer la URL pública | Medio (abuso, costo) | REQ-11, REQ-12 + alerta de presupuesto |
| Guardar nombre y teléfono | Medio (PII) | REQ-15, NFR-03, enmascarado en MCP, aviso de datos de prueba |
| Config de MCP con token admin en su Mac | Medio | Token solo en config local |

## Release, rollback y evidencia
Release: `git push heroku main:main` (Jonathan). Evidencia: `/health` 200 + guion de humo en `docs/DEPLOY.md`.
Rollback: `heroku releases` → `heroku rollback vNN`. Verify por PR antes de cada merge; cto-review antes del deploy.

## Métricas de resultado
| Métrica | Fuente | Baseline | Review | Decisión |
|---|---|---|---|---|
| Flujo demo completo en vivo (sí/no) | Ensayo 14-oct 09:00 | No corre | 14-oct 09:30 | continuar / revisar / parar |
| Escenarios críticos que pasan | `live-smoke` / `evals/` en Actions | — | 14-oct 09:30 | 100% requerido: un crítico fallado = parar (A6) |
| Escenarios no críticos que pasan (n/total) | `evals/` en Actions | — | 14-oct 09:30 | informativo; < 75% ⇒ revisar |
| Tokens y costo por conversación | `/api/admin/usage`, evals | — | 15-oct | > 2 MXN ⇒ revisar modelo |
| p95 de latencia por turno | logs / evals | — | 15-oct | > 8 s ⇒ revisar modelo |

## Archivos afectados (estimación, no contrato)
`app/` (config, catalog, leads, tools, prompts, agent, guards, sessions, main, `llm/`), `static/`,
`tests/`, `.github/workflows/`, `Dockerfile`, `.dockerignore`, `heroku.yml`, `requirements*.txt`,
`pyproject.toml`, `mcp/`, `evals/`, `README.md`, `docs/`, `CLAUDE.md`, `HANDOFF.md`, `LICENSE`.
Se borran `main.py` (queda en la historia) y `QA_REPORT.md` (se archiva con nota de inexactitud).

## Definition of Done
- [ ] `pytest` verde sin red ni keys; CI verde en cada PR mergeado
- [ ] Cero `innerHTML` con datos en `static/`; CSP sin `unsafe-inline` en scripts
- [ ] `/api/admin/*` responde 401 sin token
- [ ] Tarjetas solo desde resultados de tools (prueba automatizada)
- [ ] App corre en Heroku Basic con `/health` 200 (evidencia de Jonathan)
- [ ] Flujo demo completo en el celular (evidencia de Jonathan)
- [ ] README sin afirmaciones no verificadas; LICENSE presente
- [ ] (SHOULD-1) MCP responde `lead_stats` en Claude Desktop (evidencia de Jonathan)
- [ ] `live-smoke` contra el modelo real en verde, sin críticos fallados (REQ-32)
- [ ] (SHOULD-2) Tabla de evals con resultados reales en el README
