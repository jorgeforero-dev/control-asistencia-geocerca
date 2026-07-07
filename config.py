# ===========================================================
# Módulo: config.py
# Función: Configuración global de la aplicación Flask.
#          Centraliza rutas, llaves y parámetros por defecto.
# Variables principales:
#   - BASE_DIR ........ ruta raíz del proyecto
#   - SECRET_KEY ...... llave para firmar sesiones/cookies
#   - DATABASE_PATH ... ubicación del archivo SQLite
#   - UPLOAD_FOLDER ... carpeta de archivos subidos
# Dependencias: os, datetime
# ===========================================================

import os
import secrets

# Ruta absoluta a la raíz del proyecto (carpeta que contiene este archivo)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _obtener_secret_key():
    """Devuelve la llave secreta para firmar sesiones.
    Orden de búsqueda:
      1) Variable de entorno SECRET_KEY (recomendado en producción).
      2) Archivo local 'instance/secret_key.txt' (se genera solo la
         primera vez con un valor aleatorio fuerte y queda guardado).
    Así NUNCA se usa una llave pública conocida y las sesiones se
    mantienen estables entre reinicios."""
    env = os.environ.get("SECRET_KEY")
    if env:
        return env
    carpeta = os.path.join(BASE_DIR, "instance")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, "secret_key.txt")
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            valor = f.read().strip()
            if valor:
                return valor
    # Generar una llave aleatoria fuerte y guardarla
    valor = secrets.token_hex(32)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(valor)
    return valor


class Config:
    """Configuración base. Estas variables NO cambian el negocio:
    los parámetros laborales (horas, recargos, festivos) viven en la
    base de datos y se editan desde el panel de Configuración."""

    # ---- Seguridad ----
    # Llave secreta segura (env > archivo generado). Nunca un valor público.
    SECRET_KEY = _obtener_secret_key()

    # ---- Base de datos ----
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "asistencia.db")

    # ---- Carpetas de almacenamiento ----
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    FOTOS_FOLDER = os.path.join(UPLOAD_FOLDER, "fotografias")
    DOCS_FOLDER = os.path.join(UPLOAD_FOLDER, "documentos")
    EXCEL_FOLDER = os.path.join(BASE_DIR, "excel")
    BACKUP_FOLDER = os.path.join(BASE_DIR, "backups")
    LOG_FOLDER = os.path.join(BASE_DIR, "logs")

    # ---- Límites de carga ----
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB por archivo
    ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_DOC_EXT = {"pdf", "doc", "docx", "xlsx"}

    # ---- Sesión ----
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # En producción con HTTPS, defina la variable de entorno
    # COOKIE_SEGURA=1 para que la cookie solo viaje por conexiones
    # cifradas. En local (sin HTTPS) déjela sin definir.
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SEGURA") == "1"


# -----------------------------------------------------------
# PARÁMETROS LABORALES POR DEFECTO (Colombia)
# -----------------------------------------------------------
# Estos valores SOLO se usan la primera vez, para "sembrar" la
# tabla de configuración. Después se editan desde el panel admin
# sin tocar el código fuente.
#
# Base legal de referencia (editable por el administrador):
#   - Ley 2101 de 2021: reducción gradual de la jornada a 42 h/sem.
#   - Código Sustantivo del Trabajo (CST) y reforma laboral vigente:
#     recargos de extras, nocturno y dominical/festivo.
# -----------------------------------------------------------
CONFIG_LABORAL_DEFAULT = {
    "horas_semanales": "42",          # Jornada ordinaria máxima semanal
    "hora_inicio_jornada": "07:00",   # Inicio de la jornada
    "hora_fin_jornada": "16:00",      # Fin de la jornada
    "minutos_almuerzo": "60",         # Tiempo de almuerzo (no remunerado)
    "dias_laborables": "1,2,3,4,5",   # Lun..Vie (1=Lunes ... 7=Domingo)
    "inicio_nocturno": "21:00",       # Hora a partir de la cual aplica recargo nocturno
    "fin_nocturno": "06:00",          # Hora hasta la cual aplica recargo nocturno
    "valor_hora_ordinaria": "6189",   # Valor de la hora ordinaria (COP) - ejemplo
    # Recargos expresados como porcentaje adicional sobre la hora ordinaria
    "recargo_extra_diurna": "25",     # +25%
    "recargo_extra_nocturna": "75",   # +75%
    "recargo_nocturno": "35",         # +35% (trabajo ordinario en horario nocturno)
    "recargo_dominical": "75",        # +75% sobre la ordinaria (ajustable a 80/90/100)
    "tolerancia_minutos": "5",        # Minutos de tolerancia para marcar a tiempo
}
