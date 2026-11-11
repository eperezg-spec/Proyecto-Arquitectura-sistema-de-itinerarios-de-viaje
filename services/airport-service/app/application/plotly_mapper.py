"""
Transforma aeropuertos del dominio al formato que entiende Plotly JS.

El frontend recibe directamente {"data": [...], "layout": {...}} y solo tiene que
llamar a Plotly.newPlot(div, data, layout). Así el frontend no conoce la API externa.
"""
from typing import Any

from app.domain.models import Airport

# Rango aproximado de Colombia para encuadrar el mapa.
COLOMBIA_LAT_RANGE = [-5, 14]
COLOMBIA_LON_RANGE = [-82, -66]


def to_plotly_map(airports: list[Airport]) -> dict[str, Any]:
    # Solo podemos dibujar aeropuertos que tengan coordenadas.
    located = [a for a in airports if a.latitude is not None and a.longitude is not None]

    trace = {
        "type": "scattergeo",
        "mode": "markers",
        "lat": [a.latitude for a in located],
        "lon": [a.longitude for a in located],
        "text": [f"{a.name} ({a.iata_code}) - {a.city}, {a.department}" for a in located],
        "customdata": [a.id for a in located],  # el frontend usa el id al hacer clic
        "hovertemplate": "%{text}<extra></extra>",
        "marker": {"size": 9, "color": "#d62728"},
        "name": "Aeropuertos",
    }
    layout = {
        "title": {"text": "Aeropuertos de Colombia"},
        "geo": {
            "scope": "south america",
            "resolution": 50,
            "lataxis": {"range": COLOMBIA_LAT_RANGE},
            "lonaxis": {"range": COLOMBIA_LON_RANGE},
            "showcountries": True,
            "showland": True,
            "landcolor": "#f2efe9",
            "countrycolor": "#999999",
        },
        "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
    }
    return {"data": [trace], "layout": layout}
