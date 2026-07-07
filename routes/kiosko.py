# ===========================================================
# Módulo: routes/kiosko.py
# Función: Pantalla PÚBLICA de marcación para trabajadores
#          (sin contraseña). El trabajador escribe su documento,
#          el sistema exige FOTO y UBICACIÓN, valida que esté
#          dentro de la obra y registra entrada o salida.
# Rutas:
#   GET  /            ... pantalla del kiosko (index)
#   POST /marcar-kiosko (JSON) ... procesa el marcaje
# Flujo del marcaje:
#   1) Buscar trabajador por documento.
#   2) Validar foto (obligatoria) y ubicación (obligatoria).
#   3) Verificar que esté dentro del radio de la obra.
#   4) Si tiene jornada abierta -> salida; si no -> entrada.
# Dependencias: flask, base64, datetime, models, services
# ===========================================================

import os
import base64
import binascii
import time
from datetime import datetime, date

from flask import Blueprint, render_template, request, jsonify

from models import trabajador as m_trab
from models import asistencia as m_asis
from models import configuracion as m_config
from models import sitio as m_sitio
from services import geo_service
from utils.registro import auditar
from config import Config

kiosko_bp = Blueprint("kiosko", __name__)

# -----------------------------------------------------------
# Límite simple de peticiones por IP para el kiosko público.
# Evita spam de marcajes y que alguien "adivine" qué documentos
# existen probando muchos en poco tiempo.
# -----------------------------------------------------------
_MAX_POR_MINUTO = 20
_peticiones = {}   # { ip: [timestamps...] }


def _throttle_ok():
    """True si la IP no ha superado el límite de peticiones por minuto."""
    adelante = request.headers.get("X-Forwarded-For", "")
    ip = adelante.split(",")[0].strip() if adelante else (request.remote_addr or "?")
    ahora = time.time()
    marcas = [t for t in _peticiones.get(ip, []) if ahora - t < 60]
    if len(marcas) >= _MAX_POR_MINUTO:
        _peticiones[ip] = marcas
        return False
    marcas.append(ahora)
    _peticiones[ip] = marcas
    return True


