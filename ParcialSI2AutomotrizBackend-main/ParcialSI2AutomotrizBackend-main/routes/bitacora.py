from fastapi import APIRouter, HTTPException, Depends
from psycopg2.extras import RealDictCursor
from config.database import obtener_conexion
from middleware.auth_middleware import verificar_auth

router = APIRouter(prefix="/api", tags=["Bitácora"])


# ==========================================
# CU-09: Gestionar Bitácora
# ==========================================

@router.get("/bitacora")
def listar_bitacora(
    pagina: int = 1,
    limite: int = 20,
    usuario_id: int = None,
    tabla: str = None,
    usuario: dict = Depends(verificar_auth)
):
    """
    Listar registros de la bitácora con paginación y filtros opcionales.
    Filtros: usuario_id, tabla_afectada.
    """
    conn = obtener_conexion()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Construir filtros
        where_clauses = []
        params = []

        if usuario_id:
            where_clauses.append("b.usuario_id = %s")
            params.append(usuario_id)
        if tabla:
            where_clauses.append("b.tabla_afectada = %s")
            params.append(tabla)

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Contar total de registros
        cursor.execute(f"SELECT COUNT(*) as total FROM bitacora b {where_sql}", params)
        total = cursor.fetchone()['total']

        # Obtener resultados paginados
        offset = (pagina - 1) * limite
        query_params = params + [limite, offset]

        cursor.execute(f"""
            SELECT b.id, b.usuario_id, u.correo as usuario_correo,
                   b.accion, b.tabla_afectada, b.fecha
            FROM bitacora b
            LEFT JOIN usuario u ON b.usuario_id = u.id
            {where_sql}
            ORDER BY b.fecha DESC
            LIMIT %s OFFSET %s
        """, query_params)

        registros = cursor.fetchall()
        cursor.close()

        # Convertir datetime a string para serialización JSON
        for r in registros:
            if r.get('fecha'):
                r['fecha'] = str(r['fecha'])

        return {
            "registros": registros,
            "total": total,
            "pagina": pagina,
            "limite": limite,
            "total_paginas": (total + limite - 1) // limite
        }
    finally:
        conn.close()
