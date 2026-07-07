# ===========================================================
# Módulo: routes/trabajadores.py
# Función: Gestión del personal (listar, crear, editar, dar de baja).
# Rutas:
#   GET  /trabajadores ............ listado
#   POST /trabajadores/crear ...... alta de trabajador (+foto)
#   POST /trabajadores/<id>/editar  edición
#   POST /trabajadores/<id>/baja .. baja lógica
# Dependencias: flask, werkzeug, models.trabajador, utils
# ===========================================================

import os
from werkzeug.utils import secure_filename
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, send_file)

from models import trabajador as m_trab
from services import excel_service
from utils.seguridad import login_requerido, rol_requerido
from utils.registro import auditar
from config import Config

trabajadores_bp = Blueprint("trabajadores", __name__)


def _guardar_foto(archivo):
    """Guarda la foto del trabajador en /uploads/fotografias.
    Valida la extensión y devuelve el nombre final (o None).
    Se antepone un sello de fecha/hora al nombre para que dos archivos
    llamados igual (p.ej. 'foto.jpg') no se sobrescriban entre sí."""
    if not archivo or archivo.filename == "":
        return None
    ext = archivo.filename.rsplit(".", 1)[-1].lower()
    if ext not in Config.ALLOWED_IMAGE_EXT:
        flash("Formato de imagen no permitido.", "warning")
        return None
    from datetime import datetime
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"{sello}_{secure_filename(archivo.filename)}"
    os.makedirs(Config.FOTOS_FOLDER, exist_ok=True)
    archivo.save(os.path.join(Config.FOTOS_FOLDER, nombre))
    return nombre


@trabajadores_bp.route("/trabajadores")
@login_requerido
def listar():
    """Muestra la tabla de trabajadores activos."""
    return render_template("trabajadores.html", trabajadores=m_trab.listar())


@trabajadores_bp.route("/trabajadores/crear", methods=["POST"])
@login_requerido
def crear():
    """Da de alta un trabajador nuevo."""
    documento = request.form.get("documento", "").strip()
    if m_trab.buscar_por_documento(documento):
        flash("Ya existe un trabajador con ese documento.", "warning")
        return redirect(url_for("trabajadores.listar"))

    foto = _guardar_foto(request.files.get("foto"))
    m_trab.crear(
        documento,
        request.form.get("nombres", "").strip(),
        request.form.get("apellidos", "").strip(),
        request.form.get("cargo", "").strip(),
        request.form.get("area", "").strip(),
        request.form.get("turno", "").strip(),
        foto,
    )
    auditar("Alta de trabajador", documento)
    flash("Trabajador registrado.", "success")
    return redirect(url_for("trabajadores.listar"))


@trabajadores_bp.route("/trabajadores/<int:tid>/editar", methods=["POST"])
@login_requerido
def editar(tid):
    """Actualiza los datos de un trabajador."""
    foto = _guardar_foto(request.files.get("foto"))
    m_trab.actualizar(
        tid,
        request.form.get("nombres", "").strip(),
        request.form.get("apellidos", "").strip(),
        request.form.get("cargo", "").strip(),
        request.form.get("area", "").strip(),
        request.form.get("turno", "").strip(),
        foto,
    )
    auditar("Edición de trabajador", str(tid))
    flash("Datos actualizados.", "success")
    return redirect(url_for("trabajadores.listar"))


@trabajadores_bp.route("/trabajadores/<int:tid>/baja", methods=["POST"])
@rol_requerido("admin")
def baja(tid):
    """Baja lógica del trabajador (solo administrador)."""
    m_trab.desactivar(tid)
    auditar("Baja de trabajador", str(tid))
    flash("Trabajador dado de baja.", "info")
    return redirect(url_for("trabajadores.listar"))


# ===========================================================
#  CARGA MASIVA POR EXCEL
# ===========================================================

@trabajadores_bp.route("/trabajadores/plantilla")
@login_requerido
def descargar_plantilla():
    """Genera y entrega la plantilla Excel para llenar trabajadores."""
    ruta = excel_service.generar_plantilla_trabajadores()
    return send_file(ruta, as_attachment=True)


@trabajadores_bp.route("/trabajadores/importar", methods=["POST"])
@login_requerido
def importar():
    """Recibe un Excel con trabajadores y los crea en bloque.
    Muestra un resumen: creados, repetidos (omitidos) y con errores."""
    archivo = request.files.get("archivo_excel")
    if not archivo or archivo.filename == "":
        flash("Seleccione un archivo Excel.", "warning")
        return redirect(url_for("trabajadores.listar"))

    # Validar extensión. Solo .xlsx: openpyxl NO puede leer el formato
    # antiguo .xls, y aceptarlo provocaba un error 500 al importar.
    ext = archivo.filename.rsplit(".", 1)[-1].lower()
    if ext != "xlsx":
        flash("El archivo debe ser .xlsx (Excel moderno). "
              "Si tiene un .xls, ábralo en Excel y guárdelo como .xlsx.", "warning")
        return redirect(url_for("trabajadores.listar"))

    # Guardar temporalmente para leerlo
    os.makedirs(Config.EXCEL_FOLDER, exist_ok=True)
    ruta_tmp = os.path.join(Config.EXCEL_FOLDER, "_importar_tmp.xlsx")
    archivo.save(ruta_tmp)

    # Leer y validar las filas
    filas, errores = excel_service.leer_trabajadores_excel(ruta_tmp)

    creados = 0
    repetidos = 0
    for t in filas:
        # Omitir si ya existe ese documento
        if m_trab.buscar_por_documento(t["documento"]):
            repetidos += 1
            continue
        m_trab.crear(
            t["documento"], t["nombres"], t["apellidos"],
            t["cargo"], t["area"], t["turno"], None,
        )
        creados += 1

    # Limpiar el temporal
    try:
        os.remove(ruta_tmp)
    except OSError:
        pass

    auditar("Importación masiva",
            f"{creados} creados, {repetidos} repetidos, {len(errores)} con error")

    # Mensajes de resumen
    flash(f"Importación finalizada: {creados} creado(s), "
          f"{repetidos} repetido(s) omitido(s).", "success")
    if errores:
        # Mostrar hasta 5 errores para no saturar la pantalla
        muestra = "; ".join(errores[:5])
        extra = f" (y {len(errores) - 5} más)" if len(errores) > 5 else ""
        flash(f"Filas con problemas: {muestra}{extra}", "warning")

    return redirect(url_for("trabajadores.listar"))
