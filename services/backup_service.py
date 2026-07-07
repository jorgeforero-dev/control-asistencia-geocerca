# ===========================================================
# Módulo: services/backup_service.py
# Función: Crear copias de seguridad del archivo SQLite en /backups.
# Funciones:
#   - crear_backup() -> ruta del respaldo generado
# Dependencias: shutil, os, datetime, config
# ===========================================================

import os
import shutil
from datetime import datetime

from config import Config


def crear_backup():
    """Copia la base de datos a /backups con sello de fecha y hora.
    Devuelve la ruta del respaldo o None si la BD aún no existe."""
    if not os.path.exists(Config.DATABASE_PATH):
        return None
    os.makedirs(Config.BACKUP_FOLDER, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(Config.BACKUP_FOLDER, f"asistencia_{sello}.db")
    shutil.copy2(Config.DATABASE_PATH, destino)
    return destino
