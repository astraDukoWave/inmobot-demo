# Plan del video — InmoBot · Sofía (formato /brag)

- **Qué es:** un agente de chat que califica prospectos inmobiliarios, muestra solo propiedades del catálogo, registra visitas y pasa el lead a una persona por WhatsApp.
- **Para quién:** inmobiliarias que pierden leads fuera de horario.
- **Qué lo distingue:**
  - Las tarjetas salen de la herramienta, no del texto del modelo.
  - Hay un límite duro de ~20 s por turno.
  - Se probó contra el modelo real: 3 de 6 corridas fallaron y las 3 se corrigieron.
- **Gancho:** "11:47 p. m. — ¿Quién le contesta a esta hora?"
- **Tono:** polished, sobrio y técnico. Paleta de la app: azul #2C5F8A / #1e4464, violeta #667eea → #764ba2, verde #1f8f4e. Tipografía Inter.
- **Formato:** 1920×1080, 30 fps, 51 s.

## Storyboard
| # | Escena | Duración |
|---|---|---|
| 1 | Gancho: 11:47 p. m., un mensaje entra, "¿Quién le contesta a esta hora?" | 4.0 s |
| 2 | Presentación: "Sofía · InmoBot", agente inmobiliario con tool use, demo con catálogo ficticio | 3.5 s |
| 3 | Producto en uso: teléfono con la interfaz real. Búsqueda → 2 tarjetas → crédito → contacto → visita → WhatsApp. A la derecha, 4 subtítulos | 17.0 s |
| 4 | Cómo funciona un turno: Mensaje → Guards → Capa 1 → Agente (≤20 s) ⇄ Gemini → Tools → Tarjetas, más 3 garantías | 9.0 s |
| 5 | Prueba: 88 pruebas · 6 corridas (✓✗✗✗✓✓) · ≈0.3 MXN por conversación · 3.0–5.7 s por turno | 9.0 s |
| 6 | Cómo se construyó: Spec → Plan → PR → CI → Prueba real → Verify → Revisión CTO → Deploy; Claude Code, con una persona que aprueba cada merge | 4.5 s |
| 7 | Cierre: repo y autor | 4.0 s |

## Honestidad
- Los mensajes del prospecto y las respuestas de Sofía son **reales**: son los del escenario `lead_visita_whatsapp` de la corrida 6 (`7be5400`, Gemini). Las respuestas largas van abreviadas con "…".
- La interfaz es una recreación con los estilos reales de `static/styles.css`. Las imágenes de las tarjetas reproducen los placeholders de placehold.co del catálogo ficticio.
- Datos de prueba: "Ana Prueba, 222 123 4567". No aparece ningún número real.
- Todas las cifras salen de CI y de la bitácora de live-smoke.
