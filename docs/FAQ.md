# Preguntas técnicas probables (respuestas cortas y verificables)

## 1. ¿Por qué tools y no etiquetas en el texto?
La versión de abril pedía al modelo escribir etiquetas como `[SHOW_PROPERTIES]` y luego las buscaba con texto. Eso es frágil por tres razones:
- El modelo puede olvidar la etiqueta, deformarla o inventarla.
- Hacían falta dos llamadas por turno.
- No había un contrato que se pudiera probar.

Con tool use, el modelo pide una función con argumentos validados por un JSON Schema, el código la ejecuta y le devuelve el resultado. El contrato se prueba sin red. Ver `app/tools.py` y `tests/test_tools.py`.

## 2. ¿Cómo evitas que invente?
- **Grounding:** las tarjetas salen **solo** de los resultados de `search_properties` y `get_property`. La búsqueda la hace el código sobre el catálogo; no la hace el modelo.
  - Prueba: `test_cards_come_only_from_tool_results`, donde una propiedad inventada en el texto no produce tarjeta.
  - `live-smoke` también verifica que la respuesta no mencione propiedades que no vinieron de las tools.
- **Reglas del prompt:**
  - No afirmar créditos aceptados, porque el catálogo no tiene ese dato.
  - Confirmar los montos ambiguos.
- **Límite honesto:** el texto libre del modelo todavía puede equivocarse. Lo medimos con revisión humana de las respuestas, no con una métrica automática.

## 3. ¿Cuánto cuesta una conversación?
Una conversación medida de 5 turnos con `gemini-3.8-flash` (live-smoke 6) usó ~18,450 tokens de entrada y ~450 de salida. Eso es ≈ **$0.016 USD ≈ 0.3 MXN**.
- **Precios:** $0.75 por millón de tokens de entrada y $3.75 por millón de salida, vigentes hasta el 31-dic-2026.
- El costo crece con la longitud del historial, que está acotado a 12 turnos.
- `/api/admin/usage` da los tokens reales del proceso.
- Las 6 corridas de prueba costaron ≈ 2.08 MXN en total.

## 4. ¿Cómo escalaría?
Hoy es un solo proceso, porque la escala supuesta es de 50 conversaciones al día. Cada siguiente paso tiene un disparador escrito (`docs/BACKLOG.md`):
| Cuando pase esto | Se agrega |
|---|---|
| Más de un dyno | Sesiones y rate limit en Redis (LB-02) |
| Leads de un cliente real | Postgres (LB-01) |
| p95 > 8 s | Streaming (LB-06) |
| Fallas repetidas del proveedor | Circuit breaker (LB-10) |
| Un segundo cliente | Multi-tenant (LB-08) |

El núcleo `Agent.run_turn` no cambia.

## 5. ¿Cuál es la ruta a WhatsApp y a voz?
- **Hoy:** el handoff a una persona usa un enlace `wa.me` con el resumen del lead.
- **Siguiente:** un webhook de la WhatsApp Cloud API que llame al mismo `Agent.run_turn` (LB-03).
- **Voz:** reconocimiento y síntesis de voz alrededor del mismo agente (LB-04).

El canal es una capa de entrada y salida; la lógica, las tools y los guards no cambian.

## 6. ¿Cómo proteges los datos?
- **Admin:** solo con token, comparado en tiempo constante. Sin token configurado, responde 503.
- **CORS:** cerrado por defecto.
- **Sesión:** UUID del servidor; no se puede adivinar.
- **Logs:** sin texto ni teléfonos, y hay prueba de ello (`test_logs_carry_no_user_text_name_or_phone`).
- **Interfaz:** se pinta con `textContent` y una CSP estricta, para evitar XSS.
- **Secretos:** solo en las config vars de Heroku, nunca en el repo.
- **Límite honesto:**
  - SQLite es efímero y solo sirve para datos de prueba.
  - El proveedor del modelo recibe lo que el prospecto escribe, por eso la demo pide datos de prueba.
  - El enmascarado de teléfonos está diseñado para el servidor MCP, que no se construyó en este ciclo.

## 7. ¿Cómo te defiendes de prompt injection?
En 3 capas:
1. **Filtro determinista** antes del modelo para los intentos obvios: sin costo e instantáneo.
2. **Reglas del prompt con tools de mínimo privilegio:** aunque engañen al modelo, las tools solo leen el catálogo y escriben el lead de esa misma conversación.
3. **Canary en la salida:** si el texto del prompt aparece en una respuesta, se reemplaza.

**Límite honesto:** la prueba contra el modelo real valida la capa 1. La resistencia del modelo a injection *indirecta* está en el backlog (LB-12).

## 8. ¿Qué pasa si el modelo falla o se cuelga?
- El turno completo tiene un **límite duro de ~20 s**. El router de Heroku corta a los 30.
  - La llamada al modelo corre en un hilo y el turno la espera con un tope de reloj.
  - El primer intento tiene un tope de 9 s y hay un reintento con lo que quede.
- **Respuestas tardías:** una respuesta que llega sin tiempo para cerrar el turno se descarta **antes** de ejecutar cualquier tool. Así no se guarda un lead ni se registra una visita a destiempo.
- **Lo que ve el usuario:** un mensaje amable y el botón de WhatsApp.
- **Evidencia:** esto se diseñó a partir de fallas reales en las corridas 2–4 de `live-smoke` (ver la bitácora), y lo cubren pruebas de reloj real en `tests/test_deadline.py`.

## 9. ¿Por qué Gemini si el puesto es de Claude?
- **Razón práctica:** no tenía créditos de la API de Anthropic y sí de Google.
- **Diseño:** el núcleo no depende del proveedor (`app/llm/`). Cambiar de modelo es una variable de entorno: `LLM_PROVIDER=anthropic`.
- **Estado del adaptador de Claude:** está implementado y probado contra los tipos del SDK de Anthropic, pero **está pendiente de validación contra la API real**, y así está declarado.

## 10. ¿Cómo lo probaste y qué falta probar?
- **Probado:**
  - 88 pruebas con LLM falso en CI.
  - `live-smoke` contra Gemini real con 3 escenarios críticos, y ninguno se aprueba por mayoría.
  - Revisión independiente del PR principal.
  - Verify Report contra el spec.
- **Falta:**
  - Una suite de evals más amplia: temas ajenos, montos ambiguos e injection indirecta.
  - Medir la latencia p95 con más muestras.
  - Validar el adaptador de Claude.
  - El servidor MCP.
