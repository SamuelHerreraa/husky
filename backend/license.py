# backend/license.py
from datetime import datetime, timezone
from firebase_admin import firestore
from .firebase_config import db, DEVICE_ID
from .utils import parse_expiration_date


def check_license(user_email: str, uid: str):
    """
    Valida la licencia del usuario en Firestore.
    - Si viene expiration_date como string, la migra a Timestamp.
    - Si está expirada, marca status='inactive' PERO NO toca device_id.
    - Valida que status sea 'active'.
    - Valida que el device_id sea el mismo o esté vacío.
    """
    doc_ref = db.collection('users').document(user_email)
    doc = doc_ref.get()

    if not doc.exists:
        raise ValueError("No hay licencia activa para este usuario.")

    data = doc.to_dict() or {}
    status = data.get("status", "inactive")
    exp_field = data.get("expiration_date")
    device_id_doc = data.get("device_id", "")

    if not exp_field:
        # no hay fecha -> solo marcamos inactivo
        doc_ref.update({"status": "inactive"})
        raise ValueError("No hay licencia activa para este usuario.")

    # ---- normalizar fecha ----
    if isinstance(exp_field, str):
        # string viejo -> lo convertimos y la guardamos como Timestamp
        exp_date = parse_expiration_date(exp_field)  # ya viene en UTC
        exp_ts = firestore.Timestamp.from_datetime(exp_date)
        # ojo: SOLO actualizamos expiration_date
        doc_ref.update({"expiration_date": exp_ts})
    else:
        # Timestamp o datetime
        if hasattr(exp_field, "to_datetime"):
            exp_date = exp_field.to_datetime()
        else:
            exp_date = exp_field

        # asegurar tz
        if exp_date.tzinfo is None:
            exp_date = exp_date.replace(tzinfo=timezone.utc)
        else:
            exp_date = exp_date.astimezone(timezone.utc)

    # ---- revisar expiración ----
    now = datetime.now(timezone.utc)
    if now >= exp_date:
        # SOLO cambiamos status, NO tocamos device_id
        doc_ref.update({"status": "inactive"})
        raise ValueError("No hay licencia activa para este usuario.")

    # ---- revisar status manual ----
    if status != "active":
        raise ValueError("No hay licencia activa para este usuario.")

    # ---- revisar device ----
    if device_id_doc == DEVICE_ID:
        # ok
        return {"valid": True, "exp_date": exp_date}
    elif device_id_doc != "" and device_id_doc != DEVICE_ID:
        # ya está usado en otra PC
        raise ValueError("No hay licencia activa para este usuario.")
    else:
        # estaba vacío -> lo ocupamos
        doc_ref.update({"device_id": DEVICE_ID})
        return {"valid": True, "exp_date": exp_date}
