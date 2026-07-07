# ===========================================================
# Módulo: routes/reportes.py
# Función: Generar reportes de horas trabajadas, clasificar extras
#          y recargos, y exportar a Excel.
# Rutas:
#   GET/POST /reportes ............ filtro por fechas + resumen
#   POST     /reportes/exportar ... descarga Excel
# Dependencias: flask, datetime, models, services
# ===========================================================

from datetime import date, timedelta
from flask import (Blueprint, render_template, request, send_file, flash, redirect, url_for)

from models import asistencia as m_asis
from models import trabajador as m_trab
from models import configuracion as m_config
from services import calculo_horas as calc
from services import excel_service
from utils.seguridad import login_requerido
from utils.registro import auditar

reportes_bp = Blueprint("reportes", __name__)


def _rango_por_defecto():
    """Devuelve (lunes, hoy) de la semana actual como fechas ISO."""
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes.isoformat(), hoy.isoformat()


@reportes_bp.route("/reportes", methods=["GET", "POST"])
@login_requerido
def panel():
    """Filtra registros por rango y calcula el resumen semanal."""
    f_ini, f_fin = _rango_por_defecto()
    trabajador_id = None

    if request.method == "POST":
        f_ini = request.form.get("fecha_inicio") or f_ini
        f_fin = request.form.get("fecha_fin") or f_fin
        trabajador_id = request.form.get("trabajador_id") or None

    registros = m_asis.listar_por_rango(f_ini, f_fin, trabajador_id)

    # ---- Clasificación de horas usando el servicio de cálculo ----
    config = m_config.obtener_todo()
    calculados = []
    for r in registros:
        es_dom_fes = (
            calc.dia_semana(r["fecha"]) == 7 or m_config.es_festivo(r["fecha"])
        )
        calculados.append(calc.calcular_registro(r, config, es_dom_fes))

    resumen = calc.resumen_semanal(calculados, config)

    return render_template(
        "reportes.html",
        registros=registros,
        resumen=resumen,
        trabajadores=m_trab.listar(),
        f_ini=f_ini, f_fin=f_fin,
        trabajador_id=trabajador_id,
    )


@reportes_bp.route("/reportes/exportar", methods=["POST"])
@login_requerido
def exportar():
    """Exporta el rango seleccionado a un archivo Excel descargable."""
    f_ini = request.form.get("fecha_inicio")
    f_fin = request.form.get("fecha_fin")
    trabajador_id = request.form.get("trabajador_id") or None

    if not f_ini or not f_fin:
        flash("Indique el rango de fechas.", "warning")
        return redirect(url_for("reportes.panel"))

    registros = m_asis.listar_por_rango(f_ini, f_fin, trabajador_id)
    ruta = excel_service.exportar_asistencia(registros)
    auditar("Exportación Excel", f"{f_ini} a {f_fin}")
    return send_file(ruta, as_attachment=True)
