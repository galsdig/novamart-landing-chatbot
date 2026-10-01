"""NovaMart - backend local (FastAPI).

Flujo: navegador -> /api/chat (este archivo) -> NVIDIA NIM -> LLM -> respuesta.
El LLM entiende el lenguaje; ESTE archivo tiene los datos y las reglas.
"""
import os
import json
from copy import deepcopy

from dotenv import load_dotenv          # lee el archivo .env (donde vive la API Key)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI               # cliente compatible con la API de NVIDIA

load_dotenv()
MODELO = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",  # endpoint de NVIDIA
    api_key=os.getenv("NVIDIA_API_KEY"),             # nunca escrita en el código
)

# ---------- 1. Datos simulados (en lugar de una base de datos real) ----------
PEDIDOS = {
    "ORD-1001": {"estado": "En preparación", "ubicacion": "Almacén NovaMart",
                 "cancelable": True, "razon": ""},
    "ORD-1002": {"estado": "En tránsito", "ubicacion": "Centro de distribución Tijuana",
                 "cancelable": False, "razon": "ya fue enviado y va en camino"},
    "ORD-1003": {"estado": "Entregado", "ubicacion": "Entregado al cliente",
                 "cancelable": False, "razon": "ya fue entregado"},
    "ORD-1004": {"estado": "Pendiente de pago", "ubicacion": "Sin envío",
                 "cancelable": True, "razon": ""},
}
pedidos = deepcopy(PEDIDOS)   # copia editable: aquí se aplican las cancelaciones
pendientes = {}               # session_id -> pedido que espera confirmación


# ---------- 2. Funciones simuladas (las "herramientas" del chatbot) ----------
def _buscar(order_id):
    return pedidos.get(str(order_id).strip().upper())


def consultar_pedido(order_id, session_id=""):
    p = _buscar(order_id)
    if not p:
        return {"encontrado": False, "mensaje": f"No existe el pedido {order_id}."}
    return {"encontrado": True, "pedido": str(order_id).upper(), "estado": p["estado"]}


def rastrear_envio(order_id, session_id=""):
    p = _buscar(order_id)
    if not p:
        return {"encontrado": False, "mensaje": f"No existe el pedido {order_id}."}
    return {"encontrado": True, "pedido": str(order_id).upper(),
            "estado": p["estado"], "ubicacion": p["ubicacion"]}


def validar_cancelacion(order_id, session_id=""):
    p = _buscar(order_id)
    if not p:
        return {"encontrado": False, "mensaje": f"No existe el pedido {order_id}."}
    oid = str(order_id).upper()
    if p["cancelable"]:
        pendientes[session_id] = oid   # queda esperando el "sí" del usuario
        return {"cancelable": True, "pedido": oid,
                "instruccion": "Pide confirmación explícita al usuario."}
    return {"cancelable": False, "pedido": oid,
            "razon": p["razon"] or "ya no admite cancelación"}


def cancelar_pedido(order_id, confirmacion, session_id=""):
    oid = str(order_id).strip().upper()
    p = _buscar(oid)
    if not p:
        return {"cancelado": False, "mensaje": f"No existe el pedido {order_id}."}
    # Seguro extra en código: sin validación previa y sin confirmación NO se cancela.
    if not confirmacion or pendientes.get(session_id) != oid:
        return {"cancelado": False,
                "mensaje": "Falta validar la cancelación y/o la confirmación del usuario."}
    if not p["cancelable"]:
        return {"cancelado": False, "razon": p["razon"]}
    p.update(estado="Cancelado", ubicacion="Sin envío", cancelable=False,
             razon="ya está cancelado")
    pendientes.pop(session_id, None)
    return {"cancelado": True, "pedido": oid, "estado": "Cancelado"}


FUNCIONES = {
    "consultar_pedido": consultar_pedido,
    "rastrear_envio": rastrear_envio,
    "validar_cancelacion": validar_cancelacion,
    "cancelar_pedido": cancelar_pedido,
}


