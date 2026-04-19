import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

def obtener_conexion():
    """Obtiene una conexión a la base de datos PostgreSQL (Neon)."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"--- ERROR DE CONEXIÓN ---")
        print(e)
        print("-------------------------")
        return None

def get_db():
    conn = obtener_conexion()
    if conn is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="No se pudo conectar a la base de datos")
    try:
        yield conn
    finally:
        conn.close()

