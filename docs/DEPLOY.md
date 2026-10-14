# Deploy de InmoBot en Heroku (runbook)

Lo ejecuta una persona. El agente que escribió este runbook nunca despliega ni toca secretos.
Cada paso incluye **Verifica:** con lo que debes ver. Si no coincide, detente y revisa ese paso antes de seguir.

- **Plataforma:** Heroku, stack `container`.
  - Heroku construye la imagen con `heroku.yml` + `Dockerfile`, así que no necesitas Docker en tu máquina.
- **Dyno:** Basic. Cuesta $7 USD/mes, prorrateado por segundo, y está siempre encendido.
  - Eco ($5 USD/mes) se duerme a los 30 min y borra el disco cada vez que despierta.
- **Disco efímero:** SQLite vive en `/tmp`. Se borra en cada deploy o reinicio, y Heroku reinicia el dyno al menos una vez cada 24 h.
  - Úsalo solo para la demo, con datos de prueba.

## Límites que debes conocer antes de desplegar
Vienen del Verify Report del PR #2 (`docs/reviews/`).

- **Datos:**
  - SQLite vive en `/tmp`, un disco efímero: se borra en cada deploy o reinicio. Úsalo solo para la demo, con datos de prueba.
  - Los leads de un ensayo se pierden si vuelves a desplegar.
- **Tiempo por turno: ~20 s.**
  - Cuenta desde que la app recibe la petición. No incluye la cola previa del router de Heroku, que corta a los 30 s.
  - Si el modelo se cuelga, Sofía responde con un mensaje amable y el botón de WhatsApp. Una respuesta tardía se descarta antes de ejecutar cualquier tool.
