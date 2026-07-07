# ===========================================================
# Módulo: app.py
# Función: Punto de entrada de la aplicación Flask.
#          Crea la aplicación (patrón "application factory"),
#          carga la configuración, inicializa la base de datos y
#          registra todos los blueprints (módulos de rutas).
#
# Seguridad incorporada:
#   - Protección CSRF en todos los formularios (Flask-WTF).
#   - Las fotos solo se sirven a usuarios autenticados.
#   - Cabeceras de seguridad en cada respuesta.
#   - Modo debug APAGADO por defecto (se enciende solo con
#     la variable de entorno FLASK_DEBUG=1, nunca en producción).
# Dependencias: flask, flask_wtf, config, utils, routes
# ===========================================================

import os
from flask import Flask, render_template, send_from_directory
from flask_wtf import CSRFProtect

from config import Config
from utils.db import init_db
from utils.seguridad import login_requerido

# --- Importación de los blueprints (uno por módulo funcional) ---
from routes.auth import auth_bp
from routes.main import main_bp
from routes.kiosko import kiosko_bp, marcar_kiosko
from routes.trabajadores import trabajadores_bp
from routes.asistencia import asistencia_bp
from routes.reportes import reportes_bp
from routes.configuracion import configuracion_bp
from routes.auditoria import auditoria_bp

# Objeto de protección CSRF (se inicializa dentro de crear_app)
csrf = CSRFProtect()


def crear_app():
    """Construye la aplicación Flask completamente configurada."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # 1) Asegurar que existan las carpetas de trabajo
    for carpeta in [
        os.path.dirname(Config.DATABASE_PATH),
        Config.FOTOS_FOLDER, Config.DOCS_FOLDER,
        Config.EXCEL_FOLDER, Config.BACKUP_FOLDER, Config.LOG_FOLDER,
    ]:
        os.makedirs(carpeta, exist_ok=True)

    # 2) Inicializar base de datos (tablas + datos semilla)
    init_db()

    # 3) Activar protección CSRF en todos los formularios POST.
    #    El kiosko envía JSON desde la cámara y se exenta más abajo.
    csrf.init_app(app)

    # 4) Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(kiosko_bp)
    app.register_blueprint(trabajadores_bp)
    app.register_blueprint(asistencia_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(configuracion_bp)
    app.register_blueprint(auditoria_bp)

    # El endpoint público del kiosko usa JSON (no formulario), por eso
    # se exenta de CSRF. Su seguridad está en la validación de documento,
    # foto, ubicación y el límite de intentos por IP.
    csrf.exempt(marcar_kiosko)

    # 5) Ruta para servir fotografías subidas (SOLO usuarios con sesión)
    @app.route("/uploads/fotografias/<path:nombre>")
    @login_requerido
    def foto(nombre):
        """Entrega una imagen guardada en /uploads/fotografias.
        Protegida: solo el administrador/supervisor autenticado puede
        ver las fotos de los trabajadores. send_from_directory evita
        el acceso a rutas fuera de la carpeta (path traversal)."""
        return send_from_directory(Config.FOTOS_FOLDER, nombre)

    # 6) Cabeceras de seguridad en todas las respuestas
    @app.after_request
    def cabeceras_seguridad(resp):
        # Evita que el navegador adivine tipos de archivo
        resp.headers["X-Content-Type-Options"] = "nosniff"
        # Evita que la página sea embebida en iframes de otros sitios
        resp.headers["X-Frame-Options"] = "DENY"
        # Controla la información de referencia que se envía
        resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    # 7) Manejadores de error amigables
    @app.errorhandler(403)
    def prohibido(_):
        return render_template("error.html", codigo=403,
                               mensaje="No tiene permisos para esta sección."), 403

    @app.errorhandler(404)
    def no_encontrado(_):
        return render_template("error.html", codigo=404,
                               mensaje="Página no encontrada."), 404

    @app.errorhandler(413)
    def muy_grande(_):
        return render_template("error.html", codigo=413,
                               mensaje="El archivo es demasiado grande."), 413

    return app


# Instancia global para servidores WSGI (gunicorn, waitress) y para
# ejecución directa con "python app.py".
app = crear_app()


if __name__ == "__main__":
    # IMPORTANTE: debug APAGADO por defecto. Solo se enciende para
    # desarrollo local definiendo FLASK_DEBUG=1. NUNCA en producción.
    modo_debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=5000, debug=modo_debug)
