# ===========================================================
# Módulo: models/sitio.py
# Función: Acceso a datos de la tabla 'sitios' (estaciones y
#          patio taller de la Línea 1). Cada sitio es un punto
#          con su propio radio permitido.
# Dependencias: utils.db
# ===========================================================

from utils.db import query, execute


def listar(solo_activos=False):
    """Lista los sitios. Si solo_activos=True, solo los habilitados."""
    sql = "SELECT * FROM sitios"
    if solo_activos:
        sql += " WHERE activo = 1"
    sql += " ORDER BY nombre"
    return query(sql)


def crear(nombre, latitud, longitud, radio_m="300"):
    """Crea un sitio nuevo."""
    return execute(
        """INSERT INTO sitios (nombre, latitud, longitud, radio_m, activo)
           VALUES (?, ?, ?, ?, 1)""",
        (nombre, latitud, longitud, radio_m),
    )


def actualizar(sid, latitud, longitud, radio_m, activo):
    """Actualiza coordenadas, radio y estado de un sitio."""
    execute(
        """UPDATE sitios SET latitud=?, longitud=?, radio_m=?, activo=?
           WHERE id=?""",
        (latitud, longitud, radio_m, 1 if activo else 0, sid),
    )


def eliminar(sid):
    """Elimina un sitio."""
    execute("DELETE FROM sitios WHERE id = ?", (sid,))
