-- Script para convertir campos timezone-aware a timezone-naive en sessions table
-- Se ejecuta directamente en Supabase SQL Editor

-- Paso 1: Crear una nueva tabla temporal con campos sin timezone
CREATE TABLE sessions_temp AS 
SELECT 
    id,
    coach_id,
    player_id,
    coach_name_snapshot,
    player_name_snapshot,
    start_time::timestamp as start_time_naive,  -- Quitar timezone info
    end_time::timestamp as end_time_naive,      -- Quitar timezone info  
    status,
    notes,
    created_at::timestamp as created_at_naive,  -- Quitar timezone info
    calendar_event_id,
    updated_at::timestamp as updated_at_naive,  -- Quitar timezone info
    last_sync_at::timestamp as last_sync_at_naive,  -- Quitar timezone info
    sync_hash,
    source,
    version,
    is_dirty
FROM sessions;

-- Paso 2: Eliminar tabla original
DROP TABLE sessions CASCADE;

-- Paso 3: Recrear tabla con estructura correcta (sin timezone)
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    coach_id INTEGER REFERENCES coaches(coach_id),
    player_id INTEGER REFERENCES players(player_id),
    coach_name_snapshot VARCHAR(100),
    player_name_snapshot VARCHAR(100),
    start_time TIMESTAMP DEFAULT NOW(),  -- Sin timezone
    end_time TIMESTAMP,                  -- Sin timezone
    status session_status_enum DEFAULT 'scheduled',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(), -- Sin timezone
    calendar_event_id VARCHAR,
    updated_at TIMESTAMP DEFAULT NOW(), -- Sin timezone
    last_sync_at TIMESTAMP,             -- Sin timezone
    sync_hash VARCHAR(32),
    source VARCHAR(10) DEFAULT 'app',
    version INTEGER DEFAULT 1,
    is_dirty BOOLEAN DEFAULT FALSE
);

-- Paso 4: Copiar datos de la tabla temporal a la nueva tabla
INSERT INTO sessions (
    id, coach_id, player_id, coach_name_snapshot, player_name_snapshot,
    start_time, end_time, status, notes, created_at, calendar_event_id,
    updated_at, last_sync_at, sync_hash, source, version, is_dirty
)
SELECT 
    id, coach_id, player_id, coach_name_snapshot, player_name_snapshot,
    start_time_naive, end_time_naive, status, notes, created_at_naive, 
    calendar_event_id, updated_at_naive, last_sync_at_naive, sync_hash, 
    source, version, is_dirty
FROM sessions_temp;

-- Paso 5: Eliminar tabla temporal
DROP TABLE sessions_temp;

-- Paso 6: Reestablecer secuencia de ID
SELECT setval('sessions_id_seq', (SELECT MAX(id) FROM sessions));

-- Paso 7: Recrear índices si los había
-- (Supabase normalmente los recrea automáticamente)

-- Verificación: Mostrar algunas filas para confirmar conversión
SELECT id, start_time, created_at, updated_at 
FROM sessions 
LIMIT 5;