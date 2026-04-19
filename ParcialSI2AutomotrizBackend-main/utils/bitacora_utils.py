from datetime import datetime, timezone
from config.database import obtener_conexion


def registrar_bitacora(usuario_id: int, accion: str, tabla_afectada: str):
    """Registra una acción en la tabla bitácora para auditoría (CU-09)."""
    conn = obtener_conexion()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bitacora (usuario_id, accion, tabla_afectada, fecha)
                VALUES (%s, %s, %s, %s)
            """, (usuario_id, accion, tabla_afectada, datetime.now(timezone.utc)))
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"Error al registrar bitácora: {e}")
            conn.rollback()
        finally:
            conn.close()
