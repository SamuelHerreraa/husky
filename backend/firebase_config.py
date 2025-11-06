import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore
import sys
import os

# ==========================
# Config de Firebase (Pyrebase)
# ==========================
config = {
    "apiKey": "AIzaSyAZoYKWc92Rwf-AHcCv9w0bnzFcitmqXNo",
    "authDomain": "husky-licensing.firebaseapp.com",
    "databaseURL": "https://husky-licensing-default-rtdb.firebaseio.com/",
    "projectId": "husky-licensing",
    "storageBucket": "husky-licensing.firebasestorage.app",
    "messagingSenderId": "584612478585",
    "appId": "1:584612478585:web:61bbea7528f9c4f0d79ea8"
}

firebase_client = pyrebase.initialize_app(config)
auth_client = firebase_client.auth()

# ==========================
# Resolver base_path (normal o .exe)
# ==========================
if getattr(sys, "frozen", False):
    base_path = sys._MEIPASS
else:
    base_path = "."

# ==========================
# Inicializar Firebase Admin
# ==========================
cred_path = os.path.join(base_path, "firebase_credentials.json")
if not os.path.exists(cred_path):
    raise FileNotFoundError("No se encontró firebase_credentials.json")

# evitar doble init si importas en otro lado
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================
# Device ID único por PC
# ==========================
import hashlib
import uuid
DEVICE_ID = hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]