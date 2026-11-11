// Frontend básico: TODAS las llamadas van al API Gateway (misma URL que sirve esta página).
// El frontend solo conoce el formato "adaptado" del Airport Service, nunca API Colombia.

const state = {
  token: sessionStorage.getItem("token"),
  airports: [], // lista para los <select> y para dibujar rutas
};

// ---------- Utilidades ----------------------------------------------------
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`; // JWT que el gateway propaga
  const response = await fetch(path, { ...options, headers });

  if (response.status === 401 && state.token) {
    logout();
    throw new Error("La sesión expiró, vuelve a iniciar sesión");
  }
  if (!response.ok) {
    // Los servicios responden errores con formato {status, title, detail}
    const error = await response.json().catch(() => ({}));
    throw new Error(`${error.title || response.status}: ${error.detail || response.statusText}`);
  }
  return response.status === 204 ? null : response.json();
}

function showMessage(text, type = "ok") {
  const box = document.getElementById("message");
  box.textContent = text;
  box.className = `message ${type}`;
  box.hidden = false;
  setTimeout(() => (box.hidden = true), 5000);
}

const airportName = (id) => {
  const airport = state.airports.find((a) => a.id === id);
  return airport ? `${airport.name} (${airport.iata_code})` : `#${id}`;
};

// ---------- Login ---------------------------------------------------------
document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    const data = await api("/auth/token", {
      method: "POST",
      body: JSON.stringify({ username: form.get("username"), password: form.get("password") }),
    });
    state.token = data.access_token;
    sessionStorage.setItem("token", state.token);
    start();
  } catch (error) {
    alert(error.message);
  }
});

function logout() {
  state.token = null;
  sessionStorage.removeItem("token");
  document.getElementById("app").hidden = true;
  document.getElementById("login-section").hidden = false;
  document.getElementById("session").textContent = "";
}

// ---------- Mapa (Plotly) -------------------------------------------------
async function loadMap() {
  try {
    // El Airport Service ya devuelve {data, layout} listo para Plotly
    const figure = await api("/api/v1/airports/map");
    await Plotly.newPlot("map", figure.data, figure.layout, { responsive: true });
    document.getElementById("map").on("plotly_click", async (event) => {
      const id = event.points[0].customdata;
      const airport = await api(`/api/v1/airports/${id}`);
      document.getElementById("airport-detail").textContent =
        `${airport.name} · IATA ${airport.iata_code} · OACI ${airport.oaci_code} · ${airport.city}, ${airport.department} · ${airport.airport_type}`;
    });
  } catch (error) {
    showMessage(`No se pudo cargar el mapa. ${error.message}`, "error");
  }
}

// Dibuja la ruta salida -> llegada de un itinerario sobre el mapa
function showRoute(itinerary) {
  const from = state.airports.find((a) => a.id === itinerary.departure_airport_id);
  const to = state.airports.find((a) => a.id === itinerary.arrival_airport_id);
  if (!from || !to) return;
  const mapDiv = document.getElementById("map");
  if (mapDiv.data.length > 1) Plotly.deleteTraces("map", 1); // quita la ruta anterior
  Plotly.addTraces("map", {
    type: "scattergeo",
    mode: "lines+markers",
    lat: [from.latitude, to.latitude],
    lon: [from.longitude, to.longitude],
    line: { width: 3, color: "#1e3a5f" },
    marker: { size: 12, color: "#1e3a5f" },
    name: `${from.iata_code} → ${to.iata_code}`,
    hoverinfo: "name",
  });
  mapDiv.scrollIntoView({ behavior: "smooth" });
}

// ---------- Aeropuertos para los <select> ---------------------------------
async function loadAirports() {
  try {
    state.airports = await api("/api/v1/airports");
  } catch (error) {
    showMessage(`No se pudieron cargar los aeropuertos. ${error.message}`, "error");
    return;
  }
  const options = state.airports
    .map((a) => `<option value="${a.id}">${a.name} (${a.iata_code}) - ${a.city}</option>`)
    .join("");
  document.querySelectorAll("#itinerary-form select").forEach((select) => (select.innerHTML = options));
}

// ---------- CRUD de itinerarios -------------------------------------------
async function loadItineraries() {
  const itineraries = await api("/api/v1/itineraries?limit=100");
  const rows = document.getElementById("itinerary-rows");
  rows.innerHTML = "";
  for (const it of itineraries) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(it.user_name)}</td>
      <td>${escapeHtml(airportName(it.departure_airport_id))}</td>
      <td>${escapeHtml(airportName(it.arrival_airport_id))}</td>
      <td>${it.travel_date}</td>
      <td>${it.duration_minutes} min</td>
      <td></td>`;
    const actions = tr.lastElementChild;
    actions.append(
      button("Ruta", "secondary", () => showRoute(it)),
      button("Editar", "", () => fillForm(it)),
      button("Eliminar", "danger", () => removeItinerary(it.id)),
    );
    rows.append(tr);
  }
}

function button(text, className, onClick) {
  const b = document.createElement("button");
  b.textContent = text;
  b.className = className;
  b.addEventListener("click", onClick);
  return b;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function fillForm(it) {
  const form = document.getElementById("itinerary-form");
  for (const field of ["id", "user_name", "departure_airport_id", "arrival_airport_id", "travel_date", "duration_minutes"]) {
    form.elements[field].value = it[field];
  }
  document.getElementById("form-title").textContent = "Editar itinerario";
  document.getElementById("cancel-edit").hidden = false;
  form.scrollIntoView({ behavior: "smooth" });
}

function resetForm() {
  const form = document.getElementById("itinerary-form");
  form.reset();
  form.elements.id.value = "";
  document.getElementById("form-title").textContent = "Nuevo itinerario";
  document.getElementById("cancel-edit").hidden = true;
}

document.getElementById("cancel-edit").addEventListener("click", resetForm);

document.getElementById("itinerary-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const body = {
    user_name: form.elements.user_name.value,
    departure_airport_id: Number(form.elements.departure_airport_id.value),
    arrival_airport_id: Number(form.elements.arrival_airport_id.value),
    travel_date: form.elements.travel_date.value,
    duration_minutes: Number(form.elements.duration_minutes.value),
  };
  const id = form.elements.id.value;
  try {
    if (id) {
      await api(`/api/v1/itineraries/${id}`, { method: "PUT", body: JSON.stringify(body) });
      showMessage("Itinerario actualizado");
    } else {
      await api("/api/v1/itineraries", { method: "POST", body: JSON.stringify(body) });
      showMessage("Itinerario creado. La notificación se procesa de forma asíncrona (RabbitMQ → Lambda).");
    }
    resetForm();
    await loadItineraries();
  } catch (error) {
    showMessage(error.message, "error");
  }
});

async function removeItinerary(id) {
  if (!confirm("¿Eliminar este itinerario?")) return;
  try {
    await api(`/api/v1/itineraries/${id}`, { method: "DELETE" });
    showMessage("Itinerario eliminado");
    await loadItineraries();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

// ---------- Arranque ------------------------------------------------------
async function start() {
  document.getElementById("login-section").hidden = true;
  document.getElementById("app").hidden = false;
  const session = document.getElementById("session");
  session.innerHTML = "";
  session.append(button("Cerrar sesión", "secondary", logout));
  await loadAirports(); // primero, para mostrar nombres en la tabla
  await Promise.all([loadMap(), loadItineraries().catch((e) => showMessage(e.message, "error"))]);
}

if (state.token) start();
