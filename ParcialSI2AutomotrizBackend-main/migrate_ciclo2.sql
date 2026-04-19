-- =====================================================
-- CICLO 2: Migración - Emergencias y Logística
-- =====================================================

-- 1. Agregar geolocalización a talleres
ALTER TABLE taller ADD COLUMN IF NOT EXISTS latitud DOUBLE PRECISION;
ALTER TABLE taller ADD COLUMN IF NOT EXISTS longitud DOUBLE PRECISION;

-- 2. Crear tabla de notificaciones
CREATE TABLE IF NOT EXISTS notificacion (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES usuario(id),
    titulo VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    leida BOOLEAN DEFAULT FALSE,
    tipo VARCHAR(50) NOT NULL,         -- 'emergencia', 'asignacion', 'estado', 'sistema'
    referencia_id BIGINT,              -- ID del incidente relacionado
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notificacion_usuario ON notificacion(usuario_id);
CREATE INDEX IF NOT EXISTS idx_notificacion_leida ON notificacion(usuario_id, leida);

-- 3. Agregar columna descripcion a incidente (para que el conductor explique el problema)
ALTER TABLE incidente ADD COLUMN IF NOT EXISTS descripcion TEXT;

-- 4. Stored Procedure: Registrar nuevo incidente
CREATE OR REPLACE FUNCTION registrar_nuevo_incidente(
    p_latitud DOUBLE PRECISION,
    p_longitud DOUBLE PRECISION,
    p_descripcion TEXT,
    p_vehiculo_placa TEXT,
    p_usuario_id BIGINT
) RETURNS BIGINT AS $$
DECLARE
    v_incidente_id BIGINT;
BEGIN
    -- Insertar incidente
    INSERT INTO incidente (fechahora, latitud, longitud, estadoactual, vehiculo_placa, descripcion)
    VALUES (CURRENT_TIMESTAMP, p_latitud, p_longitud, 'Reportado', p_vehiculo_placa, p_descripcion)
    RETURNING id INTO v_incidente_id;

    -- Crear registro inicial en historial
    INSERT INTO historialincidente (incidente_id, estado_anterior, estado_nuevo, fecha_cambio)
    VALUES (v_incidente_id, 'Nuevo', 'Reportado', CURRENT_TIMESTAMP);

    -- Registrar en bitácora
    INSERT INTO bitacora (usuario_id, accion, tabla_afectada, fecha)
    VALUES (p_usuario_id, 'Solicitud de auxilio vehicular - Incidente #' || v_incidente_id, 'incidente', CURRENT_TIMESTAMP);

    RETURN v_incidente_id;
END;
$$ LANGUAGE plpgsql;

-- 5. Stored Procedure: Asignar técnico a incidente
CREATE OR REPLACE FUNCTION asignar_tecnico_incidente(
    p_incidente_id BIGINT,
    p_taller_id BIGINT,
    p_tecnico_id BIGINT,
    p_usuario_id BIGINT
) RETURNS VOID AS $$
DECLARE
    v_estado_actual TEXT;
BEGIN
    -- Verificar estado actual
    SELECT estadoactual INTO v_estado_actual FROM incidente WHERE id = p_incidente_id;

    IF v_estado_actual NOT IN ('Reportado', 'Asignado') THEN
        RAISE EXCEPTION 'El incidente no está en estado válido para asignación';
    END IF;

    -- Actualizar incidente
    UPDATE incidente
    SET taller_id = p_taller_id, tecnico_id = p_tecnico_id, estadoactual = 'En camino'
    WHERE id = p_incidente_id;

    -- Marcar técnico como no disponible
    UPDATE tecnico SET estadisponible = FALSE WHERE id = p_tecnico_id;

    -- Registrar en historial
    INSERT INTO historialincidente (incidente_id, estado_anterior, estado_nuevo, fecha_cambio)
    VALUES (p_incidente_id, v_estado_actual, 'En camino', CURRENT_TIMESTAMP);

    -- Registrar en bitácora
    INSERT INTO bitacora (usuario_id, accion, tabla_afectada, fecha)
    VALUES (p_usuario_id, 'Asignación de técnico al incidente #' || p_incidente_id, 'incidente', CURRENT_TIMESTAMP);
END;
$$ LANGUAGE plpgsql;

-- 6. Stored Procedure: Finalizar servicio con pago
CREATE OR REPLACE FUNCTION finalizar_servicio_pago(
    p_incidente_id BIGINT,
    p_monto_total NUMERIC(10,2),
    p_metodo_pago TEXT,
    p_usuario_id BIGINT
) RETURNS VOID AS $$
DECLARE
    v_tecnico_id BIGINT;
    v_transaccion_id BIGINT;
    v_comision NUMERIC(10,2);
BEGIN
    -- Obtener técnico asignado
    SELECT tecnico_id INTO v_tecnico_id FROM incidente WHERE id = p_incidente_id;

    -- Liberar técnico
    IF v_tecnico_id IS NOT NULL THEN
        UPDATE tecnico SET estadisponible = TRUE WHERE id = v_tecnico_id;
    END IF;

    -- Marcar incidente como finalizado
    UPDATE incidente SET estadoactual = 'Finalizado' WHERE id = p_incidente_id;

    -- Registrar en historial
    INSERT INTO historialincidente (incidente_id, estado_anterior, estado_nuevo, fecha_cambio)
    VALUES (p_incidente_id, 'En reparación', 'Finalizado', CURRENT_TIMESTAMP);

    -- Crear transacción
    INSERT INTO transaccion (montototal, metodopago, estadopago, incidente_id)
    VALUES (p_monto_total, p_metodo_pago, 'Completado', p_incidente_id)
    RETURNING id INTO v_transaccion_id;

    -- Calcular e insertar comisión del 10%
    v_comision := p_monto_total * 0.10;
    INSERT INTO comision (monto_comision, porcentaje, fecha_calculo, transaccion_id)
    VALUES (v_comision, 10.00, CURRENT_TIMESTAMP, v_transaccion_id);

    -- Registrar en bitácora
    INSERT INTO bitacora (usuario_id, accion, tabla_afectada, fecha)
    VALUES (p_usuario_id, 'Servicio finalizado - Incidente #' || p_incidente_id || ' - Monto: ' || p_monto_total, 'incidente', CURRENT_TIMESTAMP);
END;
$$ LANGUAGE plpgsql;

-- 7. Stored Procedure: Limpiar sesiones antiguas
CREATE OR REPLACE FUNCTION limpiar_sesiones_antiguas() RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE sesion
    SET fecha_fin = CURRENT_TIMESTAMP
    WHERE fecha_fin IS NULL
      AND fecha_inicio < CURRENT_TIMESTAMP - INTERVAL '24 hours';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- 8. Datos de prueba: Coordenadas Santa Cruz de la Sierra para talleres existentes
UPDATE taller SET latitud = -17.7833, longitud = -63.1821 WHERE latitud IS NULL;
