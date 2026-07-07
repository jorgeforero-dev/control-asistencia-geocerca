# ===========================================================
# Módulo: models/usuario.py
# Función: Acceso a datos de la tabla 'usuarios' (login del sistema).
# Funciones:
#   - buscar_por_correo(correo)
#   - buscar_por_id(uid)
#   - crear(nombre, correo, password, rol)
#   - listar()
# Dependencias: utils.db, werkzeug.security
# ===========================================================

from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import query, execute


def buscar_por_correo(correo):
    """Devuelve el usuario (dict) cuyo correo coincide, o None."""
    return query("SELECT * FROM usuarios WHERE correo = ?", (correo,), one=True)


def buscar_por_id(uid):
    """Devuelve el usuario por id, o None."""
    return query("SELECT * FROM usuarios WHERE id = ?", (uid,), one=True)


def verificar_password(usuario, password_plano):
    """Compara la contraseña en texto con el hash almacenado."""
    return check_password_hash(usuario["password_hash"], password_plano)


def crear(nombre, correo, password, rol="supervisor"):
    """Crea un usuario nuevo con la contraseña hasheada."""
    return execute(
        """INSERT INTO usuarios (nombre, correo, password_hash, rol)
           VALUES (?, ?, ?, ?)""",
        (nombre, correo, generate_password_hash(password), rol),
    )


def actualizar_password(uid, password_nuevo):
    """Cambia la contraseña de un usuario existente."""
    execute(
        "UPDATE usuarios SET password_hash = ? WHERE id = ?",
        (generate_password_hash(password_nuevo), uid),
    )


def actualizar_correo(uid, correo_nuevo):
    """Cambia el correo de un usuario existente."""
    execute(
        "UPDATE usuarios SET correo = ? WHERE id = ?",
        (correo_nuevo, uid),
    )


def listar():
    """Lista todos los usuarios del sistema."""
    return query("SELECT id, nombre, correo, rol, activo, creado_en FROM usuarios ORDER BY nombre")
