# 07 — Frontend

## Alcance

Frontend básico (HTML + JS vanilla + Plotly JS) servido por nginx y accedido **solo a través del gateway**. Nunca llama a API Colombia.

## Pantallas

1. **Login**: obtiene JWT desde `/auth/token`, lo guarda en memoria/`sessionStorage`.
2. **Mapa de aeropuertos**: `GET /api/v1/airports/map` → `Plotly.newPlot('map', [payload], payload.layout)` con `scattergeo` centrado en Colombia. Click en un punto muestra detalle (`GET /api/v1/airports/{id}`).
3. **Itinerarios**: tabla paginada (GET), formulario crear/editar (selects de aeropuerto alimentados por `/airports`), eliminar. Muestra errores RFC 7807 (`title` + `detail`).
4. **Ruta del itinerario** (extra): dibuja línea origen→destino en el mapa (`mode: 'lines+markers'`).
5. **Reporte** (si existe la Lambda): métricas en barras Plotly.

## Estructura

```
frontend/
├── index.html
├── js/{api.js, auth.js, map.js, itineraries.js}
├── css/styles.css
├── nginx.conf
└── Dockerfile
```

## Criterios de aceptación

- Se ve al menos un aeropuerto en el mapa con datos del Airport Service.
- Si Airport Service devuelve 503, el frontend muestra un aviso, no se rompe.
- Todas las llamadas llevan `Authorization` (excepto login) y `X-Request-ID`.
