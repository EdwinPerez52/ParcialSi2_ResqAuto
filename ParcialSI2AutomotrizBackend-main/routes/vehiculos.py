from fastapi import APIRouter, HTTPException, Depends
from psycopg2.extras import RealDictCursor
from models.schemas import VehiculoRequest, VehiculoUpdateRequest
from config.database import get_db
from middleware.auth_middleware import verificar_auth
from utils.bitacora_utils import registrar_bitacora
from routes.auth import normalizar_rol

router = APIRouter(prefix="/api", tags=["Vehículos"])


# ==========================================
# CU-05: Registrar / Gestionar Vehículos
# ==========================================

@router.post("/vehiculos")
def registrar_vehiculo(datos: VehiculoRequest, usuario: dict = Depends(verificar_auth), conn = Depends(get_db)):
    """Registrar un nuevo vehículo (solo conductores)."""
    if normalizar_rol(usuario.get('rol','')) != 'conductor':
        raise HTTPException(status_code=403, detail="Solo conductores pueden registrar vehículos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Obtener conductor_id del usuario
        cursor.execute(
            "SELECT id FROM conductor WHERE usuario_id = %s",
            (usuario['user_id'],)
        )
        conductor = cursor.fetchone()
        if not conductor:
            raise HTTPException(status_code=404, detail="Perfil de conductor no encontrado")

        # Verificar que la placa no exista
        cursor.execute("SELECT placa FROM vehiculo WHERE placa = %s", (datos.placa,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="La placa ya está registrada")

        cursor.execute("""
            INSERT INTO vehiculo (placa, marca, modelo, anio, color, conductor_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (datos.placa, datos.marca, datos.modelo, datos.anio, datos.color, conductor['id']))

        conn.commit()
        cursor.close()

        registrar_bitacora(usuario['user_id'], f'Registro de vehículo {datos.placa}', 'vehiculo')

        return {"mensaje": "Vehículo registrado exitosamente", "placa": datos.placa}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vehiculos")
def listar_vehiculos(usuario: dict = Depends(verificar_auth), conn = Depends(get_db)):
    """Listar vehículos del conductor autenticado, o todos si es admin."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if normalizar_rol(usuario.get('rol','')) == 'conductor':
        cursor.execute(
            "SELECT id FROM conductor WHERE usuario_id = %s",
            (usuario['user_id'],)
        )
        conductor = cursor.fetchone()
        if not conductor:
            return {"vehiculos": []}
        cursor.execute(
            "SELECT * FROM vehiculo WHERE conductor_id = %s",
            (conductor['id'],)
        )
    else:
        cursor.execute("SELECT * FROM vehiculo")

    vehiculos = cursor.fetchall()
    cursor.close()

    return {"vehiculos": vehiculos}


@router.put("/vehiculos/{placa}")
def actualizar_vehiculo(
    placa: str,
    datos: VehiculoUpdateRequest,
    usuario: dict = Depends(verificar_auth),
    conn = Depends(get_db)
):
    """Actualizar datos de un vehículo existente."""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Construir query dinámico
        updates = []
        values = []
        if datos.marca is not None:
            updates.append("marca = %s")
            values.append(datos.marca)
        if datos.modelo is not None:
            updates.append("modelo = %s")
            values.append(datos.modelo)
        if datos.anio is not None:
            updates.append("anio = %s")
            values.append(datos.anio)
        if datos.color is not None:
            updates.append("color = %s")
            values.append(datos.color)

        if not updates:
            raise HTTPException(status_code=400, detail="No hay campos para actualizar")

        values.append(placa)
        query = f"UPDATE vehiculo SET {', '.join(updates)} WHERE placa = %s"
        cursor.execute(query, values)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        conn.commit()
        cursor.close()

        registrar_bitacora(usuario['user_id'], f'Actualización de vehículo {placa}', 'vehiculo')

        return {"mensaje": "Vehículo actualizado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vehiculos/{placa}")
def eliminar_vehiculo(placa: str, usuario: dict = Depends(verificar_auth), conn = Depends(get_db)):
    """Eliminar un vehículo por su placa."""
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vehiculo WHERE placa = %s", (placa,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        conn.commit()
        cursor.close()

        registrar_bitacora(usuario['user_id'], f'Eliminación de vehículo {placa}', 'vehiculo')

        return {"mensaje": "Vehículo eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
