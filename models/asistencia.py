# ===========================================================
# Módulo: models/asistencia.py
# Función: Acceso a datos de la tabla 'asistencia'.
# Funciones: registrar entrada/salida, listar por rango, etc.
# Dependencias: utils.db
# ===========================================================

from utils.db import query, execute


def abierta_de_hoy(trabajador_id, fecha):
    """Devuelve el registro de asistencia del trabajador en la fecha
    dada que aún NO tenga hora de salida, o None."""
    return query(
        """SELECT * FROM asistencia
           WHERE trabajador_id = ? AND fecha = ? AND (hora_salida IS NULL OR hora_salida = '')
           ORDER BY id DESC LIMIT 1""",
        (trabajador_id, fecha),
        one=True,
    )


def registrar_entrada(trabajador_id, fecha, hora, foto=None, lat=None, lon=None, sitio=None):
    """Crea un registro de entrada (sin salida) con foto, ubicación y sitio."""
    return execute(
        """INSERT INTO asistencia
           (trabajador_id, fecha, hora_entrada, foto_entrada, lat_entrada, lon_entrada, sitio_entrada)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (trabajador_id, fecha, hora, foto, lat, lon, sitio),
    )


def registrar_salida(registro_id, hora, foto=None, lat=None, lon=None, sitio=None):
    """Completa el registro abierto con hora, foto, ubicación y sitio de salida."""
    execute(
        """UPDATE asistencia
           SET hora_salida = ?, foto_salida = ?, lat_salida = ?, lon_salida = ?, sitio_salida = ?
           WHERE id = ?""",
        (hora, foto, lat, lon, sitio, registro_id),
    )


def listar_por_rango(fecha_inicio, fecha_fin, trabajador_id=None):
    """Lista registros entre dos fechas, opcionalmente de un trabajador.
    Hace JOIN con trabajadores para traer el nombre."""
    sql = """
        SELECT a.*, t.documento, t.nombres, t.apellidos
        FROM asistencia a
        JOIN trabajadores t ON t.id = a.trabajador_id
        WHERE a.fecha BETWEEN ? AND ?
    """
    params = [fecha_inicio, fecha_fin]
    if trabajador_id:
        sql += " AND a.trabajador_id = ?"
        params.append(trabajador_id)
    sql += " ORDER BY a.fecha DESC, t.apellidos"
    return query(sql, tuple(params))


def listar_dia(fecha):
    """Registros de un día específico (para el dashboard)."""
    return listar_por_rango(fecha, fecha)


def contar_presentes(fecha):
    """Cuántos trabajadores tienen entrada registrada hoy."""
    fila = query(
        "SELECT COUNT(DISTINCT trabajador_id) AS n FROM asistencia WHERE fecha = ?",
        (fecha,), one=True,
    )
    return fila["n"] if fila else 0


def concentracion_por_sitio(fecha_inicio, fecha_fin):
    """Devuelve, por cada sitio donde hubo marcajes en el rango:
      - presentes: entradas SIN salida (gente que sigue dentro)
      - entradas:  total de entradas registradas en ese sitio
      - salidas:   total de salidas registradas en ese sitio
      - total:     entradas + salidas (volumen de marcajes)

    'presentes' se agrupa por el sitio de ENTRADA (donde la persona
    inició la jornada y aún no ha marcado salida). Sirve para saber
    dónde está concentrada la gente que sigue en obra.
    """
    # 1) Presentes por sitio de entrada (sin hora_salida) en el rango
    presentes = query(
        """SELECT sitio_entrada AS sitio, COUNT(*) AS n
           FROM asistencia
           WHERE fecha BETWEEN ? AND ?
             AND hora_salida IS NULL
             AND sitio_entrada IS NOT NULL
           GROUP BY sitio_entrada""",
        (fecha_inicio, fecha_fin),
    )

    # 2) Total de entradas por sitio
    entradas = query(
        """SELECT sitio_entrada AS sitio, COUNT(*) AS n
           FROM asistencia
           WHERE fecha BETWEEN ? AND ? AND sitio_entrada IS NOT NULL
           GROUP BY sitio_entrada""",
        (fecha_inicio, fecha_fin),
    )

    # 3) Total de salidas por sitio
    salidas = query(
        """SELECT sitio_salida AS sitio, COUNT(*) AS n
           FROM asistencia
           WHERE fecha BETWEEN ? AND ? AND sitio_salida IS NOT NULL
           GROUP BY sitio_salida""",
        (fecha_inicio, fecha_fin),
    )

    # Combinar los tres resultados en un diccionario por sitio
    mapa = {}

    def asegurar(nombre):
        if nombre not in mapa:
            mapa[nombre] = {"sitio": nombre, "presentes": 0,
                            "entradas": 0, "salidas": 0, "total": 0}
        return mapa[nombre]

    for r in presentes:
        asegurar(r["sitio"])["presentes"] = r["n"]
    for r in entradas:
        d = asegurar(r["sitio"])
        d["entradas"] = r["n"]
        d["total"] += r["n"]
    for r in salidas:
        d = asegurar(r["sitio"])
        d["salidas"] = r["n"]
        d["total"] += r["n"]

    # Ordenar por presentes (desc) y luego por total (desc)
    filas = sorted(mapa.values(),
                   key=lambda x: (x["presentes"], x["total"]), reverse=True)
    return filas
