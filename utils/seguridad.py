# ===========================================================
# Módulo: utils/seguridad.py
# Función: Decoradores para proteger rutas según sesión y rol.
# Funciones:
#   - login_requerido(f) ... exige sesión iniciada
#   - rol_requerido(*roles) . exige que el usuario tenga cierto rol
# Flujo: si no cumple, redirige al login o muestra error 403.
# Dependencias: functools, flask
# ===========================================================

from functools import wraps
from flask import session, redirect, url_for, flash, abort


def login_requerido(f):
    """Bloquea el acceso a una vista si no hay usuario en sesión."""
    @wraps(f)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Inicie sesión para continuar.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return envoltura


def rol_requerido(*roles):
    """Permite el acceso solo a los roles indicados.
    Uso:  @rol_requerido('admin')  ó  @rol_requerido('admin','supervisor')"""
    def decorador(f):
        @wraps(f)
        def envoltura(*args, **kwargs):
            if "usuario_id" not in session:
                return redirect(url_for("auth.login"))
            if session.get("rol") not in roles:
                abort(403)  # acceso prohibido
            return f(*args, **kwargs)
        return envoltura
    return decorador
