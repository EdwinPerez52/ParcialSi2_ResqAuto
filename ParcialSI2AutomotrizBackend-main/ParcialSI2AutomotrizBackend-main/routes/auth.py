from fastapi import APIRouter, HTTPException, Depends
import bcrypt
import secrets
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from models.schemas import (
    LoginRequest, RegistroUsuarioRequest,
    RecuperarPasswordRequest, ResetPasswordRequest
)
from config.database import obtener_conexion
from utils.jwt_utils import crear_token
from utils.bitacora_utils import registrar_bitacora
from middleware.auth_middleware import verificar_auth

router = APIRouter(prefix="/api", tags=["Autenticación"])

# Mapeo de nombres de rol de BD a identificadores internos
ROL_MAP = {
    'Conductor': 'conductor',
    'Administrador de Taller': 'administrador_taller',
    'Técnico': 'tecnico',
    # fallback for already-normalized values
    'conductor': 'conductor',
    'administrador_taller': 'administrador_taller',
    'tecnico': 'tecnico',
}

ROL_MAP_REVERSE = {
    'conductor': 'Conductor',
    'administrador_taller': 'Administrador de Taller',
    'tecnico': 'Técnico',
}

def normalizar_rol(rol_bd: str) -> str:
    """Convierte nombre de rol de BD a identificador interno."""
    return ROL_MAP.get(rol_bd, rol_bd.lower())


