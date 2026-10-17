# Deploy de InmoBot en Heroku (runbook)

Este runbook lo ejecuta una persona. El agente que lo escribió nunca despliega ni toca secretos.

## Cómo usar este runbook
- **Cada bloque se copia y se pega completo, tal como está.**
  - Los bloques no llevan comentarios. En zsh, el shell por defecto de macOS, un `#` pegado en la terminal no se trata como comentario: la opción `INTERACTIVE_COMMENTS` viene apagada ([manual de zsh](https://zsh.sourceforge.io/Doc/Release/Options.html)).
  - Un comando por línea.
- **El nombre de la app va escrito en cada comando** (`-a inmobot-sofia`).
  - Ningún bloque depende de variables definidas en otro bloque ni en otra terminal (incidente 01).
  - Si tu app tiene otro nombre, por ejemplo `inmobot-sofia-jg`, reemplázalo en cada comando antes de pegarlo.
- Los marcadores `52XXXXXXXXXX` y `vNN` se reemplazan antes de pegar.
- Cada paso incluye **Verifica:** con lo que debes ver. Si no coincide, detente y revisa ese paso antes de seguir.

## Plataforma
- **Heroku, stack `container`.** Heroku construye la imagen con `heroku.yml` + `Dockerfile`, así que no necesitas Docker en tu máquina.
- **Dyno Basic:** cuesta $7 USD/mes, prorrateado por segundo, y está siempre encendido.
  - Eco ($5 USD/mes) se duerme a los 30 min y borra el disco cada vez que despierta.
- **Disco efímero:** SQLite vive en `/tmp`. Se borra en cada deploy o reinicio, y Heroku reinicia el dyno al menos una vez cada 24 h.
  - Úsalo solo para la demo, con datos de prueba.

## Límites que debes conocer antes de desplegar
Vienen del Verify Report del PR #2 (`docs/reviews/`).

- **Datos:** los leads de un ensayo se pierden si vuelves a desplegar o si el dyno se reinicia.
- **Tiempo por turno: ~20 s.**
  - Cuenta desde que la app recibe la petición. No incluye la cola previa del router de Heroku, que corta a los 30 s.
  - Si el modelo se cuelga, Sofía responde con un mensaje amable y el botón de WhatsApp. Una respuesta tardía se descarta antes de ejecutar cualquier tool.
- **Costo:**
  - Una conversación completa de 5 turnos midió ~18–20 mil tokens de entrada (live-smoke 6: 18,450). Eso es **≈ $0.016 USD ≈ 0.3 MXN, estimado** con el precio de lista y un tipo de cambio supuesto de 18.5.
  - `DAILY_TOKEN_BUDGET=800000` equivale a unas 40 conversaciones al día, **≈ 12 MXN al día como estimación**.
  - **No es un máximo garantizado:**
    - El contador vive en memoria y vuelve a cero en cada reinicio o deploy del dyno.
    - No incluye los tokens de las llamadas abandonadas por timeout, porque nunca llega su conteo.
  - **El límite real de gasto es el spend cap mensual del proyecto en AI Studio** (https://aistudio.google.com/spend).
    - Google lo marca como experimental y tarda ~10 min en aplicarse.
    - Complementa con una alerta de presupuesto en Google Cloud Billing.
- **Concurrencia:** hasta 16 llamadas al modelo a la vez. Si se saturan, los turnos nuevos reciben el mensaje amable.
- **Calidad medida:**
  - Hubo 6 corridas de `live-smoke`. La última, sobre el SHA mergeado, pasó 3/3 escenarios críticos con 3.0–5.7 s por turno.
  - La latencia p95 de la versión desplegada **no se ha medido**. El máximo observado, 9.8 s, fue en la corrida 4, sobre una versión anterior.
  - El escenario de prompt injection valida la **capa determinista**, no la resistencia general del modelo.
  - El rechazo de temas ajenos no se ha probado contra el modelo real.
- **Proveedor:** el adaptador de Claude (Anthropic) está **pendiente de validación real**. En Heroku se usa Gemini.
- **`/health`:** `llm_configured: true` solo indica que **hay** una key. No dice que la key sirva (incidente 01). La prueba de que funciona es el paso 6.

## Emergencia (tenlo a la mano)
- **Apagar ya, sin borrar nada:** sección [Apagar la app](#apagar-la-app-sin-borrarla).
- **Volver a la versión anterior:** sección [Rollback](#rollback).
- **Si crees que la key de Gemini se filtró:**
  1. Bórrala en https://aistudio.google.com/apikey y crea otra.
  2. Cárgala con el paso 3.2 (Config Vars).
  3. Verifícala con el paso 3.3 y con el paso 6.

## 0. Requisitos (una sola vez)
1. Abre la app Terminal.
2. Corre:
   ```bash
   heroku --version
   ```
   - **Verifica:** imprime algo como `heroku/x.y.z darwin-x64 node-vXX`.
   - Si dice `command not found`, instala la CLI con el instalador oficial: https://devcenter.heroku.com/articles/heroku-cli
3. Inicia sesión. El comando pide una tecla y abre el navegador; termina el login ahí.
   ```bash
   heroku login
   ```
   Después, en un bloque aparte:
   ```bash
   heroku auth:whoami
   ```
   - **Verifica:** imprime tu correo de Heroku.
4. Corre:
   ```bash
   git --version
   ```
   - **Verifica:** imprime una versión de git.

## 1. Código actualizado
Si todavía no tienes el repo en tu Mac, clónalo una vez:
```bash
cd ~
git clone https://github.com/astraDukoWave/inmobot-demo.git
```
Después, cada vez que vayas a desplegar:
```bash
cd ~/inmobot-demo
git checkout main
git pull origin main
git log --oneline -1
```
- Si clonaste el repo en otra carpeta, cambia `~/inmobot-demo` por esa ruta.
- **Verifica:** el SHA corto que imprime `git log` es el último merge a `main`. Te lo doy al pedirte el deploy.

## 2. Crear la app (una sola vez)
```bash
heroku create inmobot-sofia --stack container
```
- Si responde `Name is already taken`, usa el nombre de respaldo y escríbelo en todos los comandos de este runbook:
  ```bash
  heroku create inmobot-sofia-jg --stack container
  ```
- **Verifica:** la salida muestra una URL del tipo `https://inmobot-sofia-xxxxxxxxxxxx.herokuapp.com/`. Heroku agrega un sufijo aleatorio, así que usa esa URL exacta. Luego corre:
  ```bash
  heroku stack -a inmobot-sofia
  ```
  Debe marcar `* container`.

## 3. Configuración y secretos
Ninguna key se pega en el chat ni se escribe en archivos del repo.

### 3.1 Variables que no son secretas
```bash
heroku config:set LLM_PROVIDER=gemini GEMINI_MODEL=gemini-3.8-flash TRUST_PROXY=true DAILY_TOKEN_BUDGET=800000 -a inmobot-sofia
```
- **Verifica:** la salida termina con las 4 variables y sus valores.

### 3.2 Key de Gemini (método principal: Config Vars en el navegador)
1. Abre https://dashboard.heroku.com/apps/inmobot-sofia/settings
2. En la sección **Config Vars**, toca **Reveal Config Vars**.
   - ⚠️ Esto muestra en pantalla los valores, incluidos los secretos. No lo hagas mientras compartes pantalla o grabas.
3. En https://aistudio.google.com/apikey, copia la key con su botón de copiar.
4. Pega la key en Heroku:
   - **Si `GEMINI_API_KEY` ya existe:** toca el lápiz de esa fila, borra todo el valor anterior, pega la key y toca **Save changes**.
   - **Si no existe:** escribe `GEMINI_API_KEY` en *KEY*, pega la key en *VALUE* y toca **Add**.
5. Toca **Hide Config Vars**.

Cada cambio de una config var reinicia la app y crea un release nuevo ([Heroku Dev Center](https://devcenter.heroku.com/articles/config-vars)).

### 3.3 Verifica la key sin mostrarla
Estos comandos **solo detectan**. No modifican la key guardada.

Longitud de la key (imprime solo un número):
```bash
heroku config:get GEMINI_API_KEY -a inmobot-sofia | tr -d '\n' | wc -c
```
Caracteres que no pertenecen a una key de Google, en hexadecimal:
```bash
heroku config:get GEMINI_API_KEY -a inmobot-sofia | LC_ALL=C tr -d 'A-Za-z0-9_\n-' | od -An -tx1
```
- **Verifica:** el segundo comando **no imprime nada**.
- Si imprime algo, la key tiene caracteres extra y debes repetir el paso 3.2. Ejemplos: `20` es un espacio, `1b` es un ESC, `22` son comillas.
- **El formato correcto no demuestra que la key funcione.** No prueba que tenga autorización ni que Gemini esté disponible. Eso lo comprueba el paso 6.

### 3.4 Token de admin (una sola vez; si lo repites, lo cambia)
```bash
heroku config:set ADMIN_TOKEN="$(openssl rand -hex 24)" -a inmobot-sofia > /dev/null
```
- El token protege `/api/admin/*`.
- `> /dev/null` evita que el valor se imprima.

### 3.5 Botón de WhatsApp (opcional)
Escribe el número del asesor como `52` + 10 dígitos, sin espacios ni `+`. Cualquiera que use la demo verá ese número en el enlace.
```bash
heroku config:set WHATSAPP_NUMBER=52XXXXXXXXXX -a inmobot-sofia
```
Sin `WHATSAPP_NUMBER`, Sofía dice que un asesor llamará al teléfono registrado y no muestra ningún botón.

Para quitarlo, por ejemplo después de una demostración:
```bash
heroku config:unset WHATSAPP_NUMBER -a inmobot-sofia
```

### 3.6 Verifica los nombres, sin valores
```bash
heroku config -a inmobot-sofia | cut -d: -f1
```
- **Verifica:** lista `LLM_PROVIDER`, `GEMINI_MODEL`, `GEMINI_API_KEY`, `ADMIN_TOKEN`, `TRUST_PROXY` y `DAILY_TOKEN_BUDGET`, más `WHATSAPP_NUMBER` si lo configuraste.
- Nunca corras `heroku config` ni `heroku config:get` sin filtro mientras compartes pantalla o grabas: muestran los secretos.

## 4. Deploy
```bash
cd ~/inmobot-demo
heroku git:remote -a inmobot-sofia
git push heroku main:main
```
- **Verifica:**
  - `heroku git:remote` responde con la URL `https://git.heroku.com/inmobot-sofia.git`.
  - El push termina con `Verifying deploy... done.` La primera construcción tarda unos 2 a 4 minutos.

Fija el dyno Basic:
```bash
heroku ps:type web=basic -a inmobot-sofia
```
Revisa el estado:
```bash
heroku ps -a inmobot-sofia
```
- **Verifica:** muestra `web (Basic)` y `web.1: up`.

## 5. Pruebas de humo
Este bloque define `URL` y la usa ahí mismo, así que pégalo completo.
```bash
URL="$(heroku apps:info -a inmobot-sofia | awk '/Web URL/ {print $3}' | sed 's#/$##')"
echo "$URL"
curl -s "$URL/health"
echo
curl -s -o /dev/null -w "admin sin token: %{http_code}\n" "$URL/api/admin/leads"
curl -s -H "Authorization: Bearer $(heroku config:get ADMIN_TOKEN -a inmobot-sofia)" "$URL/api/admin/stats"
echo
```
**Verifica, en orden:**
1. Se imprime la URL.
2. `/health` responde `{"status":"ok",...,"provider":"gemini","model":"gemini-3.8-flash","llm_configured":true,...}`. Esto confirma la configuración, no que la key funcione.
3. Sin token: `admin sin token: 401`.
4. Con token: un JSON con `"total_leads"`.

## 6. Prueba en el celular (comprueba que la key funciona)
1. Abre la URL en el celular.
2. Toca **Hablar con Sofía** y luego el chip `Busco casa en Cholula, hasta 2.5 millones, 3 recámaras`.
   - **Verifica:** aparecen 2 tarjetas, Casa Los Fresnos y Paseos de Cholula Residencial, sin el mensaje de respaldo.
3. Responde forma de pago y plazo. Da un nombre y un teléfono **de prueba**. Pide visitar Casa Los Fresnos.
   - **Verifica:** aparece la nota verde "Solicitud de visita registrada".
4. Pide un asesor.
   - **Verifica:** aparece el botón de WhatsApp, si configuraste `WHATSAPP_NUMBER`.
5. Mientras chateas, abre otra terminal y corre el comando de abajo. Para salir: Ctrl+C.
   ```bash
   heroku logs --tail -a inmobot-sofia
   ```
   - **Verifica:** aparecen líneas `"event": "turn"` con `latency_ms` y tokens, sin el contenido de los mensajes.
   - El turno del chip de Cholula trae `"fallback": null` y `"cards": [4, 5]`.

## Rollback
1. Lista las versiones:
   ```bash
   heroku releases -a inmobot-sofia
   ```
2. Elige la versión anterior que sí funcionaba. Reemplaza `vNN` por ella antes de pegar:
   ```bash
   heroku rollback vNN -a inmobot-sofia
   ```
3. **Verifica:** repite el paso 5.

Un rollback también regresa las config vars de esa versión, incluida la key ([Heroku Dev Center](https://devcenter.heroku.com/articles/releases#rollback)). Después de un rollback, repite el paso 3.3.

## Apagar la app (sin borrarla)
```bash
heroku ps:scale web=0 -a inmobot-sofia
```
Verifica el estado:
```bash
heroku ps -a inmobot-sofia
```
- **Verifica:** ya no aparece ninguna línea `web.1`.
- Con la app apagada, nada llega a Sofía, así que no hay llamadas al modelo.

## Encender la app de nuevo
Es un bloque aparte a propósito: no lo pegues junto con el de apagar.
```bash
heroku ps:scale web=1 -a inmobot-sofia
```
Espera unos 30 segundos y verifica el estado:
```bash
heroku ps -a inmobot-sofia
```
- **Verifica:** muestra `web (Basic)` y `web.1: up`. Después, repite el paso 5.

## Plan B: correr en tu Mac sin Docker (requiere internet para Gemini)
1. Revisa tu versión de Python:
   ```bash
   python3 --version
   ```
   - **Verifica:** es 3.10 o mayor. Si es menor, este plan B no aplica: usa el video de respaldo.
2. Instala, una sola vez:
   ```bash
   cd ~/inmobot-demo
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   cp .env.example .env
   ```
3. Abre `.env` con un editor:
   ```bash
   nano ~/inmobot-demo/.env
   ```
   - Pega tu key después de `GEMINI_API_KEY=`.
   - Guarda con Ctrl+O y Enter, y sal con Ctrl+X.
   - `.env` está en `.gitignore`: nunca se sube al repo.
4. Arranca la app:
   ```bash
   cd ~/inmobot-demo
   .venv/bin/uvicorn app.main:create_app --factory --env-file .env --port 8000
   ```
5. Abre http://localhost:8000 en la laptop.
   - **Verifica:** carga la página de InmoBot.

Sin internet no hay modelo: usa el video de respaldo de la demo.
