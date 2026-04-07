# 🏡 InmoBot Demo - Agente IA Conversacional para Inmobiliarias

**Demo funcional** de agente conversacional basado en IA para inmobiliarias en Puebla, México.

## 📌 Descripción

Asistente virtual (Sofía) que automatiza:
- ✅ Calificación de leads (presupuesto, zona, tipo de compra, plazo)
- ✅ Filtrado inteligente de propiedades del catálogo
- ✅ Captura automática de datos de contacto
- ✅ Agendamiento de visitas
- ✅ Atención 24/7 sin intervención humana

**Arquitectura Python-first:** filtrado de propiedades en backend (no LLM) para eliminar alucinaciones.

---

## 🚀 Inicio Rápido

### 1️⃣ Prerrequisitos

- Python 3.11+
- OpenAI API key

### 2️⃣ Instalación Local

```bash
git clone https://github.com/astraDukoWave/inmobot-demo.git
cd inmobot-demo

# Crear .env
cp .env.example .env
# Editar .env y pegar tu OPENAI_API_KEY

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
uvicorn main:app --reload --port 8000
```

Abre **http://localhost:8000** en tu navegador.

---

## 📦 Estructura del Proyecto

```
inmobot-demo/
├── main.py                 # FastAPI backend
├── properties.json         # 10 propiedades reales de Puebla
├── requirements.txt
├── Dockerfile              # Railway-ready
├── .env.example
├── .gitignore
└── static/
    └── index.html          # Landing page + chat widget
```

---

## 🧠 Arquitectura Técnica

### Flujo de Conversación

1. **Usuario envía mensaje** → POST `/chat`
2. **Extracción de intent** (OpenAI `gpt-4o-mini`, `temperature=0`)
   - JSON estructurado: `{budget_min, budget_max, zone, bedrooms, purchase_type, timeline, name, phone}`
3. **Filtrado Python** (sin LLM):
   ```python
   matched = filter_properties(budget_max, zone, bedrooms, prop_type)
   ```
4. **LLM redacta respuesta** con propiedades inyectadas en system context
5. **Parse tags especiales:**
   - `[SHOW_PROPERTIES]` → envía array de propiedades al frontend
   - `[LEAD_CAPTURED: nombre | telefono]` → guarda en SQLite
   - `[SHOW_CALENDAR]` → muestra link Calendly

### Stack

| Componente | Tecnología |
|---|---|
| Backend | FastAPI 0.115 |
| LLM | OpenAI GPT-4o-mini |
| DB | SQLite (leads) |
| Frontend | Vanilla JS + CSS |
| Deploy | Railway.app (Dockerfile incluido) |

---

## 📁 Catálogo de Propiedades

`properties.json` incluye 10 propiedades realistas:

- **Zonas:** Angelópolis, Cholula, Centro, Lomas de Angelópolis
- **Precios:** $1.5M - $4.8M MXN
- **Tipos:** Departamentos, casas, lofts, penthouses
- **Detalles:** Recamaras, baños, m², amenidades, descripciones convincentes

---

## 🔑 Endpoints API

### `POST /chat`

**Request:**
```json
{
  "session_id": "session_123",
  "message": "Busco departamento en Angelópolis de 2M"
}
```

**Response:**
```json
{
  "reply": "Perfecto, tengo varias opciones...",
  "properties": [
    {
      "id": 3,
      "name": "Torre Atlixcáyotl 1202",
      "price_mxn": 2750000,
      "zone": "Angelópolis",
      "bedrooms": 2,
      "bathrooms": 2
    }
  ],
  "lead_saved": false
}
```

### `GET /leads`

Retorna todos los leads capturados (SQLite).

---

## 🌐 Deploy en Railway

1. **Fork este repo**
2. **Conecta Railway.app** con tu GitHub
3. **New Project → Deploy from GitHub repo**
4. **Agregar variable de entorno:**
   - `OPENAI_API_KEY` = tu key
5. **Railway detecta el Dockerfile automáticamente**
6. **Deploy completo en ~2 min**

Link público: `https://inmobot-demo-production.up.railway.app`

---

## 📊 Sistema de Calificación de Leads

### Flujo de 5 Pasos

1. **Presupuesto** → filtra por rango de precio
2. **Zona** → Angelópolis / Cholula / Centro / Lomas
3. **Recámaras** → 2, 3, 4+
4. **Tipo de compra** → Crédito / Contado (**fricción comercial**)
5. **Plazo** → Inmediato / 3 meses / Explorando (**urgencia**)

### Captura de Lead

Cuando el bot detecta `nombre + teléfono` en la conversación:

```python
if "[LEAD_CAPTURED:" in assistant_msg:
    save_lead(intent, session_id)  # → SQLite
```

**Schema de `leads.db`:**

```sql
CREATE TABLE leads (
    id INTEGER PRIMARY KEY,
    name TEXT,
    phone TEXT,
    zone TEXT,
    budget_max INTEGER,
    purchase_type TEXT,
    timeline TEXT,
    session_id TEXT,
    created_at TEXT
);
```

---

## ⚡ Optimizaciones Clave

### 1. Zero Alucinaciones

**Problema:** LLMs inventan propiedades inexistentes.

**Solución:**
```python
# Filtrado en Python ANTES de pasar al LLM
matched_props = filter_properties(budget_max, zone, bedrooms)

# LLM solo redacta con datos reales inyectados
messages = [
    {"role": "system", "content": SYSTEM_PROMPT + f"\n\nPropiedades disponibles:\n{json.dumps(matched_props)}"}
]
```

### 2. System Prompt con Control Estricto

```python
SYSTEM_PROMPT = """
REGLAS CRITICAS:
- NUNCA inventes propiedades. Solo usa las que el backend te proporcione.
- Si no hay coincidencias, pide ajustar criterios.
- Haz UNA sola pregunta por mensaje.
- Cuando captures nombre Y telefono, incluye [LEAD_CAPTURED: nombre | telefono]
"""
```

### 3. Extracción de Intent con `temperature=0`

```python
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=extraction_prompt,
    temperature=0,  # Determinístico
    max_tokens=200
)
```

---

## 👨‍💻 Uso en Cursor Pro

```bash
# Clonar desde GitHub
git clone https://github.com/astraDukoWave/inmobot-demo.git
cd inmobot-demo

# Abrir en Cursor
cursor .

# Crear .env
cp .env.example .env
# Pegar OPENAI_API_KEY en .env

# Ejecutar con terminal integrada
uvicorn main:app --reload
```

---

## 🎯 Roadmap / Mejoras Futuras

- [ ] Integración con WhatsApp Business API
- [ ] Conexión a CRM real (HubSpot, Salesforce)
- [ ] Multi-idioma (español/inglés)
- [ ] Análisis de sentimiento del lead
- [ ] Notificaciones push al agente inmobiliario
- [ ] Dashboard de métricas (tasa de conversión, leads calificados)

---

## 📄 Licencia

MIT License - Ver archivo `LICENSE` para más detalles.

---

## 👤 Autor

**astraDukoWave**
- GitHub: [@astraDukoWave](https://github.com/astraDukoWave)

---

⭐ **Si este demo te sirvió para ganar un cliente, considera darle una estrella al repo!**
