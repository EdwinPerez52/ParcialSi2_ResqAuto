-- ============================================
-- ResQ Auto - Script de tabla faltante
-- Tabla de relación entre talleres y especialidades
-- ============================================

CREATE TABLE IF NOT EXISTS taller_especialidad (
    id SERIAL PRIMARY KEY,
    taller_id INTEGER NOT NULL REFERENCES taller(id) ON DELETE CASCADE,
    especialidad_id INTEGER NOT NULL REFERENCES especialidad(id) ON DELETE CASCADE,
    UNIQUE(taller_id, especialidad_id)
);

-- ============================================
-- NOTA: Si necesitas actualizar contraseñas existentes
-- de texto plano a bcrypt, puedes usar Python:
--
-- import bcrypt
-- hashed = bcrypt.hashpw(b"password_original", bcrypt.gensalt())
-- UPDATE usuario SET contrasena = 'hashed_value' WHERE id = X;
-- ============================================
