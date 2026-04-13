from fastapi import APIRouter, HTTPException, Depends
import bcrypt
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from models.schemas import (
    EspecialidadAsignarRequest, TecnicoRequest,
    TecnicoUpdateRequest, DisponibilidadRequest
)
from config.database import obtener_conexion
from middleware.auth_middleware import verificar_auth
from utils.bitacora_utils import registrar_bitacora
from routes.auth import normalizar_rol

router = APIRouter(prefix="/api", tags=["Talleres y Técnicos"])


# ==========================================
# CU-06: Configurar Especialidad del Taller
# ==========================================

@router.get("/especialidades")
def listar_especialidades(usuario: dict = Depends(verificar_auth)):
    """Listar todas las especialidades disponibles."""
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM especialidad ORDER BY id")
        especialidades = cursor.fetchall()
        cursor.close()
        return {"especialidades": especialidades}
    finally:
        conn.close()


@router.get("/taller/{taller_id}/especialidades")
def obtener_especialidades_taller(taller_id: int, usuario: dict = Depends(verificar_auth)):
    """Obtener las especialidades configuradas para un taller."""
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT e.id, e.nombreservicio
            FROM especialidad e
            JOIN taller_especialidad te ON e.id = te.especialidad_id
            WHERE te.taller_id = %s
        """, (taller_id,))
        especialidades = cursor.fetchall()
        cursor.close()
        return {"taller_id": taller_id, "especialidades": especialidades}
    finally:
        conn.close()


@router.post("/taller/{taller_id}/especialidades")
def asignar_especialidades(
    taller_id: int,
    datos: EspecialidadAsignarRequest,
    usuario: dict = Depends(verificar_auth)
):
    """Asignar especialidades a un taller (reemplaza las anteriores)."""
    if normalizar_rol(usuario.get('rol','')) != 'administrador_taller':
        raise HTTPException(
            status_code=403,
            detail="Solo administradores de taller pueden configurar especialidades"
        )

    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor()

        # Eliminar especialidades anteriores
        cursor.execute(
            "DELETE FROM taller_especialidad WHERE taller_id = %s",
            (taller_id,)
        )

        # Insertar nuevas
        for esp_id in datos.especialidad_ids:
            cursor.execute(
                "INSERT INTO taller_especialidad (taller_id, especialidad_id) VALUES (%s, %s)",
                (taller_id, esp_id)
            )

        conn.commit()
        cursor.close()

        registrar_bitacora(
            usuario['user_id'],
            f'Configuración de especialidades para taller {taller_id}',
            'taller_especialidad'
        )

        return {"mensaje": "Especialidades actualizadas exitosamente"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ==========================================
# CU-07: Gestionar Personal Técnico
# ==========================================

@router.get("/taller/{taller_id}/tecnicos")
def obtener_tecnicos(taller_id: int, usuario: dict = Depends(verificar_auth)):
    """Listar técnicos de un taller."""
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT t.id, t.nombrecompleto, t.estadisponible, t.usuario_id,
                   u.correo
            FROM tecnico t
            JOIN usuario u ON t.usuario_id = u.id
            WHERE t.taller_id = %s
        """, (taller_id,))
        tecnicos = cursor.fetchall()
        cursor.close()
        return {"taller_id": taller_id, "tecnicos": tecnicos}
    finally:
        conn.close()


