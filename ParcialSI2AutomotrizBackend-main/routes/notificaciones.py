from fastapi import APIRouter, HTTPException, Depends
from psycopg2.extras import RealDictCursor
from config.database import get_db
from middleware.auth_middleware import verificar_auth

router = APIRouter(prefix="/api", tags=["Notificaciones"])


# ==========================================
# CU-21: Enviar Notificaciones de Avance
# ==========================================

@router.get("/notificaciones")
def listar_notificaciones(
    pagina: int = 1,
    limite: int = 20,
    usuario: dict = Depends(verificar_auth),
    conn = Depends(get_db)
):
    """Listar notificaciones del usuario autenticado."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        "SELECT COUNT(*) as total FROM notificacion WHERE usuario_id = %s",
        (usuario['user_id'],)
    )
    total = cursor.fetchone()['total']

    offset = (pagina - 1) * limite
    cursor.execute("""
        SELECT id, titulo, mensaje, leida, tipo, referencia_id, fecha
        FROM notificacion
        WHERE usuario_id = %s
        ORDER BY fecha DESC
        LIMIT %s OFFSET %s
    """, (usuario['user_id'], limite, offset))

    notificaciones = cursor.fetchall()
    cursor.close()

    for n in notificaciones:
        if n.get('fecha'):
            n['fecha'] = str(n['fecha'])

    return {
        "notificaciones": notificaciones,
        "total": total,
        "pagina": pagina,
        "total_paginas": (total + limite - 1) // limite if total > 0 else 0
    }


@router.get("/notificaciones/no-leidas")
def contar_no_leidas(usuario: dict = Depends(verificar_auth), conn = Depends(get_db)):
    """Contar notificaciones no leídas."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "SELECT COUNT(*) as count FROM notificacion WHERE usuario_id = %s AND leida = FALSE",
        (usuario['user_id'],)
    )
    result = cursor.fetchone()
    cursor.close()
    return {"no_leidas": result['count']}


@router.patch("/notificaciones/{notificacion_id}/leer")
def marcar_leida(notificacion_id: int, usuario: dict = Depends(verificar_auth), conn = Depends(get_db)):
    """Marcar una notificación como leída."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notificacion SET leida = TRUE WHERE id = %s AND usuario_id = %s",
            (notificacion_id, usuario['user_id'])
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")

        conn.commit()
        cursor.close()
        return {"mensaje": "Notificación marcada como leída"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/notificaciones/leer-todas")
def marcar_todas_leidas(usuario: dict = Depends(verificar_auth), conn = Depends(get_db)):
    """Marcar todas las notificaciones como leídas."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notificacion SET leida = TRUE WHERE usuario_id = %s AND leida = FALSE",
            (usuario['user_id'],)
        )
        count = cursor.rowcount
        conn.commit()
        cursor.close()
        return {"mensaje": f"{count} notificaciones marcadas como leídas"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