def _guardar_foto_base64(data_url, documento, tipo):
    """Convierte una imagen en formato data URL (base64) que envía la
    cámara del navegador y la guarda como archivo .jpg.
    Devuelve el nombre del archivo o None si los datos no son válidos.
    - documento: para nombrar el archivo
    - tipo: 'entrada' o 'salida'
    """
    if not data_url or "," not in data_url:
        return None
    try:
        # El data URL llega como: "data:image/jpeg;base64,...."
        cabecera, codificado = data_url.split(",", 1)
        binario = base64.b64decode(codificado)
    except (ValueError, binascii.Error):
        return None

    os.makedirs(Config.FOTOS_FOLDER, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitizar el documento: solo se permiten letras y números en el
    # nombre del archivo, para evitar rutas maliciosas (path traversal).
    doc_seguro = "".join(c for c in str(documento) if c.isalnum()) or "sindoc"
    nombre = f"{doc_seguro}_{tipo}_{sello}.jpg"
    with open(os.path.join(Config.FOTOS_FOLDER, nombre), "wb") as f:
        f.write(binario)
    return nombre


@kiosko_bp.route("/")
def index():
    """Pantalla pública de marcación (el kiosko que ven los trabajadores)."""
    config = m_config.obtener_todo()
    # Solo se pasan a la vista los datos que el navegador necesita.
    datos_kiosko = {
        "exigir_foto": config.get("exigir_foto", "1") == "1",
        "validar_ubicacion": config.get("validar_ubicacion", "1") == "1",
    }
    return render_template("index.html", kiosko=datos_kiosko)


@kiosko_bp.route("/marcar-kiosko", methods=["POST"])
def marcar_kiosko():
    """Procesa el marcaje enviado por el kiosko (formato JSON).
    Responde JSON con {ok, mensaje} para que la página muestre el
    resultado sin recargar."""
    datos = request.get_json(silent=True) or {}
    documento = (datos.get("documento") or "").strip()
    foto_data = datos.get("foto")          # data URL base64 o None
    lat = datos.get("lat")
    lon = datos.get("lon")

    # Límite de peticiones por IP (anti-spam y anti-enumeración)
    if not _throttle_ok():
        return jsonify(ok=False,
                       mensaje="Demasiados intentos. Espere un momento."), 429

    # 1) Validar documento y existencia del trabajador
    if not documento:
        return jsonify(ok=False, mensaje="Escriba su número de documento."), 400

    trabajador = m_trab.buscar_por_documento(documento)
    if not trabajador or not trabajador["activo"]:
        return jsonify(ok=False, mensaje="Documento no registrado o inactivo."), 404

    config = m_config.obtener_todo()

    # 2) Validar foto si es obligatoria
    if config.get("exigir_foto", "1") == "1" and (not foto_data or "," not in foto_data):
        return jsonify(ok=False, mensaje="Debe tomarse la foto para marcar."), 400

    # 3) Validar ubicación contra los sitios (estaciones + patio taller)
    sitio_marcado = None
    if config.get("validar_ubicacion", "1") == "1":
        if lat is None or lon is None:
            return jsonify(
                ok=False,
                mensaje="Active la ubicación del dispositivo para marcar."
            ), 400
        sitios = m_sitio.listar(solo_activos=True)
        permitido, sitio_marcado, distancia = geo_service.sitio_mas_cercano(
            lat, lon, sitios
        )
        if not permitido:
            if distancia is None or distancia < 0:
                msg = "No se pudo validar la ubicación. Intente de nuevo."
            else:
                msg = (f"Está fuera de los sitios de obra. El más cercano es "
                       f"{sitio_marcado} a {int(distancia)} m.")
            auditar("Marcaje rechazado (ubicación)",
                    f"Doc {documento}: {sitio_marcado} a {distancia} m")
            return jsonify(ok=False, mensaje=msg), 403
    else:
        # Si no se valida ubicación, igual intentamos nombrar el sitio cercano
        if lat is not None and lon is not None:
            sitios = m_sitio.listar(solo_activos=True)
            _, sitio_marcado, _ = geo_service.sitio_mas_cercano(lat, lon, sitios)

    # 4) Decidir entrada o salida y registrar
    hoy = date.today().isoformat()
    ahora = datetime.now().strftime("%H:%M")
    abierta = m_asis.abierta_de_hoy(trabajador["id"], hoy)

    # Convertir coordenadas a texto SOLO si existen. Antes se guardaba
    # str(None) = "None" y los reportes mostraban enlaces de mapa rotos.
    lat_txt = str(lat) if lat is not None else None
    lon_txt = str(lon) if lon is not None else None

    if abierta:
        foto = _guardar_foto_base64(foto_data, documento, "salida")
        m_asis.registrar_salida(abierta["id"], ahora, foto, lat_txt, lon_txt, sitio_marcado)
        auditar("Marcaje salida (kiosko)", f"Doc {documento} {ahora} en {sitio_marcado}")
        accion = "Salida"
    else:
        foto = _guardar_foto_base64(foto_data, documento, "entrada")
        m_asis.registrar_entrada(trabajador["id"], hoy, ahora, foto, lat_txt, lon_txt, sitio_marcado)
        auditar("Marcaje entrada (kiosko)", f"Doc {documento} {ahora} en {sitio_marcado}")
        accion = "Entrada"

    nombre = f"{trabajador['nombres']} {trabajador['apellidos']}"
    sitio_txt = f" · {sitio_marcado}" if sitio_marcado else ""
    return jsonify(
        ok=True,
        mensaje=f"{accion} registrada a las {ahora}{sitio_txt}",
        trabajador=nombre,
        accion=accion,
    )
