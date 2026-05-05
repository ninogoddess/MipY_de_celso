-- ============================================================
-- Scrapscrap_celso — Database Update
-- Migration: 002_migration_summary.sql
-- Date: 2026-05-05
-- ============================================================
-- Ejecutar en: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

CREATE TABLE IF NOT EXISTS latam_market_summary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    summary_text TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE latam_market_summary IS 'Almacena el resumen y consolidación de todos los pain points extraídos para ser inyectado en el Wizard RPM';
