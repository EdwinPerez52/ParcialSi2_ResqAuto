import jwt
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv(override=True)

SECRET_KEY = os.getenv("JWT_SECRET", "resqauto_secret_key_2024")
ALGORITHM = "HS256"
EXPIRATION_HOURS = 24


def crear_token(data: dict) -> str:
    """Genera un JWT con los datos proporcionados y expiración de 24 horas."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token(token: str) -> dict:
    """Decodifica y valida un JWT. Retorna None si es inválido o expirado."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
