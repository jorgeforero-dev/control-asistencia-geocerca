# ===========================================================
# Módulo: routes/auth.py
# Función: Autenticación (inicio y cierre de sesión).
# Rutas:
#   GET/POST /login ... formulario y validación de credenciales
#   GET      /logout .. cierra la sesión
# Seguridad: límite de intentos por IP para frenar ataques de
#            fuerza bruta sobre la contraseña del administrador.
# Dependencias: flask, time, models.usuario, utils.registro
# ===========================================================

import time
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from models import usuario as m_usuario
from utils.registro import auditar

# El blueprint agrupa estas rutas; se registra en app.py
auth_bp = Blueprint("auth", __name__)

# -----------------------------------------------------------
# Control de intentos de login por dirección IP (en memoria).
# Tras varios fallos seguidos, se bloquea temporalmente esa IP.
# Es una defensa simple y efectiva contra fuerza bruta.
# -----------------------------------------------------------
_MAX_INTENTOS = 5           # fallos permitidos antes de bloquear
_BLOQUEO_SEGUNDOS = 300     # 5 minutos de bloqueo
_intentos = {}              # { ip: {"fallos": n, "hasta": timestamp} }


def _ip_cliente():
    """Devuelve la IP del cliente (considera proxy si está detrás de uno)."""
    adelante = request.headers.get("X-Forwarded-For", "")
    if adelante:
        return adelante.split(",")[0].strip()
    return request.remote_addr or "desconocida"


def _esta_bloqueada(ip):
    """True si la IP está en periodo de bloqueo. Devuelve segundos restantes."""
    reg = _intentos.get(ip)
    if reg and reg.get("hasta", 0) > time.time():
        return int(reg["hasta"] - time.time())
    return 0


def _registrar_fallo(ip):
    """Suma un fallo a la IP y la bloquea si pasa el máximo."""
    reg = _intentos.get(ip, {"fallos": 0, "hasta": 0})
    reg["fallos"] += 1
    if reg["fallos"] >= _MAX_INTENTOS:
        reg["hasta"] = time.time() + _BLOQUEO_SEGUNDOS
        reg["fallos"] = 0  # reinicia el contador tras bloquear
    _intentos[ip] = reg


def _limpiar(ip):
    """Borra el registro de intentos de una IP tras un login exitoso."""
    _intentos.pop(ip, None)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Muestra el formulario (GET) y valida credenciales (POST)."""
    if request.method == "POST":
        ip = _ip_cliente()

        # ¿IP bloqueada por demasiados intentos?
        restante = _esta_bloqueada(ip)
        if restante > 0:
            minutos = max(1, restante // 60)
            flash(f"Demasiados intentos. Espere {minutos} minuto(s) e intente de nuevo.",
                  "danger")
            auditar("Login bloqueado por intentos", f"IP {ip}")
            return render_template("login.html")

        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")

        usr = m_usuario.buscar_por_correo(correo)
        if usr and usr["activo"] and m_usuario.verificar_password(usr, password):
            # Credenciales correctas: se guarda el mínimo en sesión.
            _limpiar(ip)
            session.clear()
            session["usuario_id"] = usr["id"]
            session["nombre"] = usr["nombre"]
            session["rol"] = usr["rol"]
            session.permanent = False
            auditar("Inicio de sesión", f"Usuario {correo}")
            return redirect(url_for("main.dashboard"))

        # Credenciales incorrectas: registrar el fallo
        _registrar_fallo(ip)
        auditar("Login fallido", f"IP {ip}, correo {correo}")
        flash("Correo o contraseña incorrectos.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Cierra la sesión actual y vuelve al login."""
    auditar("Cierre de sesión", session.get("nombre", ""))
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("auth.login"))
