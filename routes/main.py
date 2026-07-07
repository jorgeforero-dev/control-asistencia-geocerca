# ===========================================================
# Módulo: routes/main.py
# Función: Páginas principales: portada, dashboard y perfil.
# Rutas:
#   GET  /          ... portada pública (index)
#   GET  /dashboard ... panel con indicadores (requiere login)
#   GET/POST /perfil .. datos del usuario y cambio de contraseña
# Dependencias: flask, models, utils, datetime
# ===========================================================

from datetime import date
from flask import (Blueprint, render_template, session, request,
                   flash, redirect, url_for, send_file)

from models import trabajador as m_trab
from models import asistencia as m_asis
from models import usuario as m_usuario
from services import excel_service
from utils.seguridad import login_requerido
from utils.registro import auditar

main_bp = Blueprint("main", __name__)


@main_bp.route("/dashboard")
@login_requerido
def dashboard():
    """Panel principal con indicadores del día y concentración por sitio.
    Acepta un rango de fechas opcional (?inicio=YYYY-MM-DD&fin=YYYY-MM-DD)
    para el tablero de concentración. Por defecto, el día de hoy."""
    hoy = date.today().isoformat()

    # Rango de fechas para el tablero de concentración (por defecto: hoy)
    inicio = request.args.get("inicio", hoy)
    fin = request.args.get("fin", hoy)
    # Si el usuario invierte las fechas, las corregimos
    if inicio > fin:
        inicio, fin = fin, inicio

    indicadores = {
        "trabajadores_activos": m_trab.contar_activos(),
        "presentes_hoy": m_asis.contar_presentes(hoy),
        "registros_hoy": m_asis.listar_dia(hoy),
        "fecha": hoy,
        # Tablero de concentración por estación en el rango elegido
        "concentracion": m_asis.concentracion_por_sitio(inicio, fin),
        "rango_inicio": inicio,
        "rango_fin": fin,
    }
    return render_template("dashboard.html", ind=indicadores)


@main_bp.route("/dashboard/exportar-concentracion")
@login_requerido
def exportar_concentracion():
    """Descarga en Excel la concentración por sitio del rango elegido."""
    hoy = date.today().isoformat()
    inicio = request.args.get("inicio", hoy)
    fin = request.args.get("fin", hoy)
    if inicio > fin:
        inicio, fin = fin, inicio

    filas = m_asis.concentracion_por_sitio(inicio, fin)
    ruta = excel_service.exportar_concentracion(filas, inicio, fin)
    auditar("Exportar concentración", f"{inicio} a {fin}")
    return send_file(ruta, as_attachment=True)


@main_bp.route("/perfil", methods=["GET", "POST"])
@login_requerido
def perfil():
    """Muestra el perfil y permite cambiar el correo y/o la contraseña."""
    usr = m_usuario.buscar_por_id(session["usuario_id"])

    if request.method == "POST":
        accion = request.form.get("accion", "")

        # ---- Actualizar correo ----
        if accion == "correo":
            correo_nuevo = request.form.get("correo_nuevo", "").strip().lower()
            if not correo_nuevo or "@" not in correo_nuevo:
                flash("Escriba un correo válido.", "danger")
            else:
                # Verificar que no lo use otro usuario
                existente = m_usuario.buscar_por_correo(correo_nuevo)
                if existente and existente["id"] != usr["id"]:
                    flash("Ese correo ya está en uso por otra cuenta.", "danger")
                else:
                    m_usuario.actualizar_correo(usr["id"], correo_nuevo)
                    session["correo"] = correo_nuevo
                    auditar("Cambio de correo", f"{usr['correo']} -> {correo_nuevo}")
                    flash("Correo actualizado. Úselo para iniciar sesión.", "success")
                    return redirect(url_for("main.perfil"))

        # ---- Actualizar contraseña ----
        else:
            nueva = request.form.get("password_nueva", "")
            confirma = request.form.get("password_confirma", "")
            if len(nueva) < 8:
                flash("La contraseña debe tener al menos 8 caracteres.", "danger")
            elif nueva != confirma:
                flash("Las contraseñas no coinciden.", "danger")
            else:
                m_usuario.actualizar_password(usr["id"], nueva)
                auditar("Cambio de contraseña", usr["correo"])
                flash("Contraseña actualizada.", "success")
                return redirect(url_for("main.perfil"))

    # Recargar por si cambió el correo
    usr = m_usuario.buscar_por_id(session["usuario_id"])
    return render_template("perfil.html", usuario=usr)
