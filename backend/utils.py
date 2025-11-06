# backend/utils.py
from datetime import datetime, timedelta, timezone
import json
import re

def get_default_expiration():
    """
    Retorna un datetime en UTC a 30 días.
    Firestore lo guarda como Timestamp.
    """
    return datetime.now(timezone.utc) + timedelta(days=30)

def parse_expiration_date(date_str):
    # 1) intento directo YYYY-MM-DD HH:MM:SS
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # 2) intento con formato español
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    pattern = r'(\d{1,2})\s+de\s+([a-záéíóúüñ]+)\s+de\s+(\d{4}),\s+(\d{1,2}):(\d{2})\s+([ap]\.m\.)\s+UTC([+-]\d{1,2})'
    m = re.match(pattern, date_str.lower())
    if not m:
        raise ValueError(f"Formato no reconocido: {date_str}")

    dia, mes_str, ano, hora, minu, ampm, zona = m.groups()
    mes = meses.get(mes_str)
    if mes is None:
        raise ValueError(f"Mes no reconocido: {mes_str}")

    h = int(hora)
    if ampm == 'p.m.' and h != 12:
        h += 12
    elif ampm == 'a.m.' and h == 12:
        h = 0

    offset_h = int(zona)
    # fecha original en esa zona
    dt_local = datetime(int(ano), mes, int(dia), h, int(minu))
    # la llevamos a UTC restando el offset
    dt_utc = dt_local - timedelta(hours=offset_h)
    return dt_utc.replace(tzinfo=timezone.utc)

def parse_pyrebase_error(e: Exception) -> str:
    raw = str(e)
    if '{' in raw:
        try:
            json_part = raw[raw.index('{'):]
            data = json.loads(json_part)
            return data.get("error", {}).get("message", "")
        except Exception:
            return raw
    return raw
