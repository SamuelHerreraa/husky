# backend/license.py
from datetime import datetime, timezone
from firebase_admin import firestore
from .firebase_config import db, DEVICE_ID
from .utils import parse_expiration_date


def check_license(user_email: str, uid: str):
    """
    Valida la licencia del usuario en Firestore.

    Nuevo comportamiento:
    - Si está expirada, el usuario pasa a estado "pending",
      se borra expiration_date y se libera el device_id.
    - Así queda como un usuario nuevo sin licencia.
    """
    doc_ref = db.collection('users').document(user_email)
    doc = doc_ref.get()

    if not doc.exists:
        # no hay doc → no hay licencia
        raise ValueError("No license. Please contact the admin.")

    data = doc.to_dict() or {}
    status = data.get("status", "pending")
    exp_field = data.get("expiration_date")
    device_id_doc = data.get("device_id", "")

    if not exp_field:
        # no tiene fecha, lo tratamos como sin licencia
        # nos aseguramos de que quede pending y sin device
        doc_ref.update({
            "status": "pending",
            "device_id": "",
            "expiration_date": firestore.DELETE_FIELD
        })
        raise ValueError("No license. Please contact the admin.")

    # normalizar fecha
    if isinstance(exp_field, str):
        exp_date = parse_expiration_date(exp_field)  # ya regresa en UTC
        exp_ts = firestore.Timestamp.from_datetime(exp_date)
        doc_ref.update({"expiration_date": exp_ts})
    else:
        if hasattr(exp_field, "to_datetime"):
            exp_date = exp_field.to_datetime()
        else:
            exp_date = exp_field

        if exp_date.tzinfo is None:
            exp_date = exp_date.replace(tzinfo=timezone.utc)
        else:
            exp_date = exp_date.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)

    # ⬇️ aquí está el cambio importante
    if now >= exp_date:
        # licencia vencida → lo regresamos a "pending" y limpiamos
        doc_ref.update({
            "status": "pending",
            "device_id": "",
            "expiration_date": firestore.DELETE_FIELD
        })
        raise ValueError("License expired. Please contact the admin.")

    # si la fecha está bien pero el status no es active, lo bloqueamos
    if status != "active":
        raise ValueError("No license. Please contact the admin.")

    # validar device
    if device_id_doc == DEVICE_ID:
        return {"valid": True, "exp_date": exp_date}
    elif device_id_doc != "" and device_id_doc != DEVICE_ID:
        raise ValueError("This license is already in use on another computer.")
    else:
        # estaba libre → lo reclamamos
        doc_ref.update({"device_id": DEVICE_ID})
        return {"valid": True, "exp_date": exp_date}
