# ===========================================================
# Módulo: services/calculo_horas.py
# Función: Lógica de negocio para clasificar las horas trabajadas
#          según la legislación laboral colombiana vigente.
#
#          - Jornada ordinaria semanal: parametrizable (por defecto 42h).
#          - Las horas que superan el tope semanal se clasifican como
#            HORAS EXTRAS automáticamente.
#          - Se separan porciones diurnas y nocturnas.
#          - Se marca trabajo en domingo o día festivo.
#
#          Los porcentajes de recargo y el valor hora se leen de la
#          tabla de configuración (editables desde el panel admin).
#
# Funciones:
#   - _a_minutos(hhmm) ............ "HH:MM" -> minutos desde medianoche
#   - _minutos_trabajados(...) .... duración bruta de un turno
#   - _minutos_nocturnos(...) ..... porción nocturna del turno
#   - calcular_registro(...) ...... clasifica UN registro de jornada
#   - resumen_semanal(...) ........ agrega y aplica el tope de 42h
#
# Dependencias: datetime, models.configuracion
# ===========================================================

from datetime import datetime


def _a_minutos(hhmm):
    """Convierte 'HH:MM' a minutos desde la medianoche. None -> None."""
    if not hhmm:
        return None
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _minutos_trabajados(entrada, salida, minutos_almuerzo):
    """Duración neta del turno en minutos (descontando el almuerzo).
    Si la salida es menor que la entrada se asume cruce de medianoche
    (turno nocturno) y se suman 24 horas."""
    ent = _a_minutos(entrada)
    sal = _a_minutos(salida)
    if ent is None or sal is None:
        return 0
    if sal < ent:           # cruzó medianoche
        sal += 24 * 60
    bruto = sal - ent
    neto = bruto - int(minutos_almuerzo)
    return max(neto, 0)


def _minutos_nocturnos(entrada, salida, inicio_noct, fin_noct):
    """Calcula cuántos minutos del turno caen en el horario nocturno.
    El horario nocturno suele cruzar la medianoche (p.ej. 21:00 a 06:00),
    por eso se evalúa minuto a minuto sobre una línea de 48 horas para
    cubrir turnos que también cruzan medianoche."""
    ent = _a_minutos(entrada)
    sal = _a_minutos(salida)
    if ent is None or sal is None:
        return 0
    if sal < ent:
        sal += 24 * 60

    ini_n = _a_minutos(inicio_noct)   # p.ej. 21:00 -> 1260
    fin_n = _a_minutos(fin_noct)      # p.ej. 06:00 -> 360

    nocturnos = 0
    # Recorremos cada minuto trabajado y verificamos si es nocturno.
    for minuto in range(ent, sal):
        h = minuto % (24 * 60)        # normaliza al día (0..1439)
        # Nocturno si: minuto >= inicio_nocturno  OR  minuto < fin_nocturno
        if h >= ini_n or h < fin_n:
            nocturnos += 1
    return nocturnos


def calcular_registro(registro, config, es_dom_fes):
    """Clasifica un registro individual de jornada.

    Parámetros:
      - registro: dict con 'hora_entrada' y 'hora_salida'
      - config:   dict de configuración (clave/valor en texto)
      - es_dom_fes: True si la fecha es domingo o festivo

    Devuelve un dict con horas (en horas decimales):
      total, diurnas, nocturnas, dominical_festivo (bool)
    """
    minutos_almuerzo = int(config.get("minutos_almuerzo", 60))
    total_min = _minutos_trabajados(
        registro.get("hora_entrada"), registro.get("hora_salida"), minutos_almuerzo
    )
    noct_min = _minutos_nocturnos(
        registro.get("hora_entrada"), registro.get("hora_salida"),
        config.get("inicio_nocturno", "21:00"), config.get("fin_nocturno", "06:00"),
    )
    # El almuerzo se descuenta del total; lo restamos proporcionalmente
    # de la porción diurna (criterio simple y transparente).
    noct_min = min(noct_min, total_min)
    diurno_min = max(total_min - noct_min, 0)

    return {
        "total": round(total_min / 60, 2),
        "diurnas": round(diurno_min / 60, 2),
        "nocturnas": round(noct_min / 60, 2),
        "dominical_festivo": bool(es_dom_fes),
    }


def resumen_semanal(registros_calculados, config):
    """Aplica el tope de jornada ordinaria semanal y clasifica el
    excedente como horas extras.

    Parámetros:
      - registros_calculados: lista de dicts devueltos por calcular_registro
      - config: dict de configuración

    Devuelve un dict con:
      horas_totales, horas_ordinarias, horas_extras,
      horas_nocturnas, horas_dominical_festivo,
      y una estimación de valor a pagar (informativa).
    """
    tope = float(config.get("horas_semanales", 42))

    horas_totales = round(sum(r["total"] for r in registros_calculados), 2)
    horas_nocturnas = round(sum(r["nocturnas"] for r in registros_calculados), 2)
    horas_dom_fes = round(
        sum(r["total"] for r in registros_calculados if r["dominical_festivo"]), 2
    )

    # Tope semanal: lo que pase de 'tope' son extras.
    horas_ordinarias = min(horas_totales, tope)
    horas_extras = round(max(horas_totales - tope, 0), 2)

    # --- Estimación informativa de valor (editable por configuración) ---
    valor_hora = float(config.get("valor_hora_ordinaria", 0))
    rec_extra_diurna = float(config.get("recargo_extra_diurna", 25)) / 100
    rec_nocturno = float(config.get("recargo_nocturno", 35)) / 100
    rec_dominical = float(config.get("recargo_dominical", 75)) / 100

    valor_ordinarias = horas_ordinarias * valor_hora
    valor_extras = horas_extras * valor_hora * (1 + rec_extra_diurna)
    valor_recargo_nocturno = horas_nocturnas * valor_hora * rec_nocturno
    valor_recargo_dominical = horas_dom_fes * valor_hora * rec_dominical

    total_estimado = round(
        valor_ordinarias + valor_extras
        + valor_recargo_nocturno + valor_recargo_dominical, 0
    )

    return {
        "horas_totales": horas_totales,
        "horas_ordinarias": round(horas_ordinarias, 2),
        "horas_extras": horas_extras,
        "horas_nocturnas": horas_nocturnas,
        "horas_dominical_festivo": horas_dom_fes,
        "valor_estimado": total_estimado,
    }


def dia_semana(fecha_str):
    """Devuelve el día de la semana (1=Lunes ... 7=Domingo) de 'YYYY-MM-DD'."""
    return datetime.strptime(fecha_str, "%Y-%m-%d").isoweekday()
