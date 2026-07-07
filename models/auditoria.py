# ===========================================================
# Módulo: models/auditoria.py
# Función: Lectura de la tabla 'auditoria' (la escritura se hace
#          desde utils/registro.py).
# Dependencias: utils.db
# ===========================================================

from utils.db import query


def listar(limite=200):
    """Devuelve las últimas N trazas de auditoría, más recientes primero."""
    return query(
        "SELECT * FROM auditoria ORDER BY id DESC LIMIT ?",
        (limite,),
    )
