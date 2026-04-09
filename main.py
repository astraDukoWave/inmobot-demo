import json
import os
import re
import sqlite3
import unicodedata
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="InmoBot Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# GitHub Models API endpoint
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.getenv("GITHUB_TOKEN"),
)

# --- Load properties ---
with open("properties.json", "r", encoding="utf-8") as f:
    PROPERTIES = json.load(f)

# --- In-memory conversation store ---
CONVERSATIONS: dict[str, list] = {}

# --- SQLite setup ---
DB_PATH = "leads.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            zone TEXT,
            budget_max INTEGER,
            purchase_type TEXT,
            timeline TEXT,
            session_id TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Models ---
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str
    properties: list = []
    lead_saved: bool = False

def normalize_text(text: str) -> str:
    return (
        unicodedata.normalize("NFKD", text)
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .lower()
    )

# --- Filter properties in Python (no LLM hallucinations) ---
def filter_properties(budget_min: Optional[int], budget_max: Optional[int],
                      zone: Optional[str], bedrooms: Optional[int],
                      prop_type: Optional[str]) -> list:
    if budget_min is not None and budget_min < 100:
        budget_min = budget_min * 1_000_000
    if budget_max is not None and budget_max < 100:
        budget_max = budget_max * 1_000_000
    results = []
    for p in PROPERTIES:
        if budget_min and p["price_mxn"] < budget_min:
            continue
        if budget_max and p["price_mxn"] > budget_max:
            continue
        if zone and normalize_text(zone) != normalize_text(p["zone"]):
            continue
        if bedrooms and p["bedrooms"] != bedrooms:
            continue
        if prop_type and normalize_text(prop_type) not in normalize_text(p["type"]):
            continue
        results.append(p)
    return results[:3]  # max 3 results

# --- Extract intent from user message ---
def extract_intent(session_history: list) -> dict:
    extraction_prompt = [
        {"role": "system", "content": (
            "Analiza la conversacion y extrae los criterios de busqueda inmobiliaria. "
            "budget_max y budget_min DEBEN ser números completos (ej. 3000000). "
            "prop_type debe ser 'casa' o 'departamento' (usa null si dice algo general como 'propiedad'). "
            "Responde UNICAMENTE con JSON valido con estos campos (usa null si no se menciona): "
            '{"budget_min": int|null, "budget_max": int|null, "zone": str|null, '
            '"bedrooms": int|null, "prop_type": str|null, "name": str|null, '
            '"phone": str|null, "purchase_type": str|null, "timeline": str|null}'
        )}
    ] + session_history
    
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=extraction_prompt,
        temperature=0,
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        return {}

# --- Save lead to DB ---
def save_lead(intent: dict, session_id: str) -> bool:
    if not intent.get("name") or not intent.get("phone"):
        return False
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO leads (name, phone, zone, budget_max, purchase_type, timeline, session_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        intent.get("name"),
        intent.get("phone"),
        intent.get("zone"),
        intent.get("budget_max"),
        intent.get("purchase_type"),
        intent.get("timeline"),
        session_id,
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()
    return True

SYSTEM_PROMPT = """
Eres Sofia, asesora inmobiliaria virtual de InmoBot para Puebla, Mexico.
Tu objetivo es calificar leads y mostrar propiedades del catalogo.

FLUJO OBLIGATORIO (una pregunta a la vez):
1. Presupuesto: rango en pesos mexicanos
2. Zona preferida: Angelopolis, Cholula, Centro, Lomas de Angelopolis
3. Recamaras: cuantas necesita
4. Tipo de compra: credito hipotecario o recurso propio / contado
5. Plazo: inmediato, 3 meses, o solo explorando

Inmediatamente después de recibir el dato de Plazo, DEBES mostrar las propiedades usando la etiqueta [SHOW_PROPERTIES] antes de pedir el nombre y teléfono.
No pidas nombre ni teléfono hasta haber enviado ese mensaje con [SHOW_PROPERTIES] cuando el backend te haya proporcionado propiedades filtradas.

ETIQUETAS (cumplimiento estricto, texto exacto, sin variantes):
- [SHOW_PROPERTIES]: obligatoria en el mensaje donde presentas el catalogo filtrado; no la omitas ni la sustituyas por otra frase.
- [LEAD_CAPTURED: nombre | telefono]: solo cuando tengas nombre Y telefono; formato exacto con ese nombre y separador.
- [SHOW_CALENDAR]: incluyela exactamente asi cuando toque agendar.

REGLAS CRITICAS:
- NUNCA inventes propiedades. Solo usa las que el backend te proporcione.
- Si no hay coincidencias, pide ajustar criterios (sin inventar listados).
- Haz UNA sola pregunta por mensaje mientras recopilas datos; el mensaje posterior a Plazo resume/muestra resultados y lleva [SHOW_PROPERTIES], sin mezclar en ese mismo mensaje la peticion de nombre o telefono.
- Cuando captures nombre Y telefono, incluye [LEAD_CAPTURED: nombre | telefono] en tu respuesta.
- Cuando sea momento de agendar, incluye [SHOW_CALENDAR] en tu respuesta.
- Menciona que los horarios suelen ocuparse rapido esta semana para crear urgencia.
- Usa tono amigable, profesional y conversacional.
- Precios siempre con formato: $2,450,000 MXN
"""

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if req.session_id not in CONVERSATIONS:
        CONVERSATIONS[req.session_id] = []
    
    history = CONVERSATIONS[req.session_id]
    history.append({"role": "user", "content": req.message})
    
    # Extract intent from full conversation
    intent = extract_intent(history)
    
    # Filter properties in Python
    matched_props = []
    if intent.get("budget_max") or intent.get("zone") or intent.get("bedrooms"):
        matched_props = filter_properties(
            intent.get("budget_min"),
            intent.get("budget_max"),
            intent.get("zone"),
            intent.get("bedrooms"),
            intent.get("prop_type"),
        )
    
    # Build context message for LLM
    context_msg = ""
    if matched_props:
        context_msg = f"\n\n[BACKEND DATA - propiedades filtradas para mostrar]:\n{json.dumps(matched_props, ensure_ascii=False, indent=2)}"
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + context_msg}
    ] + history
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=600,
    )
    
    assistant_msg = response.choices[0].message.content
    if intent.get("timeline") and matched_props and "[SHOW_PROPERTIES]" not in assistant_msg:
        assistant_msg = assistant_msg.rstrip() + " [SHOW_PROPERTIES]"
    history.append({"role": "assistant", "content": assistant_msg})
    
    # Check for lead capture
    lead_saved = False
    if "[LEAD_CAPTURED:" in assistant_msg:
        lead_saved = save_lead(intent, req.session_id)
    
    # Clean tags from visible message
    clean_msg = re.sub(r"\[LEAD_CAPTURED:[^\]]*\]", "", assistant_msg)
    clean_msg = clean_msg.replace("[SHOW_PROPERTIES]", "").replace("[SHOW_CALENDAR]", "").strip()
    
    # Show calendar link if tag present
    if "[SHOW_CALENDAR]" in assistant_msg:
        clean_msg += "\n\n📅 Agenda tu visita aqui: https://calendly.com/inmobot-demo/visita"
    
    props_to_send = matched_props if "[SHOW_PROPERTIES]" in assistant_msg else []
    
    return ChatResponse(
        reply=clean_msg,
        properties=props_to_send,
        lead_saved=lead_saved,
    )

@app.get("/leads")
async def get_leads():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT * FROM leads ORDER BY created_at DESC")
    leads = [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
    conn.close()
    return leads

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
