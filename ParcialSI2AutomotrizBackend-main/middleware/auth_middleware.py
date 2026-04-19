from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from utils.jwt_utils import verificar_token

security = HTTPBearer()


async def verificar_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependencia de FastAPI que verifica el JWT del header Authorization.
    Valida que el token sea válido y no haya expirado.
    Retorna el payload del token con info del usuario.
    """
    token = credentials.credentials
    payload = verificar_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    # Agregar el token al payload para uso en logout
    payload["token"] = token
    return payload

