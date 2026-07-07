# ===========================================================
# Módulo: routes/configuracion.py
# Función: Panel del administrador para modificar TODOS los
#          parámetros laborales sin tocar el código fuente:
#          horas semanales, horario, recargos, valor hora,
#          festivos y turnos.
# Rutas:
#   GET/POST /configuracion ............ parámetros generales
#   POST     /configuracion/festivo .... agregar festivo
#   POST     /configuracion/festivo/<id>/eliminar
#   POST     /configuracion/turno ...... agregar turno
#   POST     /configuracion/turno/<id>/eliminar
#   POST     /configuracion/backup ..... respaldo de la BD
# Acceso: solo rol 'admin'.
# Dependencias: flask, models.configuracion, services.backup_service
# ===========================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash

from models import configuracion as m_config
from models import sitio as m_sitio
from services import backup_service
from utils.seguridad import rol_requerido
from utils.registro import auditar

configuracion_bp = Blueprint("configuracion", __name__)

# Claves de configuración editables desde el formulario general.
CLAVES_EDITABLES = [
    "horas_semanales", "hora_inicio_jornada", "hora_fin_jornada",
    "minutos_almuerzo", "dias_laborables", "inicio_nocturno", "fin_nocturno",
    "valor_hora_ordinaria", "recargo_extra_diurna", "recargo_extra_nocturna",
    "recargo_nocturno", "recargo_dominical", "tolerancia_minutos",
    # ---- Ubicación de la obra (geocerca) y reglas del kiosko ----
    "obra_latitud", "obra_longitud", "obra_radio_m",
    "validar_ubicacion", "exigir_foto",
]


@configuracion_bp.route("/configuracion", methods=["GET", "POST"])
@rol_requerido("admin")
def panel():
    """Lee y guarda los parámetros laborales generales."""
    if request.method == "POST":
        for clave in CLAVES_EDITABLES:
            if clave in request.form:
                m_config.guardar(clave, request.form.get(clave))
        auditar("Actualización de configuración", "Parámetros laborales")
        flash("Configuración guardada.", "success")
        return redirect(url_for("configuracion.panel"))

    return render_template(
        "configuracion.html",
        config=m_config.obtener_todo(),
        festivos=m_config.listar_festivos(),
        turnos=m_config.listar_turnos(),
        sitios=m_sitio.listar(),
    )


@configuracion_bp.route("/configuracion/festivo", methods=["POST"])
@rol_requerido("admin")
def agregar_festivo():
    """Agrega un día festivo parametrizable."""
    m_config.agregar_festivo(
        request.form.get("fecha"), request.form.get("nombre", "")
    )
    auditar("Festivo agregado", request.form.get("fecha", ""))
    flash("Festivo agregado.", "success")
    return redirect(url_for("configuracion.panel"))


@configuracion_bp.route("/configuracion/festivo/<int:fid>/eliminar", methods=["POST"])
@rol_requerido("admin")
def eliminar_festivo(fid):
    m_config.eliminar_festivo(fid)
    auditar("Festivo eliminado", str(fid))
    flash("Festivo eliminado.", "info")
    return redirect(url_for("configuracion.panel"))


@configuracion_bp.route("/configuracion/turno", methods=["POST"])
@rol_requerido("admin")
def agregar_turno():
    """Agrega un turno parametrizable."""
    m_config.agregar_turno(
        request.form.get("nombre"),
        request.form.get("hora_inicio"),
        request.form.get("hora_fin"),
    )
    auditar("Turno agregado", request.form.get("nombre", ""))
    flash("Turno agregado.", "success")
    return redirect(url_for("configuracion.panel"))


@configuracion_bp.route("/configuracion/turno/<int:tid>/eliminar", methods=["POST"])
@rol_requerido("admin")
def eliminar_turno(tid):
    m_config.eliminar_turno(tid)
    auditar("Turno eliminado", str(tid))
    flash("Turno eliminado.", "info")
    return redirect(url_for("configuracion.panel"))


@configuracion_bp.route("/configuracion/backup", methods=["POST"])
@rol_requerido("admin")
def backup():
    """Genera una copia de seguridad de la base de datos."""
    ruta = backup_service.crear_backup()
    if ruta:
        auditar("Respaldo de BD", ruta)
        flash("Respaldo creado correctamente.", "success")
    else:
        flash("Aún no existe base de datos para respaldar.", "warning")
    return redirect(url_for("configuracion.panel"))


# ===========================================================
#  GESTIÓN DE SITIOS (estaciones + patio taller)
# ===========================================================

@configuracion_bp.route("/configuracion/sitio", methods=["POST"])
@rol_requerido("admin")
def agregar_sitio():
    """Agrega un sitio nuevo. Acepta el campo 'coordenadas' como
    'lat, lon' (tal como se copia de Google Maps) o lat/lon separados."""
    nombre = request.form.get("nombre", "").strip()
    coordenadas = request.form.get("coordenadas", "").strip()
    radio = request.form.get("radio_m", "300").strip() or "300"

    lat, lon = "", ""
    if coordenadas and "," in coordenadas:
        partes = coordenadas.split(",", 1)
        lat = partes[0].strip()
        lon = partes[1].strip()

    if not nombre or not lat or not lon:
        flash("Indique el nombre y las coordenadas (lat, lon).", "warning")
        return redirect(url_for("configuracion.panel"))

    m_sitio.crear(nombre, lat, lon, radio)
    auditar("Sitio agregado", nombre)
    flash(f"Sitio '{nombre}' agregado.", "success")
    return redirect(url_for("configuracion.panel"))


@configuracion_bp.route("/configuracion/sitio/<int:sid>/actualizar", methods=["POST"])
@rol_requerido("admin")
def actualizar_sitio(sid):
    """Actualiza coordenadas, radio y estado (activo) de un sitio.
    Acepta 'coordenadas' como 'lat, lon'."""
    coordenadas = request.form.get("coordenadas", "").strip()
    radio = request.form.get("radio_m", "300").strip() or "300"
    activo = request.form.get("activo") == "1"

    if coordenadas and "," in coordenadas:
        partes = coordenadas.split(",", 1)
        lat = partes[0].strip()
        lon = partes[1].strip()
        m_sitio.actualizar(sid, lat, lon, radio, activo)
        auditar("Sitio actualizado", str(sid))
        flash("Sitio actualizado.", "success")
    else:
        flash("Coordenadas inválidas. Use el formato lat, lon.", "warning")
    return redirect(url_for("configuracion.panel"))


@configuracion_bp.route("/configuracion/sitio/<int:sid>/eliminar", methods=["POST"])
@rol_requerido("admin")
def eliminar_sitio(sid):
    """Elimina un sitio."""
    m_sitio.eliminar(sid)
    auditar("Sitio eliminado", str(sid))
    flash("Sitio eliminado.", "info")
    return redirect(url_for("configuracion.panel"))
