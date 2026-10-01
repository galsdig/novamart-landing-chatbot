// Identificador de esta conversación (el backend lo usa para recordar qué cancelación espera confirmación)
const sessionId = crypto.randomUUID();
const historial = [];   // mensajes que se reenvían en cada petición: el LLM no tiene memoria propia

const $ = (id) => document.getElementById(id);
const clases = { "En preparación": "e-prep", "En tránsito": "e-transito", "Entregado": "e-entregado",
  "Pendiente de pago": "e-pago", "Cancelado": "e-cancelado" };

// ----- Sección de pedidos: pide la lista al backend -----
async function cargarPedidos() {
  const res = await fetch("/api/pedidos");
  const datos = await res.json();
  $("lista-pedidos").innerHTML = "";
  for (const p of datos) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="id"></span><span class="ubi"></span><span class="estado"></span>`;
    li.children[0].textContent = p.pedido;
    li.children[1].textContent = p.ubicacion;
    li.children[2].textContent = p.estado;
    li.children[2].classList.add(clases[p.estado] || "e-pago");
    $("lista-pedidos").appendChild(li);
  }
}

// ----- Widget -----
function abrir(si) {
  $("chat").hidden = !si;
  $("chat-btn").hidden = si;
  $("chat-btn").setAttribute("aria-expanded", si);
  if (si) $("chat-in").focus();
}

function pintar(texto, quien) {
  const d = document.createElement("div");
  d.className = "m " + quien;
  d.textContent = texto;   // textContent (no innerHTML) evita inyectar HTML
  $("msgs").appendChild(d);
  $("msgs").scrollTop = $("msgs").scrollHeight;
  return d;
}

async function enviar(texto) {
  pintar(texto, "yo");
  historial.push({ role: "user", content: texto });
  const espera = pintar("Escribiendo…", "bot");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, messages: historial }),
    });
    const { reply } = await res.json();
    espera.textContent = reply;
    historial.push({ role: "assistant", content: reply });
    cargarPedidos();   // por si se canceló un pedido, la lista se actualiza
  } catch (e) {
    espera.textContent = "No pude conectarme con el servidor.";
  }
}

$("chat-btn").onclick = () => abrir(true);
$("chat-x").onclick = () => abrir(false);
$("chat-form").onsubmit = (e) => {
  e.preventDefault();
  const t = $("chat-in").value.trim();
  if (!t) return;
  $("chat-in").value = "";
  enviar(t);
};

pintar("Hola, soy el asistente de NovaMart. Te ayudo con el estado, rastreo o cancelación de tus pedidos.", "bot");
for (const q of ["¿Cuál es el estado de ORD-1001?", "Quiero cancelar ORD-1004", "Quiero rastrear mi pedido"]) {
  const b = document.createElement("button");
  b.textContent = q;
  b.onclick = () => enviar(q);
  $("chips").appendChild(b);
}
cargarPedidos();
