# InmoBot S01 — Auditoría de línea base
Fecha: 2026-10-13 · Commit auditado: `main` @ `53d1006` · Método: código ejecutado en esta sesión, no reportes.

Etiquetas: `[verified-this-session]` comprobado aquí · `[inherited-unverified]` heredado sin comprobar · `[contradicted]` la evidencia lo contradice.

## Ejecución
| Prueba | Resultado |
|---|---|
| `python -c "import main"` sin `GITHUB_TOKEN` | `openai.OpenAIError: Missing credentials` — la app no arranca |
| Con `GITHUB_TOKEN=dummy`: `GET /` | 200 |
| `GET /leads` sin autenticación | 200 (expone la tabla completa) |
| `POST /chat` | 500 `APIConnectionError` |
| `GET /health` | 404 |
| `pip install -r requirements.txt` | `openai>=1.55.0` resuelve hoy a 3.29.0 (sin tope) |

## Hallazgos de la revisión del 13-oct
| # | Afirmación | Etiqueta | Evidencia |
|---|---|---|---|
| 1 | Único backend: GitHub Models (main.py:29-32), retirado | [verified-this-session] | Código + changelog oficial de GitHub: retiro total el 30-jul-2026. El 500 local es consistente, no prueba por sí solo el retiro. |
| 2 | Un solo main.py (~270 líneas), dos llamadas al LLM por turno | [verified-this-session] | 270 líneas; `extract_intent` (L198) y `chat` (L220) |
| 3 | Acciones por etiquetas de texto; Calendly fijo | [verified-this-session] | L167-183; enlace fijo en L248 |
| 4 | Leads en SQLite, sesiones en memoria, UI en `static/index.html` | [verified-this-session] | L39-62; `CONVERSATIONS` crece sin límite |
| 5 | Sin pruebas, sin CI, sin `/health` | [verified-this-session] | Sin `tests/`; 0 workflows por API; `/health` 404 |
| 6 | Dockerfile con puerto 8000 fijo; sin `.dockerignore` | [verified-this-session] | Dockerfile L10-12 |
| 7 | XSS en `linkifyMessageHtml` | [verified-this-session] | index.html L448-470: solo escapa las URLs; el resto del texto entra crudo a `innerHTML`. Las tarjetas también usan `innerHTML` (L479). |
| 8 | `/leads` expone nombres y teléfonos sin auth | [verified-this-session] | main.py L258-264; `GET /leads` 200 |
| 9 | CORS `*`; ID de sesión adivinable | [verified-this-session] | main.py L21-26; index.html L427 `'session_'+Date.now()` |
| 10 | Sin tope de mensaje, sin rate limit, sin defensa ante prompt injection | [verified-this-session] | `ChatRequest` sin validación; el prompt no tiene reglas al respecto |
| 11 | El prompt inventa urgencia | [verified-this-session] | L184 y, además, L172 ("que no te ganen la oportunidad") |
| 12 | README: "10 propiedades reales" | [verified-this-session] — falso | README L51; `properties.json` es ficticio, imágenes de placehold.co |
| 13 | README: "Zero alucinaciones" | [verified-this-session] — sin evidencia | README L191; no hay pruebas ni evals |
| 14 | README pide `OPENAI_API_KEY`; el código lee `GITHUB_TOKEN` | [verified-this-session] | README L33/144/243 vs main.py L31 |
| 15 | Licencia MIT sin archivo LICENSE | [verified-this-session] | README L264; no existe LICENSE |
| 16 | `QA_REPORT.md` inexacto | [contradicted] (en lo grave) | L47 afirma resistencia a prompt injection: no hay ninguna defensa |
| 17 | 21 commits del 7-8 abr 2026, con Cursor, ninguno con Claude | [verified-this-session] | `git log`: 21 commits; 5 con `Made-with: Cursor`; 0 `Co-Authored-By: Claude` |

## Hallazgos nuevos
- El README apunta a una URL de Railway que ya no está alojada.
- La "visita" no se registra en ningún lado: solo es un enlace de Calendly.
- El teléfono se guarda sin validar; `datetime.utcnow()` está deprecado.
- El filtro exige recámaras exactas (3 ≠ "al menos 3").

## Conclusión
Reconstruir el núcleo (tools, guards, pruebas) en vez de parchar: los defectos son de diseño
(acciones por texto, dos llamadas por turno, cero pruebas), no puntuales.
