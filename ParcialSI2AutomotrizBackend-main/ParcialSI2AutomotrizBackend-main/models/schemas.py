from pydantic import BaseModel
from typing import Optional


# ==========================================
# AUTENTICACIÓN (CU-01, CU-02, CU-03, CU-04)
# ==========================================
class LoginRequest(BaseModel):
    correo: str
    contrasena: str


class RegistroUsuarioRequest(BaseModel):
    correo: str
    contrasena: str
    nombre_completo: str
    telefono: Optional[str] = None
    rol: str  # 'conductor', 'administrador_taller', 'tecnico'
    # Campos para administrador_taller
    nit: Optional[str] = None
    nombre_comercial: Optional[str] = None
    direccion: Optional[str] = None
    # Campo para técnico
    taller_id: Optional[int] = None


class RecuperarPasswordRequest(BaseModel):
    correo: str


class ResetPasswordRequest(BaseModel):
    correo: str
    nueva_contrasena: str
    token_reset: str


# ==========================================
# VEHÍCULOS (CU-05)
# ==========================================
class VehiculoRequest(BaseModel):
    placa: str
    marca: str
    modelo: str
    anio: int
    color: str


class VehiculoUpdateRequest(BaseModel):
    marca: Optional[str] = None
    modelo: Optional[str] = None
    anio: Optional[int] = None
    color: Optional[str] = None


# ==========================================
# TALLERES Y TÉCNICOS (CU-06, CU-07, CU-08)
# ==========================================
class EspecialidadAsignarRequest(BaseModel):
    especialidad_ids: list[int]


class TecnicoRequest(BaseModel):
    nombre_completo: str
    correo: str
    contrasena: str


class TecnicoUpdateRequest(BaseModel):
    nombre_completo: Optional[str] = None


class DisponibilidadRequest(BaseModel):
    estadisponible: bool
