from fastapi import APIRouter, HTTPException, Depends, Query
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from typing import Optional
from models.schemas import (
    SolicitudAuxilioRequest, AceptarEmergenciaRequest,
    RechazarEmergenciaRequest, ActualizarEstadoRescateRequest,
    CancelarSolicitudRequest, FinalizarServicioRequest,
    TallerUbicacionRequest
)
from config.database import get_db
from middleware.auth_middleware import verificar_auth
from utils.bitacora_utils import registrar_bitacora
from routes.auth import normalizar_rol
import math

router = APIRouter(prefix="/api", tags=["Emergencias"])

# Estados válidos y sus transiciones
TRANSICIONES_VALIDAS = {
    'Reportado': ['Asignado', 'Cancelado'],
    'Asignado': ['En camino', 'Reportado', 'Cancelado'],  # Reportado = rechazado/reasignado
    'En camino': ['En sitio'],
    'En sitio': ['En reparación'],
    'En reparación': ['Finalizado'],
}


def crear_notificacion(conn, usuario_id, titulo, mensaje, tipo, referencia_id=None):
    """Crea una notificación para un usuario."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notificacion (usuario_id, titulo, mensaje, tipo, referencia_id, fecha)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (usuario_id, titulo, mensaje, tipo, referencia_id, datetime.now(timezone.utc)))
    cursor.close()


def haversine(lat1, lon1, lat2, lon2):
    """Calcula distancia en km entre dos coordenadas."""
    R = 6371  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def buscar_taller_cercano(conn, latitud, longitud, excluir_taller_ids=None):
    """Busca el taller más cercano con técnicos disponibles."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    excluir_sql = ""
    params = []
    if excluir_taller_ids:
        placeholders = ','.join(['%s'] * len(excluir_taller_ids))
        excluir_sql = f"AND t.id NOT IN ({placeholders})"
        params = list(excluir_taller_ids)

    cursor.execute(f"""
        SELECT DISTINCT t.id, t.nombrecomercial, t.latitud, t.longitud, t.usuario_id
        FROM taller t
        JOIN tecnico tc ON tc.taller_id = t.id
        WHERE t.latitud IS NOT NULL
          AND t.longitud IS NOT NULL
          AND tc.estadisponible = TRUE
          {excluir_sql}
    """, params)

    talleres = cursor.fetchall()
    cursor.close()

    if not talleres:
        return None

    # Calcular distancias y ordenar
    for t in talleres:
        t['distancia_km'] = haversine(latitud, longitud, float(t['latitud']), float(t['longitud']))

    talleres.sort(key=lambda x: x['distancia_km'])
    return talleres[0]


