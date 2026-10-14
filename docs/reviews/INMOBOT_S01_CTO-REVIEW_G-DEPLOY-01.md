# CTO Review — gate G-DEPLOY-01: merge PR #3 + deploy a Heroku
- **Ciclo:** INMOBOT-S01 · **Fecha:** 2026-10-14
- **Artefacto:** PR #3 @ `913e021`
- **sha256 de `docs/DEPLOY.md` al revisar:** `c5dea40257d78805d44f81999662fb2b9d337720faef2d3516a7c6afe92cc0ec`

## Clasificación por acción
| Acción | Clase | Gate |
|---|---|---|
| Merge del PR #3 a `main` | rutina | CI + verify + firma de Jonathan |
| Crear la app y fijar el dyno Basic | alto (dinero) | la ejecuta Jonathan |
| Cargar `GEMINI_API_KEY` y `ADMIN_TOKEN` | alto (secretos) | la ejecuta Jonathan, con `read -s` |
| `git push heroku main:main` (URL pública) | alto (producción) | este dictamen + Jonathan |
| `WHATSAPP_NUMBER` con número real | alto (dato personal visible en el enlace) | decisión de Jonathan |

## Verificaciones
| Claim | Etiqueta |
|---|---|
| Sin secretos en el repo; `.env` fuera de git | [verified-this-session]: escaneo de patrones de keys limpio |
| `CMD` con `$PORT` y arranque solo con los archivos de la imagen (código final) | [verified-this-session]: simulación fuera de Docker |
| La key de Gemini funciona | [verified-this-session] desde GitHub Actions (live-smoke 6). Desde Heroku: [inherited-unverified] |
| `docker build` | [inherited-unverified]: Docker Hub bloqueado en la sesión del agente. Lo verifica el build de Heroku |
| URL con sufijo aleatorio; dyno por default | [inherited-unverified]: el runbook pide copiar la URL exacta y fija Basic |

## Veredicto: APROBAR CON CAMBIOS (aplicados en `913e021`)
1. **El runbook no imprime valores de secretos:** `heroku config | cut -d: -f1`. *Por qué:* el autor puede estar grabando o compartiendo pantalla.
2. **Sección de emergencia:** apagar con `ps:scale web=0`, rollback y rotación de la key.

## Requisitos de alto riesgo
- **Rollback:**
  - Primer deploy: apagar con `ps:scale web=0`.
  - Siguientes: `heroku rollback vNN`.
- **Blast radius:**
  - Dinero: tope diario de tokens (estimación) + rate limit por IP + spend cap mensual de AI Studio.
  - Datos: solo de prueba, en SQLite efímero.
  - Admin: protegido con token.
- **Dueño:** Jonathan.
- **Observabilidad:**
  - `heroku logs --tail`: una línea por turno, sin contenido.
  - `/health` y `/api/admin/usage`.
  - El panel de uso de AI Studio.

## Corrección posterior (pedida por Jonathan)
El dictamen en chat decía "tope de ≈12 MXN/día". Lo correcto es **≈12 MXN/día como estimación, no como máximo garantizado**, por dos razones:
- El contador de `DAILY_TOKEN_BUDGET` vive en memoria y vuelve a cero en cada reinicio o deploy.
- No cuenta las llamadas abandonadas por timeout.

El límite real es el spend cap mensual del proyecto en AI Studio, que Google marca como experimental y que tarda ~10 min en aplicarse.

## Decisiones humanas registradas
- **Merge del PR #3:** autorizado por Jonathan sobre `913e021` (merge commit → `main` @ `dcce6ff`).
- **WhatsApp:** Jonathan usa su propio número solo durante la demo y lo configura él como config var. **El número no está en el repo.** Lo retira después de la entrevista con `heroku config:unset WHATSAPP_NUMBER`.
- **Gasto:**
  - `DAILY_TOKEN_BUDGET=800000`.
  - Alerta de presupuesto en Google Cloud.
  - Revisar el spend cap del proyecto en AI Studio.