# ==========================================
# CU-01: Iniciar Sesión
# ==========================================
@router.post("/login")
def iniciar_sesion(datos: LoginRequest):
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Buscar usuario por correo
        cursor.execute("""
            SELECT u.id, u.correo, u.contrasena, r.nombre as rol, u.estado
            FROM usuario u
            JOIN rol r ON u.rol_id = r.id
            WHERE u.correo = %s
        """, (datos.correo,))

        usuario = cursor.fetchone()

        if not usuario:
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

        if usuario['estado'] != 'activo':
            raise HTTPException(status_code=403, detail="Cuenta desactivada")

        # Verificar contraseña con bcrypt
        if not bcrypt.checkpw(
            datos.contrasena.encode('utf-8'),
            usuario['contrasena'].encode('utf-8')
        ):
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

        # Normalizar rol
        rol_normalizado = normalizar_rol(usuario['rol'])

        # Obtener información extra según el rol
        extra_info = {}
        if rol_normalizado == 'conductor':
            cursor.execute(
                "SELECT id, nombrecompleto, telefono FROM conductor WHERE usuario_id = %s",
                (usuario['id'],)
            )
            data = cursor.fetchone()
            if data:
                extra_info = {
                    "conductor_id": data['id'],
                    "nombre": data['nombrecompleto'],
                    "telefono": data['telefono']
                }

        elif rol_normalizado == 'administrador_taller':
            cursor.execute(
                "SELECT id, nombrecomercial, nit, direccion FROM taller WHERE usuario_id = %s",
                (usuario['id'],)
            )
            data = cursor.fetchone()
            if data:
                extra_info = {
                    "taller_id": data['id'],
                    "nombre_comercial": data['nombrecomercial'],
                    "nit": data['nit'],
                    "direccion": data['direccion']
                }

        elif rol_normalizado == 'tecnico':
            cursor.execute("""
                SELECT t.id, t.nombrecompleto, t.estadisponible, t.taller_id,
                       ta.nombrecomercial as nombre_taller
                FROM tecnico t
                JOIN taller ta ON t.taller_id = ta.id
                WHERE t.usuario_id = %s
            """, (usuario['id'],))
            data = cursor.fetchone()
            if data:
                extra_info = {
                    "tecnico_id": data['id'],
                    "nombre": data['nombrecompleto'],
                    "disponible": data['estadisponible'],
                    "taller_id": data['taller_id'],
                    "nombre_taller": data['nombre_taller']
                }

        # Crear JWT (usar rol normalizado)
        token_data = {
            "user_id": usuario['id'],
            "correo": usuario['correo'],
            "rol": rol_normalizado
        }
        token = crear_token(token_data)

        # Guardar sesión en tabla sesion
        cursor.execute("""
            INSERT INTO sesion (usuario_id, token, fecha_inicio)
            VALUES (%s, %s, %s)
        """, (usuario['id'], token, datetime.now(timezone.utc)))
        conn.commit()
        cursor.close()

        # Registrar en bitácora
        registrar_bitacora(usuario['id'], 'Inicio de sesión', 'sesion')

        return {
            "mensaje": "Login exitoso",
            "token": token,
            "usuario": {
                "id": usuario['id'],
                "correo": usuario['correo'],
                "rol": rol_normalizado,
                **extra_info
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ==========================================
# CU-02: Registrar Usuario
# ==========================================
@router.post("/registro")
def registrar_usuario(datos: RegistroUsuarioRequest):
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar si el correo ya existe
        cursor.execute("SELECT id FROM usuario WHERE correo = %s", (datos.correo,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="El correo ya está registrado")

        # Obtener ID del rol (convertir a nombre de BD)
        rol_bd = ROL_MAP_REVERSE.get(datos.rol, datos.rol)
        cursor.execute("SELECT id FROM rol WHERE nombre = %s", (rol_bd,))
        rol = cursor.fetchone()
        if not rol:
            raise HTTPException(status_code=400, detail=f"Rol '{datos.rol}' no válido")

        # Encriptar contraseña con bcrypt
        hashed_password = bcrypt.hashpw(
            datos.contrasena.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Insertar usuario
        cursor.execute("""
            INSERT INTO usuario (correo, contrasena, estado, fecharegistro, rol_id)
            VALUES (%s, %s, 'activo', %s, %s)
            RETURNING id
        """, (datos.correo, hashed_password, datetime.now(timezone.utc), rol['id']))

        nuevo_usuario = cursor.fetchone()
        usuario_id = nuevo_usuario['id']

        # Crear registro según el rol
        if datos.rol == 'conductor':
            cursor.execute("""
                INSERT INTO conductor (nombrecompleto, telefono, usuario_id)
                VALUES (%s, %s, %s)
            """, (datos.nombre_completo, datos.telefono, usuario_id))

        elif datos.rol == 'administrador_taller':
            cursor.execute("""
                INSERT INTO taller (nombrecomercial, nit, direccion, usuario_id)
                VALUES (%s, %s, %s, %s)
            """, (
                datos.nombre_comercial or datos.nombre_completo,
                datos.nit,
                datos.direccion,
                usuario_id
            ))

        elif datos.rol == 'tecnico':
            if not datos.taller_id:
                raise HTTPException(
                    status_code=400,
                    detail="Se requiere taller_id para registrar técnicos"
                )
            cursor.execute("""
                INSERT INTO tecnico (nombrecompleto, estadisponible, usuario_id, taller_id)
                VALUES (%s, true, %s, %s)
            """, (datos.nombre_completo, usuario_id, datos.taller_id))

        conn.commit()
        cursor.close()

        registrar_bitacora(usuario_id, f'Registro de usuario ({datos.rol})', 'usuario')

        return {"mensaje": "Usuario registrado exitosamente", "usuario_id": usuario_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ==========================================
# CU-03: Recuperar Contraseña (Simulado)
# ==========================================
@router.post("/recuperar-password")
def recuperar_password(datos: RecuperarPasswordRequest):
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id FROM usuario WHERE correo = %s", (datos.correo,))
        usuario = cursor.fetchone()
        cursor.close()

        if not usuario:
            # No revelamos si el email existe o no (seguridad)
            return {
                "mensaje": "Si el correo existe, recibirás instrucciones para recuperar tu contraseña",
                "token_reset": None
            }

        # Generar token de recuperación simulado
        token_reset = secrets.token_hex(32)

        return {
            "mensaje": "Token de recuperación generado (simulado)",
            "token_reset": token_reset,
            "nota": "En producción, este token se enviaría por email"
        }
    finally:
        conn.close()


@router.post("/reset-password")
def reset_password(datos: ResetPasswordRequest):
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id FROM usuario WHERE correo = %s", (datos.correo,))
        usuario = cursor.fetchone()

        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Encriptar nueva contraseña
        hashed_password = bcrypt.hashpw(
            datos.nueva_contrasena.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        cursor.execute("""
            UPDATE usuario SET contrasena = %s WHERE correo = %s
        """, (hashed_password, datos.correo))

        conn.commit()
        cursor.close()

        registrar_bitacora(usuario['id'], 'Cambio de contraseña', 'usuario')

        return {"mensaje": "Contraseña actualizada exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ==========================================
# CU-04: Cerrar Sesión
# ==========================================
@router.post("/logout")
def cerrar_sesion(usuario: dict = Depends(verificar_auth)):
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sesion SET fecha_fin = %s
            WHERE token = %s AND fecha_fin IS NULL
        """, (datetime.now(timezone.utc), usuario['token']))
        conn.commit()
        cursor.close()

        registrar_bitacora(usuario['user_id'], 'Cierre de sesión', 'sesion')

        return {"mensaje": "Sesión cerrada exitosamente"}
    finally:
        conn.close()


# ==========================================
# Obtener Perfil del usuario autenticado
# ==========================================
@router.get("/perfil")
def obtener_perfil(usuario: dict = Depends(verificar_auth)):
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT u.id, u.correo, r.nombre as rol, u.estado, u.fecharegistro
            FROM usuario u
            JOIN rol r ON u.rol_id = r.id
            WHERE u.id = %s
        """, (usuario['user_id'],))

        perfil = cursor.fetchone()

        if not perfil:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Info extra según rol
        extra = {}
        rol_norm = normalizar_rol(perfil['rol'])
        if rol_norm == 'conductor':
            cursor.execute(
                "SELECT id, nombrecompleto, telefono FROM conductor WHERE usuario_id = %s",
                (perfil['id'],)
            )
            data = cursor.fetchone()
            if data:
                extra = {
                    "conductor_id": data['id'],
                    "nombre": data['nombrecompleto'],
                    "telefono": data['telefono']
                }

        elif rol_norm == 'administrador_taller':
            cursor.execute(
                "SELECT id, nombrecomercial, nit, direccion FROM taller WHERE usuario_id = %s",
                (perfil['id'],)
            )
            data = cursor.fetchone()
            if data:
                extra = {
                    "taller_id": data['id'],
                    "nombre_comercial": data['nombrecomercial'],
                    "nit": data['nit'],
                    "direccion": data['direccion']
                }

        elif rol_norm == 'tecnico':
            cursor.execute("""
                SELECT t.id, t.nombrecompleto, t.estadisponible, t.taller_id,
                       ta.nombrecomercial as nombre_taller
                FROM tecnico t
                JOIN taller ta ON t.taller_id = ta.id
                WHERE t.usuario_id = %s
            """, (perfil['id'],))
            data = cursor.fetchone()
            if data:
                extra = {
                    "tecnico_id": data['id'],
                    "nombre": data['nombrecompleto'],
                    "disponible": data['estadisponible'],
                    "taller_id": data['taller_id'],
                    "nombre_taller": data['nombre_taller']
                }

        cursor.close()

        return {
            "id": perfil['id'],
            "correo": perfil['correo'],
            "rol": rol_norm,
            "estado": perfil['estado'],
            "fecharegistro": str(perfil['fecharegistro']),
            **extra
        }
    finally:
        conn.close()