# ==========================================
# CU-10: Solicitar Auxilio Vehicular
# CU-11: Capturar Ubicación Satelital
# CU-12: Filtrar y Asignar Taller Cercano
# ==========================================
@router.post("/emergencias/solicitar")
def solicitar_auxilio(datos: SolicitudAuxilioRequest, usuario: dict = Depends(verificar_auth), conn = Depends(get_db)):
    """Conductor solicita auxilio vehicular. Se captura ubicación y se asigna taller cercano."""
    if normalizar_rol(usuario.get('rol', '')) != 'conductor':
        raise HTTPException(status_code=403, detail="Solo conductores pueden solicitar auxilio")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar que el vehículo pertenece al conductor
        cursor.execute("""
            SELECT v.placa FROM vehiculo v
            JOIN conductor c ON v.conductor_id = c.id
            WHERE v.placa = %s AND c.usuario_id = %s
        """, (datos.vehiculo_placa, usuario['user_id']))

        if not cursor.fetchone():
            raise HTTPException(status_code=403, detail="Este vehículo no te pertenece")

        # Verificar que no tenga una emergencia activa con este vehículo
        cursor.execute("""
            SELECT id FROM incidente
            WHERE vehiculo_placa = %s AND estadoactual NOT IN ('Finalizado', 'Cancelado')
        """, (datos.vehiculo_placa,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Ya tienes una emergencia activa con este vehículo")

        # CU-10: Registrar incidente usando stored procedure
        cursor.execute(
            "SELECT registrar_nuevo_incidente(%s, %s, %s, %s, %s)",
            (datos.latitud, datos.longitud, datos.descripcion, datos.vehiculo_placa, usuario['user_id'])
        )
        incidente_id = cursor.fetchone()['registrar_nuevo_incidente']

        # CU-12: Buscar taller cercano automáticamente
        taller_cercano = buscar_taller_cercano(conn, datos.latitud, datos.longitud)

        resultado = {
            "mensaje": "Auxilio solicitado exitosamente",
            "incidente_id": incidente_id,
            "estado": "Reportado",
            "taller_asignado": None
        }

        if taller_cercano:
            # Asignar taller (estado pasa a 'Asignado', esperando aceptación)
            cursor.execute("""
                UPDATE incidente SET taller_id = %s, estadoactual = 'Asignado'
                WHERE id = %s
            """, (taller_cercano['id'], incidente_id))

            cursor.execute("""
                INSERT INTO historialincidente (incidente_id, estado_anterior, estado_nuevo, fecha_cambio)
                VALUES (%s, 'Reportado', 'Asignado', %s)
            """, (incidente_id, datetime.now(timezone.utc)))

            resultado["estado"] = "Asignado"
            resultado["taller_asignado"] = {
                "id": taller_cercano['id'],
                "nombre": taller_cercano['nombrecomercial'],
                "distancia_km": round(taller_cercano['distancia_km'], 2)
            }

            # CU-21: Notificar al admin del taller
            crear_notificacion(
                conn, taller_cercano['usuario_id'],
                '🚨 Nueva emergencia asignada',
                f'Se ha asignado una emergencia vehicular cerca de tu taller ({round(taller_cercano["distancia_km"], 1)} km)',
                'emergencia', incidente_id
            )

            # Notificar al conductor
            crear_notificacion(
                conn, usuario['user_id'],
                '✅ Taller asignado',
                f'Se asignó el taller "{taller_cercano["nombrecomercial"]}" a tu emergencia',
                'asignacion', incidente_id
            )

        conn.commit()
        cursor.close()
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# CU-13: Aceptar o Rechazar Alerta
# CU-14: Bloquear por Exclusividad
# ==========================================
@router.post("/emergencias/{incidente_id}/aceptar")
def aceptar_emergencia(
    incidente_id: int,
    datos: AceptarEmergenciaRequest,
    usuario: dict = Depends(verificar_auth),
    conn = Depends(get_db)
):
    """Admin taller acepta emergencia y asigna técnico."""
    if normalizar_rol(usuario.get('rol', '')) != 'administrador_taller':
        raise HTTPException(status_code=403, detail="Solo administradores de taller pueden aceptar emergencias")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar que el incidente está asignado a este taller
        cursor.execute("""
            SELECT i.id, i.estadoactual, i.taller_id, i.vehiculo_placa,
                   v.conductor_id, c.usuario_id as conductor_usuario_id
            FROM incidente i
            JOIN vehiculo v ON i.vehiculo_placa = v.placa
            JOIN conductor c ON v.conductor_id = c.id
            WHERE i.id = %s
        """, (incidente_id,))
        incidente = cursor.fetchone()

        if not incidente:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")

        taller_id = usuario.get('taller_id')
        if not taller_id:
            cursor.execute("SELECT id FROM taller WHERE usuario_id = %s", (usuario['user_id'],))
            taller_data = cursor.fetchone()
            taller_id = taller_data['id'] if taller_data else None

        if incidente['taller_id'] != taller_id:
            raise HTTPException(status_code=403, detail="Esta emergencia no está asignada a tu taller")

        if incidente['estadoactual'] != 'Asignado':
            raise HTTPException(status_code=400, detail=f"No se puede aceptar: estado actual es '{incidente['estadoactual']}'")

        # CU-14: Verificar que el técnico pertenece al taller y está disponible
        cursor.execute("""
            SELECT id, nombrecompleto FROM tecnico
            WHERE id = %s AND taller_id = %s AND estadisponible = TRUE
        """, (datos.tecnico_id, taller_id))
        tecnico = cursor.fetchone()

        if not tecnico:
            raise HTTPException(status_code=400, detail="Técnico no disponible o no pertenece a tu taller")

        # Usar stored procedure para asignar
        cursor.execute(
            "SELECT asignar_tecnico_incidente(%s, %s, %s, %s)",
            (incidente_id, taller_id, datos.tecnico_id, usuario['user_id'])
        )

        # CU-21: Notificar al conductor
        crear_notificacion(
            conn, incidente['conductor_usuario_id'],
            '🔧 Técnico en camino',
            f'El técnico "{tecnico["nombrecompleto"]}" va en camino a tu ubicación',
            'estado', incidente_id
        )

        # Notificar al técnico
        cursor.execute("SELECT usuario_id FROM tecnico WHERE id = %s", (datos.tecnico_id,))
        tecnico_usuario = cursor.fetchone()
        if tecnico_usuario:
            crear_notificacion(
                conn, tecnico_usuario['usuario_id'],
                '📋 Nueva asignación',
                f'Se te ha asignado la emergencia #{incidente_id}',
                'asignacion', incidente_id
            )

        conn.commit()
        cursor.close()

        return {
            "mensaje": "Emergencia aceptada, técnico asignado",
            "incidente_id": incidente_id,
            "tecnico": tecnico['nombrecompleto'],
            "estado": "En camino"
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/emergencias/{incidente_id}/rechazar")
def rechazar_emergencia(
    incidente_id: int,
    datos: RechazarEmergenciaRequest,
    usuario: dict = Depends(verificar_auth),
    conn = Depends(get_db)
):
    """Admin taller rechaza la emergencia. Se reasigna al siguiente taller más cercano."""
    if normalizar_rol(usuario.get('rol', '')) != 'administrador_taller':
        raise HTTPException(status_code=403, detail="Solo administradores de taller pueden rechazar")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT id, estadoactual, taller_id, latitud, longitud
            FROM incidente WHERE id = %s
        """, (incidente_id,))
        incidente = cursor.fetchone()

        if not incidente:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")
        if incidente['estadoactual'] != 'Asignado':
            raise HTTPException(status_code=400, detail="Solo se puede rechazar en estado 'Asignado'")

        taller_rechazado_id = incidente['taller_id']

        # CU-17: Buscar siguiente taller cercano (excluyendo el que rechazó)
        nuevo_taller = buscar_taller_cercano(
            conn, float(incidente['latitud']), float(incidente['longitud']),
            excluir_taller_ids=[taller_rechazado_id]
        )

        if nuevo_taller:
            cursor.execute("""
                UPDATE incidente SET taller_id = %s WHERE id = %s
            """, (nuevo_taller['id'], incidente_id))

            crear_notificacion(
                conn, nuevo_taller['usuario_id'],
                '🚨 Nueva emergencia asignada',
                f'Se ha reasignado una emergencia vehicular a tu taller ({round(nuevo_taller["distancia_km"], 1)} km)',
                'emergencia', incidente_id
            )

            resultado = {
                "mensaje": "Emergencia rechazada, reasignada a otro taller",
                "nuevo_taller": nuevo_taller['nombrecomercial']
            }
        else:
            # Sin talleres disponibles → volver a Reportado
            cursor.execute("""
                UPDATE incidente SET taller_id = NULL, estadoactual = 'Reportado' WHERE id = %s
            """, (incidente_id,))

            cursor.execute("""
                INSERT INTO historialincidente (incidente_id, estado_anterior, estado_nuevo, fecha_cambio)
                VALUES (%s, 'Asignado', 'Reportado', %s)
            """, (incidente_id, datetime.now(timezone.utc)))

            resultado = {
                "mensaje": "Emergencia rechazada. No hay talleres disponibles, se mantiene en espera",
                "nuevo_taller": None
            }

        conn.commit()
        cursor.close()
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# CU-15: Actualizar Estado del Rescate
# ==========================================
@router.patch("/emergencias/{incidente_id}/estado")
def actualizar_estado(
    incidente_id: int,
    datos: ActualizarEstadoRescateRequest,
    usuario: dict = Depends(verificar_auth),
    conn = Depends(get_db)
):
    """Técnico actualiza el estado del rescate."""
    rol = normalizar_rol(usuario.get('rol', ''))

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT i.id, i.estadoactual, i.tecnico_id, i.taller_id, i.vehiculo_placa,
                   v.conductor_id, c.usuario_id as conductor_usuario_id
            FROM incidente i
            JOIN vehiculo v ON i.vehiculo_placa = v.placa
            JOIN conductor c ON v.conductor_id = c.id
            WHERE i.id = %s
        """, (incidente_id,))
        incidente = cursor.fetchone()

        if not incidente:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")

        # Verificar permisos
        if rol == 'tecnico':
            cursor.execute("SELECT id FROM tecnico WHERE usuario_id = %s", (usuario['user_id'],))
            tecnico = cursor.fetchone()
            if not tecnico or tecnico['id'] != incidente['tecnico_id']:
                raise HTTPException(status_code=403, detail="No estás asignado a esta emergencia")

        estado_actual = incidente['estadoactual']
        nuevo_estado = datos.estado

        # Validar transición
        transiciones = TRANSICIONES_VALIDAS.get(estado_actual, [])
        if nuevo_estado not in transiciones:
            raise HTTPException(
                status_code=400,
                detail=f"Transición no válida: '{estado_actual}' → '{nuevo_estado}'. Permitidos: {transiciones}"
            )

        # Actualizar estado
        cursor.execute(
            "UPDATE incidente SET estadoactual = %s WHERE id = %s",
            (nuevo_estado, incidente_id)
        )

        # Registrar historial
        cursor.execute("""
            INSERT INTO historialincidente (incidente_id, estado_anterior, estado_nuevo, fecha_cambio)
            VALUES (%s, %s, %s, %s)
        """, (incidente_id, estado_actual, nuevo_estado, datetime.now(timezone.utc)))

        # Si finalizado, liberar técnico
        if nuevo_estado == 'Finalizado' and incidente['tecnico_id']:
            cursor.execute(
                "UPDATE tecnico SET estadisponible = TRUE WHERE id = %s",
                (incidente['tecnico_id'],)
            )

        # CU-21: Notificar al conductor
        emojis = {'En sitio': '📍', 'En reparación': '🔧', 'Finalizado': '✅'}
        crear_notificacion(
            conn, incidente['conductor_usuario_id'],
            f'{emojis.get(nuevo_estado, "📋")} Estado actualizado',
            f'Tu emergencia #{incidente_id} cambió a: {nuevo_estado}',
            'estado', incidente_id
        )

        # Notificar al admin del taller también
        if incidente['taller_id']:
            cursor.execute("SELECT usuario_id FROM taller WHERE id = %s", (incidente['taller_id'],))
            taller = cursor.fetchone()
            if taller:
                crear_notificacion(
                    conn, taller['usuario_id'],
                    f'{emojis.get(nuevo_estado, "📋")} Emergencia #{incidente_id}',
                    f'Estado actualizado a: {nuevo_estado}',
                    'estado', incidente_id
                )

        registrar_bitacora(usuario['user_id'], f'Cambio estado incidente #{incidente_id}: {estado_actual} → {nuevo_estado}', 'incidente')

        conn.commit()
        cursor.close()

        return {
            "mensaje": f"Estado actualizado a '{nuevo_estado}'",
            "incidente_id": incidente_id,
            "estado_anterior": estado_actual,
            "estado_nuevo": nuevo_estado
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# CU-16: Cancelar Solicitud de Auxilio
# ==========================================
@router.post("/emergencias/{incidente_id}/cancelar")
def cancelar_emergencia(
    incidente_id: int,
    datos: CancelarSolicitudRequest,
    usuario: dict = Depends(verificar_auth),
    conn = Depends(get_db)
):
    """Conductor cancela su solicitud de auxilio."""
    if normalizar_rol(usuario.get('rol', '')) != 'conductor':
        raise HTTPException(status_code=403, detail="Solo el conductor puede cancelar su solicitud")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT i.id, i.estadoactual, i.tecnico_id, i.taller_id, i.vehiculo_placa
            FROM incidente i
            JOIN vehiculo v ON i.vehiculo_placa = v.placa
            JOIN conductor c ON v.conductor_id = c.id
            WHERE i.id = %s AND c.usuario_id = %s
        """, (incidente_id, usuario['user_id']))
        incidente = cursor.fetchone()

        if not incidente:
            raise HTTPException(status_code=404, detail="Incidente no encontrado o no te pertenece")

        if incidente['estadoactual'] not in ('Reportado', 'Asignado'):
            raise HTTPException(
                status_code=400,
                detail=f"No se puede cancelar en estado '{incidente['estadoactual']}'. Solo en 'Reportado' o 'Asignado'"
            )

        # Liberar técnico si hay uno asignado
        if incidente['tecnico_id']:
            cursor.execute("UPDATE tecnico SET estadisponible = TRUE WHERE id = %s", (incidente['tecnico_id'],))

        # Cambiar estado
        cursor.execute(
            "UPDATE incidente SET estadoactual = 'Cancelado', tecnico_id = NULL WHERE id = %s",
            (incidente_id,)
        )

        cursor.execute("""
            INSERT INTO historialincidente (incidente_id, estado_anterior, estado_nuevo, fecha_cambio)
            VALUES (%s, %s, 'Cancelado', %s)
        """, (incidente_id, incidente['estadoactual'], datetime.now(timezone.utc)))

        # Notificar al taller si había uno asignado
        if incidente['taller_id']:
            cursor.execute("SELECT usuario_id FROM taller WHERE id = %s", (incidente['taller_id'],))
            taller = cursor.fetchone()
            if taller:
                crear_notificacion(
                    conn, taller['usuario_id'],
                    '❌ Emergencia cancelada',
                    f'El conductor canceló la emergencia #{incidente_id}',
                    'estado', incidente_id
                )

        registrar_bitacora(usuario['user_id'], f'Cancelación de emergencia #{incidente_id}', 'incidente')
        conn.commit()
        cursor.close()

        return {"mensaje": "Solicitud cancelada exitosamente", "incidente_id": incidente_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# CU-17: Reasignar emergencia por demora
# ==========================================
@router.post("/emergencias/{incidente_id}/reasignar")
def reasignar_emergencia(incidente_id: int, usuario: dict = Depends(verificar_auth), conn = Depends(get_db)):
    """Reasignar emergencia a otro taller (por demora o rechazo)."""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT id, estadoactual, taller_id, latitud, longitud FROM incidente WHERE id = %s
        """, (incidente_id,))
        incidente = cursor.fetchone()

        if not incidente:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")

        if incidente['estadoactual'] not in ('Asignado', 'Reportado'):
            raise HTTPException(status_code=400, detail="Solo se puede reasignar en estado 'Asignado' o 'Reportado'")

        excluir = [incidente['taller_id']] if incidente['taller_id'] else []
        nuevo_taller = buscar_taller_cercano(
            conn, float(incidente['latitud']), float(incidente['longitud']),
            excluir_taller_ids=excluir if excluir else None
        )

        if not nuevo_taller:
            return {"mensaje": "No hay talleres disponibles para reasignación", "nuevo_taller": None}

        cursor.execute("""
            UPDATE incidente SET taller_id = %s, estadoactual = 'Asignado' WHERE id = %s
        """, (nuevo_taller['id'], incidente_id))

        crear_notificacion(
            conn, nuevo_taller['usuario_id'],
            '🚨 Emergencia reasignada a tu taller',
            f'Se te ha reasignado la emergencia #{incidente_id}',
            'emergencia', incidente_id
        )

        conn.commit()
        cursor.close()

        return {
            "mensaje": "Emergencia reasignada",
            "nuevo_taller": nuevo_taller['nombrecomercial'],
            "distancia_km": round(nuevo_taller['distancia_km'], 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))



# ==========================================
# Consultas de Emergencias
# ==========================================
@router.get("/emergencias")
def listar_emergencias(
    estado: Optional[str] = None,
    pagina: int = 1,
    limite: int = 20,
    usuario: dict = Depends(verificar_auth),
    conn = Depends(get_db)
):
    """Listar emergencias según rol del usuario."""
    rol = normalizar_rol(usuario.get('rol', ''))

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        where_clauses = []
        params = []

        if rol == 'conductor':
            where_clauses.append("""
                i.vehiculo_placa IN (
                    SELECT v.placa FROM vehiculo v
                    JOIN conductor c ON v.conductor_id = c.id
                    WHERE c.usuario_id = %s
                )
            """)
            params.append(usuario['user_id'])
        elif rol == 'administrador_taller':
            cursor.execute("SELECT id FROM taller WHERE usuario_id = %s", (usuario['user_id'],))
            taller = cursor.fetchone()
            if taller:
                where_clauses.append("i.taller_id = %s")
                params.append(taller['id'])
        elif rol == 'tecnico':
            cursor.execute("SELECT id FROM tecnico WHERE usuario_id = %s", (usuario['user_id'],))
            tecnico = cursor.fetchone()
            if tecnico:
                where_clauses.append("i.tecnico_id = %s")
                params.append(tecnico['id'])

        if estado:
            where_clauses.append("i.estadoactual = %s")
            params.append(estado)

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Total count
        cursor.execute(f"SELECT COUNT(*) as total FROM incidente i {where_sql}", params)
        total = cursor.fetchone()['total']

        # Results
        offset = (pagina - 1) * limite
        cursor.execute(f"""
            SELECT i.id, i.fechahora, i.latitud, i.longitud, i.estadoactual,
                   i.descripcion, i.vehiculo_placa,
                   t.nombrecomercial as taller_nombre,
                   tc.nombrecompleto as tecnico_nombre
            FROM incidente i
            LEFT JOIN taller t ON i.taller_id = t.id
            LEFT JOIN tecnico tc ON i.tecnico_id = tc.id
            {where_sql}
            ORDER BY i.fechahora DESC
            LIMIT %s OFFSET %s
        """, params + [limite, offset])

        emergencias = cursor.fetchall()
        cursor.close()

        for e in emergencias:
            if e.get('fechahora'):
                e['fechahora'] = str(e['fechahora'])

        return {
            "emergencias": emergencias,
            "total": total,
            "pagina": pagina,
            "total_paginas": (total + limite - 1) // limite if total > 0 else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/emergencias/{incidente_id}")
def detalle_emergencia(incidente_id: int, usuario: dict = Depends(verificar_auth), conn = Depends(get_db)):
    """Detalle completo de una emergencia con historial."""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT i.*, t.nombrecomercial as taller_nombre, t.latitud as taller_lat,
                   t.longitud as taller_lng, t.direccion as taller_direccion,
                   tc.nombrecompleto as tecnico_nombre,
                   v.marca, v.modelo, v.color, v.anio
            FROM incidente i
            LEFT JOIN taller t ON i.taller_id = t.id
            LEFT JOIN tecnico tc ON i.tecnico_id = tc.id
            LEFT JOIN vehiculo v ON i.vehiculo_placa = v.placa
            WHERE i.id = %s
        """, (incidente_id,))
        incidente = cursor.fetchone()

        if not incidente:
            raise HTTPException(status_code=404, detail="Incidente no encontrado")

        # Historial
        cursor.execute("""
            SELECT estado_anterior, estado_nuevo, fecha_cambio
            FROM historialincidente
            WHERE incidente_id = %s
            ORDER BY fecha_cambio ASC
        """, (incidente_id,))
        historial = cursor.fetchall()

        cursor.close()

        if incidente.get('fechahora'):
            incidente['fechahora'] = str(incidente['fechahora'])
        for h in historial:
            if h.get('fecha_cambio'):
                h['fecha_cambio'] = str(h['fecha_cambio'])

        return {"incidente": incidente, "historial": historial}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# ==========================================
# Configurar ubicación de taller
# ==========================================
@router.patch("/taller/{taller_id}/ubicacion")
def configurar_ubicacion_taller(
    taller_id: int,
    datos: TallerUbicacionRequest,
    usuario: dict = Depends(verificar_auth),
    conn = Depends(get_db)
):
    """Configurar la ubicación geográfica del taller."""
    if normalizar_rol(usuario.get('rol', '')) != 'administrador_taller':
        raise HTTPException(status_code=403, detail="Solo administradores de taller")

    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE taller SET latitud = %s, longitud = %s WHERE id = %s",
            (datos.latitud, datos.longitud, taller_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Taller no encontrado")

        conn.commit()
        cursor.close()

        registrar_bitacora(usuario['user_id'], f'Ubicación del taller {taller_id} actualizada', 'taller')
        return {"mensaje": "Ubicación actualizada"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
