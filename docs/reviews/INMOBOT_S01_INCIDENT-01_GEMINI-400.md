# Incidente 01 — Gemini responde 400 en Heroku
- **Fecha:** 2026-10-14 · **Ciclo:** INMOBOT-S01
- **Severidad:** alta, porque bloqueaba el flujo principal en producción.
- **Estado:** resuelto y validado por Jonathan desde el celular.

## Síntoma
Deploy `dcce6ff` en Heroku, dyno Basic. `/health` respondía 200, `"llm_configured": true` y el admin con token respondía 200.

Al tocar el chip de Cholula en el celular:
- Gemini respondía **HTTP 400 en ~149 ms, con un cuerpo HTML genérico**.
- El turno quedaba con `fallback = "bad_request"`, `tools = []` y `cards = []`.
- La interfaz mostraba el mensaje de respaldo y el botón de WhatsApp.

El `/api/chat` respondía 200, pero eso **no** cuenta como éxito del escenario.

## Investigación
**Lo descartado [verified-this-session]:**
- Era el mismo código que pasó la corrida 6 de `live-smoke` (`dcce6ff` contiene `7be5400`).
- El modelo y la versión del SDK eran los mismos.
- `X-Server-Timeout` salía con el mismo valor ("10").

**Lo comprobado sobre el transporte [verified-this-session]:**
- httpx **sí envía** al servidor una key con caracteres de control (por ejemplo, los códigos ESC de un pegado en terminal) o con comillas.
- Un carácter no-ASCII (espacio de ancho cero, NBSP) lo rechaza httpx localmente. Habría producido otro error, no un 400 de Google.

**Hipótesis previa al diagnóstico:**
- La key quedó guardada con caracteres de más.
- La frontera de Google rechaza ese header malformado con un 400 HTML genérico, sin llegar al modelo.
- Eso cuadraba con los ~149 ms y con el HTML.

**Diagnóstico ejecutado por Jonathan** (script en el dyno, sin imprimir la key; solo longitud, prefijo, caracteres sobrantes en hexadecimal y los últimos 4):
- **Caracteres extra en la key guardada:** hipótesis **confirmada**.
- **La variable `APP` estaba vacía** en la terminal donde corrió los comandos. Una terminal nueva no conserva la variable, y los comandos del runbook dependen de ella.

## Corrección
1. **Key recargada desde el portapapeles, filtrada:** `pbpaste | LC_ALL=C tr -cd 'A-Za-z0-9_-'`. La key nunca se mostró en pantalla y el portapapeles se vació después.
2. Heroku reinició el dyno con la key nueva. **Sin cambios de código ni redeploy.**

## Validación (Jonathan, desde el celular)
Repitió las pruebas del paso 6 del runbook y **todas pasaron**. El chip de Cholula mostró las **2 tarjetas esperadas** (Casa Los Fresnos y Paseos de Cholula Residencial), sin fallback.

## Lecciones y acciones
| Acción | Estado |
|---|---|
| Cada bloque del runbook fija `APP=...` al inicio, para no depender de la terminal anterior | Hecho en este PR (`docs/DEPLOY.md`) |
| Cargar la key desde el portapapeles filtrado en lugar de `read -s` | Hecho en este PR (`docs/DEPLOY.md`) |
| Validar el formato de `GEMINI_API_KEY` al arrancar y reportarlo en `/health` (sin revelarla), para que `llm_configured` no engañe | Backlog LB-14. Es código y requiere deploy: no entra antes del congelamiento |

**Lección:** `/health` decía `llm_configured: true` porque había *una* key, no porque la key *sirviera*. Un healthcheck que no prueba la dependencia real solo comprueba la configuración.
