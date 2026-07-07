# ===========================================================
# Módulo: utils/db.py
# Función: Capa de acceso a la base de datos SQLite.
#          Centraliza la conexión para que NINGUNA vista (route)
#          ejecute SQL directamente. Las vistas llaman a los
#          modelos, y los modelos usan estas funciones.
# Funciones:
#   - get_connection() ... abre conexión con row_factory por nombre
#   - query(sql, params, one) ... SELECT (lista o un registro)
#   - execute(sql, params) ... INSERT/UPDATE/DELETE (devuelve lastrowid)
#   - init_db() ........... crea tablas y siembra datos iniciales
# Dependencias: sqlite3, os, config, werkzeug.security
# ===========================================================

import os
import sqlite3
from werkzeug.security import generate_password_hash

from config import Config, CONFIG_LABORAL_DEFAULT


def get_connection():
    """Abre una conexión a SQLite.
    row_factory=sqlite3.Row permite acceder a las columnas por nombre
    (fila["nombre"]) en lugar de por índice numérico."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # respetar llaves foráneas
    return conn


def query(sql, params=(), one=False):
    """Ejecuta un SELECT.
    - sql:    sentencia con marcadores '?'
    - params: tupla de parámetros (evita inyección SQL)
    - one:    True devuelve un solo registro; False devuelve lista
    Devuelve dict(s) para no acoplar el resto del código a sqlite3.Row."""
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        if one:
            fila = cur.fetchone()
            return dict(fila) if fila else None
        return [dict(f) for f in cur.fetchall()]
    finally:
        conn.close()


def execute(sql, params=()):
    """Ejecuta INSERT/UPDATE/DELETE y confirma la transacción.
    Devuelve el id de la última fila insertada (lastrowid)."""
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def init_db():
    """Crea el esquema completo de la base de datos si no existe
    y siembra el usuario administrador y la configuración laboral
    por defecto. Es idempotente: se puede llamar varias veces."""
    # Asegura que la carpeta /database exista
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)

    conn = get_connection()
    try:
        # ---- Tabla de usuarios del sistema (admin / supervisor) ----
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre        TEXT NOT NULL,
                correo        TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol           TEXT NOT NULL DEFAULT 'supervisor',  -- admin | supervisor
                activo        INTEGER NOT NULL DEFAULT 1,
                creado_en     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            -- ---- Trabajadores (la plantilla de personal) ----
            CREATE TABLE IF NOT EXISTS trabajadores (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                documento     TEXT UNIQUE NOT NULL,
                nombres       TEXT NOT NULL,
                apellidos     TEXT NOT NULL,
                cargo         TEXT,
                area          TEXT,
                turno         TEXT,
                foto          TEXT,                       -- nombre de archivo en /uploads/fotografias
                activo        INTEGER NOT NULL DEFAULT 1,
                creado_en     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            -- ---- Registros de asistencia (un registro por jornada) ----
            CREATE TABLE IF NOT EXISTS asistencia (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                trabajador_id  INTEGER NOT NULL,
                fecha          TEXT NOT NULL,              -- YYYY-MM-DD
                hora_entrada   TEXT,                       -- HH:MM
                hora_salida    TEXT,                       -- HH:MM
                observacion    TEXT,
                creado_en      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (trabajador_id) REFERENCES trabajadores(id) ON DELETE CASCADE
            );

            -- ---- Configuración laboral (clave/valor, totalmente editable) ----
            CREATE TABLE IF NOT EXISTS configuracion (
                clave  TEXT PRIMARY KEY,
                valor  TEXT NOT NULL
            );

            -- ---- Días festivos (parametrizables por el administrador) ----
            CREATE TABLE IF NOT EXISTS festivos (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha  TEXT UNIQUE NOT NULL,               -- YYYY-MM-DD
                nombre TEXT
            );

            -- ---- Turnos parametrizables ----
            CREATE TABLE IF NOT EXISTS turnos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre       TEXT UNIQUE NOT NULL,
                hora_inicio  TEXT NOT NULL,                -- HH:MM
                hora_fin     TEXT NOT NULL                 -- HH:MM
            );

            -- ---- Sitios de obra (estaciones + patio taller) ----
            -- Cada sitio es un punto con su propio radio. El trabajador
            -- puede marcar si está dentro de CUALQUIER sitio activo.
            CREATE TABLE IF NOT EXISTS sitios (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre    TEXT UNIQUE NOT NULL,
                latitud   TEXT NOT NULL,
                longitud  TEXT NOT NULL,
                radio_m   TEXT NOT NULL DEFAULT '300',
                activo    INTEGER NOT NULL DEFAULT 1
            );

            -- ---- Auditoría (trazabilidad de acciones) ----
            CREATE TABLE IF NOT EXISTS auditoria (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario    TEXT,
                accion     TEXT NOT NULL,
                detalle    TEXT,
                ip         TEXT,
                fecha      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );
            """
        )

        # ---- Sembrar configuración laboral por defecto ----
        for clave, valor in CONFIG_LABORAL_DEFAULT.items():
            conn.execute(
                "INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)",
                (clave, valor),
            )

        # ---- Sembrar usuario administrador inicial ----
        # IMPORTANTE: se verifica si existe ALGÚN administrador activo,
        # no un correo específico. Antes se buscaba 'admin@empresa.com';
        # si el administrador cambiaba su correo, en el siguiente arranque
        # se volvía a crear un admin con la contraseña por defecto
        # (una puerta trasera involuntaria). Corregido.
        existe_admin = conn.execute(
            "SELECT 1 FROM usuarios WHERE rol = 'admin' AND activo = 1 LIMIT 1"
        ).fetchone()
        if not existe_admin:
            conn.execute(
                """INSERT INTO usuarios (nombre, correo, password_hash, rol)
                   VALUES (?, ?, ?, 'admin')""",
                ("Administrador", "admin@empresa.com",
                 generate_password_hash("admin123")),
            )

        # -------------------------------------------------------
        # MIGRACIÓN: columnas nuevas para el kiosko de marcación.
        # Se agregan solo si no existen, sin borrar datos previos.
        # Cada marcaje (entrada y salida) guarda foto y coordenadas.
        # -------------------------------------------------------
        columnas_asistencia = [
            ("foto_entrada", "TEXT"),   # archivo de foto en la entrada
            ("foto_salida", "TEXT"),    # archivo de foto en la salida
            ("lat_entrada", "TEXT"),    # latitud al marcar entrada
            ("lon_entrada", "TEXT"),    # longitud al marcar entrada
            ("lat_salida", "TEXT"),     # latitud al marcar salida
            ("lon_salida", "TEXT"),     # longitud al marcar salida
            ("sitio_entrada", "TEXT"),  # nombre del sitio donde marcó entrada
            ("sitio_salida", "TEXT"),   # nombre del sitio donde marcó salida
        ]
        existentes = [
            r[1] for r in conn.execute("PRAGMA table_info(asistencia)").fetchall()
        ]
        for nombre_col, tipo in columnas_asistencia:
            if nombre_col not in existentes:
                conn.execute(
                    f"ALTER TABLE asistencia ADD COLUMN {nombre_col} {tipo}"
                )

        # ---- Sembrar configuración de la geocerca (obra) ----
        # Valores de ejemplo (centro de Bogotá); el admin los ajusta.
        config_geocerca = {
            "obra_latitud": "4.6097",     # latitud del centro de la obra
            "obra_longitud": "-74.0817",  # longitud del centro de la obra
            "obra_radio_m": "150",        # radio permitido en metros
            "validar_ubicacion": "1",     # 1=exige estar dentro / 0=no valida
            "exigir_foto": "1",           # 1=foto obligatoria al marcar
        }
        for clave, valor in config_geocerca.items():
            conn.execute(
                "INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)",
                (clave, valor),
            )

        # -------------------------------------------------------
        # Sembrar los 17 sitios de la Línea 1 del Metro de Bogotá
        # (16 estaciones + patio taller).
        # IMPORTANTE: las coordenadas son APROXIMADAS, para arrancar.
        # El administrador DEBE verificar y ajustar cada una en campo
        # (Google Maps / Mapas Bogotá). Radio por defecto: 300 m.
        # Solo se siembran si la tabla está vacía (primer arranque).
        # -------------------------------------------------------
        hay_sitios = conn.execute("SELECT COUNT(*) FROM sitios").fetchone()[0]
        if hay_sitios == 0:
            sitios_l1 = [
                # (nombre, lat aprox, lon aprox)
                ("01 Gibraltar",            "4.6283", "-74.1660"),
                ("02 Portal Américas",      "4.6278", "-74.1635"),
                ("03 Carrera 80",           "4.6258", "-74.1548"),
                ("04 Calle 42 Sur",         "4.6205", "-74.1497"),
                ("05 Hospital de Kennedy",  "4.6172", "-74.1455"),
                ("06 Avenida Boyacá",       "4.6122", "-74.1398"),
                ("07 Avenida Carrera 68",   "4.6082", "-74.1300"),
                ("08 Puente Aranda",        "4.6051", "-74.1182"),
                ("09 SENA",                 "4.6030", "-74.1100"),
                ("10 Avenida Carrera 24",   "4.6001", "-74.0982"),
                ("11 Hospital HOMI",        "4.5985", "-74.0902"),
                ("12 Avenida Jiménez",      "4.6022", "-74.0752"),
                ("13 Central",              "4.6092", "-74.0722"),
                ("14 Calle 45",            "4.6322", "-74.0692"),
                ("15 Calle 63",            "4.6482", "-74.0652"),
                ("16 Calle 72",            "4.6582", "-74.0632"),
                ("17 Patio Taller (Bosa)", "4.6205", "-74.1900"),
            ]
            for nombre, lat, lon in sitios_l1:
                conn.execute(
                    """INSERT INTO sitios (nombre, latitud, longitud, radio_m, activo)
                       VALUES (?, ?, ?, '300', 1)""",
                    (nombre, lat, lon),
                )

        conn.commit()
    finally:
        conn.close()
