# ===========================================================
# Módulo: models/trabajador.py
# Función: Acceso a datos de la tabla 'trabajadores'.
# Funciones: listar, buscar, crear, actualizar, desactivar.
# Dependencias: utils.db
# ===========================================================

from utils.db import query, execute


def listar(solo_activos=True):
    """Devuelve la lista de trabajadores ordenada por apellidos."""
    sql = "SELECT * FROM trabajadores"
    if solo_activos:
        sql += " WHERE activo = 1"
    sql += " ORDER BY apellidos, nombres"
    return query(sql)


def buscar_por_id(tid):
    """Devuelve un trabajador por id, o None."""
    return query("SELECT * FROM trabajadores WHERE id = ?", (tid,), one=True)


def buscar_por_documento(documento):
    """Devuelve un trabajador por número de documento, o None."""
    return query("SELECT * FROM trabajadores WHERE documento = ?", (documento,), one=True)


def crear(documento, nombres, apellidos, cargo, area, turno, foto=None):
    """Inserta un trabajador nuevo y devuelve su id."""
    return execute(
        """INSERT INTO trabajadores (documento, nombres, apellidos, cargo, area, turno, foto)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (documento, nombres, apellidos, cargo, area, turno, foto),
    )


def actualizar(tid, nombres, apellidos, cargo, area, turno, foto=None):
    """Actualiza los datos de un trabajador. Si foto es None, conserva la actual."""
    if foto is None:
        execute(
            """UPDATE trabajadores
               SET nombres=?, apellidos=?, cargo=?, area=?, turno=?
               WHERE id=?""",
            (nombres, apellidos, cargo, area, turno, tid),
        )
    else:
        execute(
            """UPDATE trabajadores
               SET nombres=?, apellidos=?, cargo=?, area=?, turno=?, foto=?
               WHERE id=?""",
            (nombres, apellidos, cargo, area, turno, foto, tid),
        )


def desactivar(tid):
    """Baja lógica: marca el trabajador como inactivo (no borra histórico)."""
    execute("UPDATE trabajadores SET activo = 0 WHERE id = ?", (tid,))


def contar_activos():
    """Cuenta de trabajadores activos (para el dashboard)."""
    fila = query("SELECT COUNT(*) AS n FROM trabajadores WHERE activo = 1", one=True)
    return fila["n"] if fila else 0