@router.post("/taller/{taller_id}/tecnicos")
def agregar_tecnico(
    taller_id: int,
    datos: TecnicoRequest,
    usuario: dict = Depends(verificar_auth)
):
    """Agregar un nuevo técnico al taller (crea usuario + técnico)."""
    if normalizar_rol(usuario.get('rol','')) != 'administrador_taller':
        raise HTTPException(
            status_code=403,
            detail="Solo administradores de taller pueden gestionar técnicos"
        )

    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar que el correo no exista
        cursor.execute("SELECT id FROM usuario WHERE correo = %s", (datos.correo,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="El correo ya está registrado")

        # Obtener rol de técnico
        cursor.execute("SELECT id FROM rol WHERE nombre = %s", ('Técnico',))
        rol = cursor.fetchone()
        if not rol:
            raise HTTPException(status_code=500, detail="Rol 'tecnico' no encontrado en BD")

        # Encriptar contraseña
        hashed = bcrypt.hashpw(
            datos.contrasena.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Crear cuenta de usuario
        cursor.execute("""
            INSERT INTO usuario (correo, contrasena, estado, fecharegistro, rol_id)
            VALUES (%s, %s, 'activo', %s, %s)
            RETURNING id
        """, (datos.correo, hashed, datetime.now(timezone.utc), rol['id']))
        nuevo_usuario = cursor.fetchone()

        # Crear registro de técnico
        cursor.execute("""
            INSERT INTO tecnico (nombrecompleto, estadisponible, usuario_id, taller_id)
            VALUES (%s, true, %s, %s)
            RETURNING id
        """, (datos.nombre_completo, nuevo_usuario['id'], taller_id))
        nuevo_tecnico = cursor.fetchone()

        conn.commit()
        cursor.close()

        registrar_bitacora(
            usuario['user_id'],
            f'Registro de técnico en taller {taller_id}',
            'tecnico'
        )

        return {
            "mensaje": "Técnico agregado exitosamente",
            "tecnico_id": nuevo_tecnico['id']
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.put("/taller/{taller_id}/tecnicos/{tecnico_id}")
def actualizar_tecnico(
    taller_id: int,
    tecnico_id: int,
    datos: TecnicoUpdateRequest,
    usuario: dict = Depends(verificar_auth)
):
    """Actualizar datos de un técnico."""
    if normalizar_rol(usuario.get('rol','')) != 'administrador_taller':
        raise HTTPException(
            status_code=403,
            detail="Solo administradores de taller pueden gestionar técnicos"
        )

    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor()

        if datos.nombre_completo:
            cursor.execute("""
                UPDATE tecnico SET nombrecompleto = %s
                WHERE id = %s AND taller_id = %s
            """, (datos.nombre_completo, tecnico_id, taller_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Técnico no encontrado en este taller")

        conn.commit()
        cursor.close()

        registrar_bitacora(
            usuario['user_id'],
            f'Actualización de técnico {tecnico_id}',
            'tecnico'
        )

        return {"mensaje": "Técnico actualizado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.delete("/taller/{taller_id}/tecnicos/{tecnico_id}")
def eliminar_tecnico(
    taller_id: int,
    tecnico_id: int,
    usuario: dict = Depends(verificar_auth)
):
    """Eliminar un técnico (desactiva su cuenta de usuario)."""
    if normalizar_rol(usuario.get('rol','')) != 'administrador_taller':
        raise HTTPException(
            status_code=403,
            detail="Solo administradores de taller pueden gestionar técnicos"
        )

    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Obtener usuario_id antes de eliminar
        cursor.execute(
            "SELECT usuario_id FROM tecnico WHERE id = %s AND taller_id = %s",
            (tecnico_id, taller_id)
        )
        tecnico = cursor.fetchone()
        if not tecnico:
            raise HTTPException(status_code=404, detail="Técnico no encontrado en este taller")

        # Eliminar técnico
        cursor.execute(
            "DELETE FROM tecnico WHERE id = %s AND taller_id = %s",
            (tecnico_id, taller_id)
        )

        # Desactivar cuenta de usuario
        cursor.execute(
            "UPDATE usuario SET estado = 'inactivo' WHERE id = %s",
            (tecnico['usuario_id'],)
        )

        conn.commit()
        cursor.close()

        registrar_bitacora(
            usuario['user_id'],
            f'Eliminación de técnico {tecnico_id}',
            'tecnico'
        )

        return {"mensaje": "Técnico eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ==========================================
# CU-08: Cambiar Estado de Disponibilidad
# ==========================================

@router.patch("/tecnicos/{tecnico_id}/disponibilidad")
def cambiar_disponibilidad(
    tecnico_id: int,
    datos: DisponibilidadRequest,
    usuario: dict = Depends(verificar_auth)
):
    """Cambiar el estado de disponibilidad de un técnico."""
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tecnico SET estadisponible = %s WHERE id = %s
        """, (datos.estadisponible, tecnico_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Técnico no encontrado")

        conn.commit()
        cursor.close()

        estado = "disponible" if datos.estadisponible else "no disponible"
        registrar_bitacora(
            usuario['user_id'],
            f'Cambio de disponibilidad técnico {tecnico_id} a {estado}',
            'tecnico'
        )

        return {"mensaje": f"Disponibilidad actualizada a {estado}"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
