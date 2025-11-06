# Husky Licensing Desktop

Aplicación de escritorio (Tkinter + ttkbootstrap) que:

- Autentica usuarios contra **Firebase Authentication**.
- Valida la licencia del usuario en **Firestore**.
- Bloquea el login si la licencia está **inactiva** o **expirada**.
- Amarra la licencia a **un solo dispositivo** usando un `device_id` basado en el MAC.
- Incluye una herramienta de administración (`admin_tool.py`) para ver usuarios y extender días de licencia.
- Migra fechas de expiración antiguas (guardadas como string) a **Timestamp**.

## Requisitos

- Python 3.10+
- Archivo `firebase_credentials.json` en la raíz del proyecto (NO se sube al repo).
- Proyecto de Firebase configurado (Auth + Firestore).

## Cómo correr

```bash
pip install -r requirements.txt
python frontend/main.py