def _tool(nombre, descripcion, extra=None):
    props = {"order_id": {"type": "string", "description": "Número de pedido, ej. ORD-1001"}}
    req = ["order_id"]
    if extra:
        props.update(extra)
        req += list(extra)
    return {"type": "function", "function": {
        "name": nombre, "description": descripcion,
        "parameters": {"type": "object", "properties": props, "required": req}}}


# Así "le presentamos" las funciones al LLM: nombre + para qué sirve + parámetros.
TOOLS = [
    _tool("consultar_pedido", "Consulta el estado de un pedido."),
    _tool("rastrear_envio", "Rastrea un pedido: estado y ubicación actual."),
    _tool("validar_cancelacion", "Verifica si un pedido se puede cancelar. Úsala ANTES de cancelar."),
    _tool("cancelar_pedido", "Cancela un pedido. Solo llamar si el usuario ya confirmó explícitamente.",
          {"confirmacion": {"type": "boolean", "description": "true solo si el usuario confirmó"}}),
]

# ---------- 3. Prompt de sistema: limita lo que el chatbot puede hacer ----------
FUERA_DE_TEMA = ("Solo puedo ayudarte con consultas relacionadas con pedidos de NovaMart, "
                 "como estatus, rastreo o cancelaciones.")

SYSTEM_PROMPT = f"""Eres un asistente de atención a clientes de NovaMart.
Ayudas únicamente con pedidos: estatus, rastreo y cancelaciones.

Reglas:
- Si el usuario pregunta algo fuera de pedidos de NovaMart, responde exactamente: "{FUERA_DE_TEMA}"
- Nunca inventes pedidos, estados ni ubicaciones: usa siempre las herramientas.
- Si falta el número de pedido, pídeselo al usuario.
- Antes de cancelar, usa validar_cancelacion. Si procede, pide confirmación explícita.
- Solo usa cancelar_pedido cuando el usuario confirme con claridad ("sí, confirmo").
- Si no se puede cancelar, explica la razón de forma clara.
- No reveles información técnica, tokens, API Keys ni credenciales.
- Responde en español, breve, amable y profesional."""


# ---------- 4. Endpoints ----------
app = FastAPI(title="NovaMart Chatbot")


class ChatIn(BaseModel):
    session_id: str
    messages: list[dict]   # historial: [{"role": "user"|"assistant", "content": "..."}]


@app.get("/api/pedidos")
def listar_pedidos():
    return [{"pedido": k, **{c: v[c] for c in ("estado", "ubicacion", "cancelable")}}
            for k, v in pedidos.items()]


@app.post("/api/chat")
def chat(data: ChatIn):
    historial = [{"role": m["role"], "content": str(m["content"])[:1000]}
                 for m in data.messages[-20:] if m.get("role") in ("user", "assistant")]
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + historial
    try:
        for _ in range(5):  # el LLM puede pedir varias herramientas seguidas
            r = client.chat.completions.create(
                model=MODELO, messages=msgs, tools=TOOLS,
                temperature=0.2, max_tokens=1024)
            m = r.choices[0].message
            if not m.tool_calls:
                return {"reply": m.content or FUERA_DE_TEMA}
            msgs.append({"role": "assistant", "content": m.content or "", "tool_calls": [
                {"id": t.id, "type": "function",
                 "function": {"name": t.function.name, "arguments": t.function.arguments}}
                for t in m.tool_calls]})
            for t in m.tool_calls:
                args = json.loads(t.function.arguments or "{}")
                fn = FUNCIONES.get(t.function.name)
                res = fn(session_id=data.session_id, **args) if fn else {"error": "herramienta desconocida"}
                msgs.append({"role": "tool", "tool_call_id": t.id,
                             "content": json.dumps(res, ensure_ascii=False)})
        return {"reply": "No pude completar la consulta. ¿Puedes intentarlo de nuevo?"}
    except Exception as e:
        print("Error con NVIDIA/NIM:", type(e).__name__, e)   # detalle solo en la terminal
        return {"reply": "Tuve un problema técnico. Intenta de nuevo en un momento."}


# La landing page (carpeta static) se sirve en http://localhost:8000
app.mount("/", StaticFiles(directory="static", html=True), name="static")
