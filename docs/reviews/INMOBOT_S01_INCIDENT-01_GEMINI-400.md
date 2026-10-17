# Incidente 01 — Gemini responde 400 en Heroku
- **Fecha:** 2026-10-14 · **Ciclo:** INMOBOT-S01
- **Severidad:** alta. Bloqueaba el flujo principal en producción.
- **Estado:** resuelto. Jonathan recargó la key y validó la app desde el celular.
- **Versión del registro:** v2, 2026-10-17.
  - Corrige la secuencia del diagnóstico.
  - Ya no atribuye la corrección a un método de recarga que nadie verificó.

## Síntoma
Producción corría el deploy `dcce6ff` en Heroku, con dyno Basic. A primera vista todo estaba bien:
- `/health` respondía 200 con `"llm_configured": true`.
- El admin con token respondía 200.

Pero al tocar el chip de Cholula en el celular:
- Gemini respondía **HTTP 400 en ~149 ms, con un cuerpo HTML genérico**.
- El turno quedaba con `fallback = "bad_request"`, `tools = []` y `cards = []`.
- La interfaz mostraba el mensaje de respaldo y el botón de WhatsApp.

`/api/chat` respondía 200, pero eso **no** cuenta como éxito del escenario.

## Cronología
| # | Paso | Resultado | Fuente |
|---|---|---|---|
| 1 | Revisión desde el repo, sin acceso a Heroku | Es el mismo código que pasó la corrida 6 de `live-smoke` (`dcce6ff` contiene `7be5400`). Son el mismo modelo y el mismo SDK. `X-Server-Timeout` sale con el mismo valor ("10"). El código queda descartado como causa | [verified-this-session] 2026-10-14 |
| 2 | Prueba local del transporte (httpx) | Una key con caracteres de control (por ejemplo, el ESC de un pegado en terminal) o con comillas **sí llega** a Google. Un carácter no-ASCII (espacio de ancho cero, NBSP) lo rechaza httpx antes de enviarlo, con otro error, no con un 400 de Google | [verified-this-session] 2026-10-14 |
| 3 | Hipótesis | La key guardada tiene caracteres de más. La frontera de Google rechaza ese header malformado con un 400 HTML genérico, sin llegar al modelo. Eso cuadra con los ~149 ms y con el HTML | Hipótesis, sin confirmar en ese momento |
| 4 | **Diagnóstico, plan A:** correr un script en el dyno con `heroku run -a "$APP" …` | **Falló con `not_found`.** El script no llegó a correr | Jonathan |
| 5 | Estado de esa terminal | La variable `APP` estaba **vacía**, y los comandos del runbook dependían de ella | Jonathan |
| 6 | **Diagnóstico, plan B, desde la Mac:** `heroku config:get GEMINI_API_KEY` pasado por `wc -c` (longitud) y por `tr` + `od` (solo los caracteres que no pertenecen a una key de Google, en hexadecimal). La key nunca se mostró | **Se confirmaron caracteres extra** en la key guardada | Jonathan |
| 7 | **Corrección:** recarga de la key | Hecha. **No quedó registrado con qué método se recargó**, así que este documento no la atribuye a ninguno | Jonathan |
| 8 | **Validación desde el celular:** pruebas del paso 6 del runbook | **Pasaron.** El criterio de aceptación era que el chip de Cholula mostrara 2 tarjetas (Casa Los Fresnos y Paseos de Cholula Residencial) sin fallback | Jonathan |

**Causa del `not_found` (paso 4):** no se determinó. Una posibilidad, sin comprobar, es la variable `APP` vacía, porque el comando la usaba en `-a`.

## Causa
- **Causa raíz:** la key guardada en Heroku tenía caracteres extra. Lo sostienen tres hechos:
  - el 400 HTML en ~149 ms;
  - los caracteres extra confirmados en el paso 6;
  - las pruebas, que pasaron después de recargar la key.
- **Cómo entraron esos caracteres:** no se determinó. El runbook de entonces cargaba la key pegándola en la terminal con `read -s`.
- **Factor contribuyente:** los comandos del runbook dependían de una variable (`APP`) definida en otra terminal.
- **Factor de detección:** `/health` reportaba `llm_configured: true` porque *había* una key, no porque la key *sirviera*.

La corrección fue de configuración. No cambió código.

Heroku reinicia la app y crea un release nuevo cada vez que cambia una config var ([Heroku Dev Center: Config Vars](https://devcenter.heroku.com/articles/config-vars)).

## Acciones
| Acción | Estado |
|---|---|
| Runbook: el método principal para cargar la key es editarla en Heroku → *Settings* → *Config Vars*. No pasa por la terminal ni por filtros | Hecho en este PR (`docs/DEPLOY.md`, paso 3) |
| Runbook: verificar la forma de la key guardada sin mostrarla, con los comandos del plan B. Solo detecta; no modifica nada | Hecho en este PR (`docs/DEPLOY.md`, paso 3) |
| Runbook: el nombre de la app va escrito en cada comando. Ningún bloque depende de variables de otro bloque ni de otra terminal | Hecho en este PR (`docs/DEPLOY.md`) |
| Runbook: bloques sin comentarios, un comando por línea, y apagar y encender en bloques separados | Hecho en este PR (`docs/DEPLOY.md`) |
| `/health` y su verificación: distinguir key presente, formato válido y funcionamiento comprobado contra el proveedor, sin llamadas de pago en el healthcheck habitual | [LB-14](../BACKLOG.md), propuesto para el ciclo S02. Requiere spec aprobado |
| **Retirado:** recargar la key con el portapapeles filtrado (`pbpaste \| tr -cd …`), que proponía la primera versión de este PR | Un filtro silencioso puede esconder el problema en lugar de mostrarlo, y no hay evidencia de que ese haya sido el método usado |

## Lecciones
1. `/health` decía `llm_configured: true` porque había *una* key, no porque la key *sirviera*. Un healthcheck que no prueba la dependencia real solo comprueba la configuración.
2. Un filtro que "limpia" la key sin avisar también esconde el síntoma. Es mejor detectar y avisar (plan B) que transformar en silencio.
3. Un comando que depende de una variable de otra terminal falla de formas confusas. El nombre de la app va escrito en cada comando.
