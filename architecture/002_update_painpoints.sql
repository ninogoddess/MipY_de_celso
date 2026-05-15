-- ============================================================
-- Scrapscrap_celso — Update latam_pain_points schema
-- Migration: 002_update_painpoints.sql
-- Date: 2026-05-14
-- ============================================================

-- Primero limpiamos la tabla de las pruebas anteriores (videos)
DELETE FROM latam_pain_points;

-- Añadir nuevas columnas obligatorias según el Hito 4
ALTER TABLE latam_pain_points
ADD COLUMN IF NOT EXISTS name TEXT,
ADD COLUMN IF NOT EXISTS keywords TEXT[],
ADD COLUMN IF NOT EXISTS sources TEXT,
ADD COLUMN IF NOT EXISTS semantic_metadata JSONB,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Trigger para updated_at si no existe
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_latam_pain_points_updated_at') THEN
        CREATE TRIGGER trg_latam_pain_points_updated_at
            BEFORE UPDATE ON latam_pain_points
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;
