# backend/auth.py
from .utils import parse_pyrebase_error
from .firebase_config import auth_client

def do_login(email: str, password: str) -> dict:
    if not email or not password:
        raise ValueError("Please enter email and password.")

    try:
        user = auth_client.sign_in_with_email_and_password(email, password)
        return {
            "email": user["email"],
            "uid": user["localId"],
        }
    except Exception as e:
        firebase_msg = parse_pyrebase_error(e).lower()

        if ("invalid_email" in firebase_msg or "auth/invalid-email" in firebase_msg):
            raise ValueError("The email address is not valid.")
        elif (
            "invalid_login_credentials" in firebase_msg
            or "invalid_password" in firebase_msg
            or "wrong_password" in firebase_msg
            or "auth/wrong-password" in firebase_msg
        ):
            raise ValueError("Incorrect email or password.")
        elif ("user_not_found" in firebase_msg or "auth/user-not-found" in firebase_msg):
            raise ValueError("User not found.")
        else:
            raise ValueError("Unexpected error. Please try again or contact support.")
