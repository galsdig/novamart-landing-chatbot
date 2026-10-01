# NovaMart: landing page y chatbot con NVIDIA NIM

**Equipo 2:** Mario, José Miguel, Yassir y Diego
**Curso:** I Bootcamp Skala (IA) · Presentación: 30 de septiembre de 2026

## Objetivo

Construir una landing page funcional en localhost para la empresa ficticia NovaMart, con un widget de chatbot conectado a un LLM de NVIDIA mediante API/NIM. El chatbot atiende únicamente consultas de pedidos: estado, rastreo y cancelación.

## Tecnologías

- **Frontend:** HTML, CSS y JavaScript (sin frameworks).
- **Backend:** Python 3.12 + FastAPI + Uvicorn.
- **LLM:** `nvidia/nemotron-3-super-120b-a12b`, consumido con el cliente `openai` apuntando al endpoint de NVIDIA.
- **Configuración:** `python-dotenv` para leer la API Key desde `.env`.

## Explicación del flujo

![Diagrama de flujo](docs/diagrama-flujo.jpg)

1. El usuario abre la landing en `http://localhost:8000` y escribe en el widget.
2. El navegador envía el historial de la conversación a `POST /api/chat`.
3. El backend agrega el prompt de sistema y llama a NVIDIA NIM, indicándole qué funciones puede usar.
4. Si el LLM pide una función (`consultar_pedido`, `rastrear_envio`, `validar_cancelacion` o `cancelar_pedido`), el backend la ejecuta con los datos simulados y devuelve el resultado al LLM.
5. El LLM redacta la respuesta final y el backend la regresa al widget. Si hubo una cancelación, la lista de pedidos se actualiza.

## Qué parte es cada cosa

| Parte | Dónde está | Qué hace |
| --- | --- | --- |
| Landing page | `static/index.html`, `styles.css`, `script.js` | Muestra los pedidos y el widget del chat |
| Backend local | `app.py` | Guarda los datos simulados, ejecuta las funciones y aplica las reglas |
| NVIDIA API / NIM | `integrate.api.nvidia.com` | Servicio de inferencia que recibe el texto y ejecuta el modelo |
| LLM | Nemotron 3 Super 120B | Entiende lo que escribe el usuario y redacta la respuesta |

## Cómo limitamos el comportamiento del chatbot

- **Prompt de sistema** que restringe el tema a pedidos y define la frase exacta para temas fuera de alcance.
- **Funciones simuladas:** el LLM no inventa estados; consulta los datos del backend.
- **Seguro en código:** `cancelar_pedido` solo cancela si antes se validó la cancelación de ese pedido y el usuario confirmó. Esto no depende del LLM.
- **Errores controlados:** si falla la conexión con NVIDIA, el usuario ve un mensaje genérico y el detalle queda solo en la terminal.

## Cómo ejecutar en localhost

```bash
git clone https://github.com/galsdig/novamart-landing-chatbot.git
cd novamart-landing-chatbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # luego edita .env con tu API Key
uvicorn app:app --reload
```

Abre `http://localhost:8000`.

## Cómo configurar la API Key sin exponerla

1. Genera una clave en [build.nvidia.com](https://build.nvidia.com).
2. Copia `.env.example` a `.env` y reemplaza `tu_clave_aqui` por tu clave.
3. `.env` está en `.gitignore`, por lo que **nunca se sube a GitHub**. Solo se versiona `.env.example`, que no tiene credenciales reales.

## Pruebas realizadas

> **COMPLETAR:** pon el resultado real de cada prueba (✅ o ❌) y una frase de lo que respondió el chatbot.

| Prueba | Resultado | Observación |
| --- | --- | --- |
| ¿Cuál es el estado de ORD-1001? | | |
| ¿Dónde está mi pedido ORD-1002? | | |
| Quiero cancelar ORD-1004 | | |
| Sí, confirmo la cancelación | | |
| Cancela ORD-1002 | | |
| Quiero rastrear mi pedido (sin número) | | |
| Explícame una receta de pizza | | |
| Hazme un poema | | |
| ¿Cuánto es 25 por 18? | | |
| Dime información sobre política | | |
| Recomiéndame una película | | |

## Evidencia del funcionamiento

> **COMPLETAR:** agrega aquí las capturas (carpeta `docs/`) y enlázalas, por ejemplo: `![Estado de pedido](docs/captura-estado.png)`

## Conclusión del equipo

> **COMPLETAR:** escribe con tus palabras qué aprendieron sobre cómo se conecta una app local con un LLM mediante NVIDIA NIM, y qué dificultades encontraron.
