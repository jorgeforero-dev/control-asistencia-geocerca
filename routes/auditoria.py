# ===========================================================
# Módulo: routes/auditoria.py
# Función: Mostrar la traza de auditoría del sistema (solo admin).
# Rutas:
#   GET /auditoria ... últimas acciones registradas
# Dependencias: flask, models.auditoria, utils.seguridad
# ===========================================================

from flask import Blueprint, render_template
from models import auditoria as m_auditoria
from utils.seguridad import rol_requerido

auditoria_bp = Blueprint("auditoria", __name__)


@auditoria_bp.route("/auditoria")
@rol_requerido("admin")
def panel():
    """Lista las últimas trazas de auditoría."""
    return render_template("auditoria.html", trazas=m_auditoria.listar())
