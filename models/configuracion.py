# ===========================================================
# Módulo: models/configuracion.py
# Función: Acceso a las tablas 'configuracion', 'festivos' y 'turnos'.
#          Estas tablas permiten cambiar el comportamiento laboral
#          del sistema SIN tocar el código fuente.
# Dependencias: utils.db
# ===========================================================

from utils.db import query, execute


# ---------------- Configuración clave/valor ----------------
def obtener_todo():
    """Devuelve toda la configuración como diccionario {clave: valor}."""
    filas = query("SELECT clave, valor FROM configuracion")
    return {f["clave"]: f["valor"] for f in filas}


def obtener(clave, por_defecto=None):
    """Devuelve el valor de una clave de configuración."""
    fila = query("SELECT valor FROM configuracion WHERE clave = ?", (clave,), one=True)
    return fila["valor"] if fila else por_defecto


def guardar(clave, valor):
    """Inserta o actualiza una clave de configuración (UPSERT)."""
    execute(
        """INSERT INTO configuracion (clave, valor) VALUES (?, ?)
           ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor""",
        (clave, str(valor)),
    )


# ---------------- Festivos ----------------
def listar_festivos():
    """Lista de festivos ordenada por fecha."""
    return query("SELECT * FROM festivos ORDER BY fecha")


def es_festivo(fecha):
    """True si la fecha (YYYY-MM-DD) está en la tabla de festivos."""
    fila = query("SELECT 1 FROM festivos WHERE fecha = ?", (fecha,), one=True)
    return fila is not None


def agregar_festivo(fecha, nombre):
    execute("INSERT OR IGNORE INTO festivos (fecha, nombre) VALUES (?, ?)", (fecha, nombre))


def eliminar_festivo(fid):
    execute("DELETE FROM festivos WHERE id = ?", (fid,))


# ---------------- Turnos ----------------
def listar_turnos():
    return query("SELECT * FROM turnos ORDER BY hora_inicio")


def agregar_turno(nombre, hora_inicio, hora_fin):
    execute(
        "INSERT OR IGNORE INTO turnos (nombre, hora_inicio, hora_fin) VALUES (?, ?, ?)",
        (nombre, hora_inicio, hora_fin),
    )


def eliminar_turno(tid):
    execute("DELETE FROM turnos WHERE id = ?", (tid,))
