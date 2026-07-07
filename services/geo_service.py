# ===========================================================
# Módulo: services/geo_service.py
# Función: Cálculos de geolocalización para validar que el
#          trabajador esté dentro del perímetro de la obra.
# Funciones:
#   - distancia_metros(lat1, lon1, lat2, lon2) -> metros (Haversine)
#   - dentro_de_obra(lat, lon, config) -> (bool, distancia)
# Dependencias: math, models.configuracion
# ===========================================================

import math


def distancia_metros(lat1, lon1, lat2, lon2):
    """Calcula la distancia en metros entre dos puntos geográficos
    usando la fórmula de Haversine (considera la curvatura terrestre).
    Recibe coordenadas en grados decimales."""
    R = 6371000  # radio de la Tierra en metros

    # Convertir grados a radianes
    f1 = math.radians(float(lat1))
    f2 = math.radians(float(lat2))
    df = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))

    a = (math.sin(df / 2) ** 2
         + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def dentro_de_obra(lat, lon, config):
    """Indica si las coordenadas dadas están dentro del radio
    permitido alrededor del centro de la obra.

    Devuelve una tupla (permitido: bool, distancia_m: float).
    Si la validación está desactivada, siempre permite (True, 0)."""
    # Si el admin desactivó la validación, no se exige ubicación.
    if config.get("validar_ubicacion", "1") != "1":
        return True, 0.0

    try:
        obra_lat = config.get("obra_latitud")
        obra_lon = config.get("obra_longitud")
        radio = float(config.get("obra_radio_m", 150))
        dist = distancia_metros(lat, lon, obra_lat, obra_lon)
        return (dist <= radio), round(dist, 1)
    except (TypeError, ValueError):
        # Si faltan datos o vienen mal, por seguridad NO se permite.
        return False, -1.0


def sitio_mas_cercano(lat, lon, sitios):
    """Recorre TODOS los sitios activos y devuelve el más cercano.

    Parámetros:
      - lat, lon: ubicación del trabajador
      - sitios: lista de dicts con nombre, latitud, longitud, radio_m

    Devuelve (permitido, nombre_sitio, distancia_m):
      - permitido: True si está dentro del radio de algún sitio
      - nombre_sitio: el sitio más cercano (esté dentro o no)
      - distancia_m: distancia al sitio más cercano
    Si no hay sitios o las coordenadas son inválidas, no permite.
    """
    if not sitios:
        return False, None, -1.0

    mejor_nombre = None
    mejor_dist = None
    permitido = False

    for s in sitios:
        try:
            d = distancia_metros(lat, lon, s["latitud"], s["longitud"])
            radio = float(s.get("radio_m", 300))
        except (TypeError, ValueError):
            continue
        # Guardar el sitio más cercano visto hasta ahora
        if mejor_dist is None or d < mejor_dist:
            mejor_dist = d
            mejor_nombre = s["nombre"]
        # Si está dentro del radio de este sitio, queda permitido
        if d <= radio:
            permitido = True
            mejor_nombre = s["nombre"]
            mejor_dist = d
            break  # ya encontró un sitio válido, no sigue buscando

    if mejor_dist is None:
        return False, None, -1.0
    return permitido, mejor_nombre, round(mejor_dist, 1)