- **Costo:**
  - Una conversación completa de 5 turnos midió ~18–20 mil tokens de entrada (live-smoke 6: 18,450). Eso es ≈ $0.016 USD ≈ 0.3 MXN.
  - `DAILY_TOKEN_BUDGET=800000` equivale a unas 40 conversaciones al día, **≈ 12 MXN al día como estimación**.
  - **No es un máximo garantizado:**
    - El contador vive en memoria y vuelve a cero en cada reinicio o deploy del dyno.
    - No incluye los tokens de las llamadas abandonadas por timeout, porque nunca llega su conteo.
  - **El límite real de gasto es el spend cap mensual del proyecto en AI Studio** (https://aistudio.google.com/spend).
    - Google lo marca como experimental y tarda ~10 min en aplicarse.
    - Complementa con una alerta de presupuesto en Google Cloud Billing.
- **Concurrencia:** hasta 16 llamadas al modelo a la vez. Si se saturan, los turnos nuevos reciben el mensaje amable.
- **Calidad medida:**
  - 6 corridas de `live-smoke`. La última, sobre el SHA mergeado, pasó 3/3 críticos.
  - La latencia p95 es desconocida; el máximo observado fue 9.8 s.
  - El escenario de prompt injection valida la **capa determinista**, no la resistencia general del modelo.
  - El rechazo de temas ajenos no se ha probado contra el modelo real.
- **Proveedor:** el adaptador de Claude (Anthropic) está **pendiente de validación real**. En Heroku se usa Gemini.

## Emergencia (tenlo a la mano)
- **Apagar ya**, sin borrar nada:
  ```bash
  heroku ps:scale web=0 -a inmobot-sofia
  ```
  Usa `inmobot-sofia-jg` si ese fue el nombre.
- **Volver a la versión anterior:**
  ```bash
  heroku releases -a inmobot-sofia
  heroku rollback vNN -a inmobot-sofia
  ```
- **Si crees que la key de Gemini se filtró:**
  1. Bórrala en https://aistudio.google.com/apikey y crea otra.
  2. Cárgala con el bloque `read -s` del paso 3.

## 0. Requisitos (una sola vez)

1. Abre la app Terminal.
2. Corre `heroku --version`.
   - **Verifica:** imprime algo como `heroku/x.y.z darwin-x64 node-vXX`.
   - Si dice `command not found`, instala la CLI con el instalador oficial: https://devcenter.heroku.com/articles/heroku-cli
3. Corre `heroku login` (se abre el navegador). Luego corre `heroku auth:whoami`.
   - **Verifica:** imprime tu correo de Heroku.
4. Corre `git --version`.
   - **Verifica:** imprime una versión de git.

## 1. Código actualizado

```bash
cd ~                                   # o la carpeta donde guardas tus repos
git clone https://github.com/astraDukoWave/inmobot-demo.git   # solo si no lo tienes clonado
cd inmobot-demo
git checkout main
git pull origin main
git log --oneline -1
```
**Verifica:** el SHA corto que imprime `git log` es el último merge a `main` (te lo doy al pedirte el deploy).

## 2. Crear la app (una sola vez)

```bash
APP=inmobot-sofia
heroku create "$APP" --stack container
```
- Si responde `Name is already taken`, usa el nombre de respaldo:
  ```bash
  APP=inmobot-sofia-jg
  heroku create "$APP" --stack container
  ```
- **Verifica:**
  - La salida muestra una URL del tipo `https://inmobot-sofia-xxxxxxxxxxxx.herokuapp.com/`. Heroku agrega un sufijo aleatorio: usa esa URL exacta.
  - `git remote -v` muestra dos líneas `heroku`.
  - `heroku stack -a "$APP"` marca `* container`.

## 3. Configuración y secretos

Ninguna key se pega en el chat ni se escribe en archivos del repo.

```bash
heroku config:set LLM_PROVIDER=gemini GEMINI_MODEL=gemini-3.8-flash TRUST_PROXY=true DAILY_TOKEN_BUDGET=800000 -a "$APP"

# La key de Gemini se teclea sin que se vea ni quede en el historial:
printf "Pega tu GEMINI_API_KEY y presiona Enter: "; read -s GEMINI_KEY; echo
heroku config:set GEMINI_API_KEY="$GEMINI_KEY" -a "$APP" > /dev/null && echo "GEMINI_API_KEY guardada"
unset GEMINI_KEY

# Token de admin aleatorio (para /api/admin/* y para el servidor MCP):
heroku config:set ADMIN_TOKEN="$(openssl rand -hex 24)" -a "$APP" > /dev/null && echo "ADMIN_TOKEN guardado"
```

**Opcional: botón de WhatsApp.** Pon el número del asesor como `52` + 10 dígitos, sin espacios ni `+`. Cualquiera que use la demo verá ese número en el enlace.
```bash
heroku config:set WHATSAPP_NUMBER=52XXXXXXXXXX -a "$APP"
```
Sin `WHATSAPP_NUMBER`, Sofía dice que un asesor llamará al teléfono registrado y no muestra ningún botón.

**Verifica sin mostrar valores:**
```bash
heroku config -a "$APP" | cut -d: -f1
```
Debe listar `LLM_PROVIDER`, `GEMINI_MODEL`, `GEMINI_API_KEY`, `ADMIN_TOKEN`, `TRUST_PROXY` y `DAILY_TOKEN_BUDGET`.
Nunca corras `heroku config` ni `heroku config:get` sin filtro mientras compartes pantalla o grabas: muestran los secretos.

## 4. Deploy

```bash
git push heroku main:main
```
- **Verifica:** la salida termina con `Verifying deploy... done.` La primera construcción tarda unos 2 a 4 minutos.
- Después, fija el dyno Basic:
  ```bash
  heroku ps:type web=basic -a "$APP"
  heroku ps -a "$APP"
  ```
- **Verifica:** `heroku ps` muestra `web (Basic): up`.

## 5. Pruebas de humo

```bash
URL=$(heroku apps:info -a "$APP" | awk '/Web URL/ {print $3}'); URL=${URL%/}; echo "$URL"
curl -s "$URL/health"; echo
curl -s -o /dev/null -w "admin sin token: %{http_code}\n" "$URL/api/admin/leads"
curl -s -H "Authorization: Bearer $(heroku config:get ADMIN_TOKEN -a "$APP")" "$URL/api/admin/stats"; echo
```
**Verifica, en orden:**
1. Se imprime la URL.
2. `/health` responde `{"status":"ok",...,"provider":"gemini","model":"gemini-3.8-flash","llm_configured":true,...}`.
3. Sin token: `admin sin token: 401`.
4. Con token: un JSON con `"total_leads"`.

## 6. Prueba en el celular

1. Abre la URL en el celular.
2. Toca **Hablar con Sofía** y luego el chip `Busco casa en Cholula, hasta 2.5 millones, 3 recámaras`.
   - **Verifica:** aparecen 2 tarjetas, Casa Los Fresnos y Paseos de Cholula Residencial.
3. Responde forma de pago y plazo. Da un nombre y un teléfono **de prueba**. Pide visitar Casa Los Fresnos.
   - **Verifica:** aparece la nota verde "Solicitud de visita registrada".
4. Pide un asesor.
   - **Verifica:** aparece el botón de WhatsApp, si configuraste `WHATSAPP_NUMBER`.
5. Mientras chateas, en la terminal corre `heroku logs --tail -a "$APP"`. Para salir: Ctrl+C.
   - **Verifica:** aparecen líneas `"event": "turn"` con `latency_ms` y tokens, sin el contenido de los mensajes.

## Rollback

```bash
heroku releases -a "$APP"          # lista v1, v2, ...
heroku rollback vNN -a "$APP"      # NN = la versión anterior que sí funcionaba
```
**Verifica:** `curl -s "$URL/health"` vuelve a responder `ok`.

## Apagar después de la entrevista (opcional, ahorra créditos)

```bash
heroku ps:scale web=0 -a "$APP"    # apaga sin borrar la app
heroku ps:scale web=1 -a "$APP"    # la vuelve a encender
```

## Plan B: correr en tu Mac sin Docker (requiere internet para Gemini)

1. Corre `python3 --version`.
   - **Verifica:** es 3.10 o mayor.
   - Si es menor, este plan B no aplica: usa el video de respaldo.
2. Instala y arranca:
   ```bash
   cd ~/inmobot-demo   # la carpeta donde clonaste el repo
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   nano .env           # escribe tu key después de GEMINI_API_KEY=, guarda con Ctrl+O, Enter, Ctrl+X
   uvicorn app.main:create_app --factory --env-file .env --port 8000
   ```
3. Abre http://localhost:8000 en la laptop.
   - **Verifica:** carga la página de InmoBot.

Sin internet no hay modelo: usa el video de respaldo de la demo.
