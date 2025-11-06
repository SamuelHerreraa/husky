from .firebase_config import auth_client
from .utils import parse_pyrebase_error

def do_login(email, password):
    """
    Intenta login con Firebase Auth.
    Retorna dict con user data si OK, o lanza Exception con msg clara.
    """
    if not email or not password:
        raise ValueError("Completa email y password")

    try:
        user = auth_client.sign_in_with_email_and_password(email, password)
        uid = user['localId']
        user_email = user['email']
        print(f"Debug Email: {user_email}")
        from .firebase_config import DEVICE_ID
        print(f"Debug Device ID: {DEVICE_ID}")
        return {'uid': uid, 'email': user_email}
    except Exception as e:
        firebase_msg = parse_pyrebase_error(e).lower()
        if ("invalid_email" in firebase_msg or "auth/invalid-email" in firebase_msg):
            raise ValueError("El email no es válido.")
        elif ("invalid_login_credentials" in firebase_msg or
              "invalid_password" in firebase_msg or
              "wrong_password" in firebase_msg or
              "auth/wrong-password" in firebase_msg):
            raise ValueError("Email o contraseña incorrectos.")
        elif ("user_not_found" in firebase_msg or "auth/user-not-found" in firebase_msg):
            raise ValueError("Usuario no encontrado.")
        else:
            raise ValueError("Error inesperado. Intenta de nuevo o contacta soporte.")