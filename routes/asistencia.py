# ===========================================================
# Módulo: routes/asistencia.py
# Función: Registro de entradas y salidas de los trabajadores.
# Rutas:
#   GET  /asistencia ............ pantalla de marcaje
#   POST /asistencia/marcar ..... registra entrada o salida
# Lógica: si el trabajador tiene una jornada abierta hoy, se marca
#         salida; si no, se marca entrada. La hora se toma del servidor.
# Dependencias: flask, datetime, models, utils
# ===========================================================

from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash

from models import trabajador as m_trab
from models import asistencia as m_asis
from utils.seguridad import login_requerido
from utils.registro import auditar

asistencia_bp = Blueprint("asistencia", __name__)


@asistencia_bp.route("/asistencia")
@login_requerido
def panel():
    """Pantalla de marcaje: lista los trabajadores activos."""
    return render_template(
        "asistencia.html",
        trabajadores=m_trab.listar(),
        registros_hoy=m_asis.listar_dia(date.today().isoformat()),
    )


@asistencia_bp.route("/asistencia/marcar", methods=["POST"])
@login_requerido
def marcar():
    """Registra entrada o salida según el estado actual del trabajador."""
    trabajador_id = request.form.get("trabajador_id")
    if not trabajador_id:
        flash("Seleccione un trabajador.", "warning")
        return redirect(url_for("asistencia.panel"))

    hoy = date.today().isoformat()
    ahora = datetime.now().strftime("%H:%M")

    abierta = m_asis.abierta_de_hoy(trabajador_id, hoy)
    if abierta:
        # Ya tiene entrada sin salida -> registramos salida.
        m_asis.registrar_salida(abierta["id"], ahora)
        auditar("Marcaje salida", f"Trabajador {trabajador_id} {ahora}")
        flash(f"Salida registrada a las {ahora}.", "success")
    else:
        # No tiene jornada abierta -> registramos entrada.
        m_asis.registrar_entrada(trabajador_id, hoy, ahora)
        auditar("Marcaje entrada", f"Trabajador {trabajador_id} {ahora}")
        flash(f"Entrada registrada a las {ahora}.", "success")

    return redirect(url_for("asistencia.panel"))
