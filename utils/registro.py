# ===========================================================
# Módulo: utils/registro.py
# Función: Registrar acciones en la tabla de auditoría y en el
#          archivo de log del sistema.
# Funciones:
#   - auditar(accion, detalle) ... guarda traza en BD
#   - get_logger() ............... logger configurado a /logs
# Dependencias: logging, os, flask, config, utils.db
# ===========================================================

import os
import logging
from flask import session, request

from config import Config
from utils.db import execute

_logger = None


def get_logger():
    """Devuelve (y crea una sola vez) un logger que escribe en
    /logs/sistema.log con rotación simple por nivel INFO."""
    global _logger
    if _logger is None:
        os.makedirs(Config.LOG_FOLDER, exist_ok=True)
        _logger = logging.getLogger("control_asistencia")
        _logger.setLevel(logging.INFO)
        if not _logger.handlers:
            manejador = logging.FileHandler(
                os.path.join(Config.LOG_FOLDER, "sistema.log"), encoding="utf-8"
            )
            formato = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s"
            )
            manejador.setFormatter(formato)
            _logger.addHandler(manejador)
    return _logger


def auditar(accion, detalle=""):
    """Inserta una traza en la tabla de auditoría usando el usuario
    en sesión y la IP de la petición. También escribe en el log."""
    usuario = session.get("nombre", "anónimo")
    ip = request.remote_addr if request else "-"
    execute(
        "INSERT INTO auditoria (usuario, accion, detalle, ip) VALUES (?, ?, ?, ?)",
        (usuario, accion, detalle, ip),
    )
    get_logger().info("%s | %s | %s", usuario, accion, detalle)
