-- ============================================================
-- Scrapscrap_celso — Initial Database Schema
-- Migration: 001_initial_schema.sql
-- Date: 2026-04-27
-- Target: Supabase (PostgreSQL)
-- ============================================================
-- Ejecutar en: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- Enable UUID extension (usually enabled by default in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- CAPA 1: DATOS CRUDOS (RAW LAYER)
-- ============================================================

-- 1. CHANNELS — Soporte multi-canal desde día 1
CREATE TABLE IF NOT EXISTS channels (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id    TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    url           TEXT,
    description   TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE channels IS 'Canales de YouTube registrados para scraping';

-- 2. VIDEOS — Metadata estática de cada video scrapeado
CREATE TABLE IF NOT EXISTS videos (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id        UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    video_id          TEXT NOT NULL UNIQUE,
    title             TEXT NOT NULL,
    description       TEXT,
    url               TEXT NOT NULL,
    published_at      TIMESTAMPTZ,
    duration_seconds  INTEGER,
    thumbnail_url     TEXT,
    tags              TEXT[],
    language          TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE videos IS 'Metadata estática de cada video de YouTube scrapeado';

-- 3. VIDEO_SNAPSHOTS — Evolución temporal de datos dinámicos
CREATE TABLE IF NOT EXISTS video_snapshots (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id      UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    views         BIGINT,
    likes         BIGINT,
    comments_count INTEGER,
    captured_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE video_snapshots IS 'Captura periódica de métricas dinámicas (views, likes, comments) para rastrear evolución';

-- 4. TRANSCRIPTIONS — Transcripciones completas extraídas vía Apify
CREATE TABLE IF NOT EXISTS transcriptions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id    UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    language    TEXT,
    full_text   TEXT NOT NULL,
    segments    JSONB,
    source      TEXT NOT NULL DEFAULT 'apify_pinto_studio',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE transcriptions IS 'Transcripciones completas. full_text para LLM, segments para timestamps detallados';

-- 5. SCRAPER_RUNS — Historial de ejecuciones del scraper
CREATE TABLE IF NOT EXISTS scraper_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id      UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    videos_found    INTEGER DEFAULT 0,
    videos_new      INTEGER DEFAULT 0,
    videos_updated  INTEGER DEFAULT 0,
    errors          JSONB,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

COMMENT ON TABLE scraper_runs IS 'Registro de cada ejecución del scraper con estadísticas y errores';

-- ============================================================
-- CAPA 2: DATOS PROCESADOS (ANALYSIS LAYER)
-- ============================================================

-- 6. VIDEO_CLASSIFICATIONS — Análisis IA por video
CREATE TABLE IF NOT EXISTS video_classifications (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id                UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    business_model          TEXT,
    industry                TEXT,
    revenue_range           TEXT,
    key_insights            JSONB,
    pain_points_identified  JSONB,
    latam_relevance_score   INTEGER CHECK (latam_relevance_score BETWEEN 0 AND 100),
    model_used              TEXT,
    prompt_version          TEXT,
    classified_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE video_classifications IS 'Clasificaciones IA separadas de datos crudos del video';

-- 7. LATAM_PAIN_POINTS — Pain points con evidencia y video fuente
CREATE TABLE IF NOT EXISTS latam_pain_points (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    description      TEXT NOT NULL,
    impact_level     TEXT NOT NULL CHECK (impact_level IN ('Low', 'Medium', 'High', 'Critical')),
    category         TEXT,
    evidence         TEXT,
    source_video_id  UUID REFERENCES videos(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE latam_pain_points IS 'Pain points del mercado LATAM identificados desde videos con evidencia real';

-- ============================================================
-- CAPA 3: DATOS DE USUARIO Y DELIVERY
-- ============================================================

-- 8. USER_PROFILES — Perfil base del usuario
CREATE TABLE IF NOT EXISTS user_profiles (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    display_name  TEXT NOT NULL,
    email         TEXT UNIQUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE user_profiles IS 'Perfil base del usuario del sistema';

-- 9. RPM_PROFILES — Perfil RPM versionado
CREATE TABLE IF NOT EXISTS rpm_profiles (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    resources         JSONB,
    process           JSONB,
    market            JSONB,
    raw_answers       JSONB,
    ai_interpretation JSONB,
    version           INTEGER NOT NULL DEFAULT 1,
    is_active         BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE rpm_profiles IS 'Perfil RPM del usuario. Versionado: cada wizard crea un nuevo registro';

-- 10. SOLUTIONS — Soluciones de negocio generadas
CREATE TABLE IF NOT EXISTS solutions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    rpm_profile_id  UUID NOT NULL REFERENCES rpm_profiles(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    latam_adaptation TEXT,
    rpm_fit_score   INTEGER CHECK (rpm_fit_score BETWEEN 0 AND 100),
    difficulty      TEXT CHECK (difficulty IN ('Low', 'Medium', 'High')),
    justification   TEXT,
    status          TEXT NOT NULL DEFAULT 'generated' CHECK (status IN ('generated', 'reviewing', 'validating', 'validated', 'rejected')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE solutions IS 'Soluciones de negocio generadas por IA basadas en videos reales y perfil RPM';

-- 11. SOLUTION_SOURCE_VIDEOS — Trazabilidad solución ↔ videos
CREATE TABLE IF NOT EXISTS solution_source_videos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    solution_id     UUID NOT NULL REFERENCES solutions(id) ON DELETE CASCADE,
    video_id        UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    relevance_note  TEXT,
    UNIQUE(solution_id, video_id)
);

COMMENT ON TABLE solution_source_videos IS 'Tabla puente N:M que traza cada solución a los videos que la inspiraron';

-- 12. MVT_VALIDATIONS — Registro de validación MVT
CREATE TABLE IF NOT EXISTS mvt_validations (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    solution_id          UUID NOT NULL UNIQUE REFERENCES solutions(id) ON DELETE CASCADE,
    decision             TEXT CHECK (decision IN ('Pivot', 'Proceed', 'Kill')),
    conversion_rate      FLOAT,
    engagement_score     FLOAT,
    total_conversations  INTEGER DEFAULT 0,
    total_tests          INTEGER DEFAULT 0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE mvt_validations IS 'Validación MVT por solución. Relación 1:1 con solutions';

-- 13. MVT_EVIDENCE — Evidencia real (conversaciones, tests)
CREATE TABLE IF NOT EXISTS mvt_evidence (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    validation_id   UUID NOT NULL REFERENCES mvt_validations(id) ON DELETE CASCADE,
    evidence_type   TEXT NOT NULL CHECK (evidence_type IN ('conversation', 'test', 'survey', 'landing_page')),
    content         TEXT NOT NULL,
    source          TEXT,
    outcome         TEXT,
    evidence_url    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE mvt_evidence IS 'Piezas de evidencia real para validaciones MVT. Prohibido datos falsos';

-- ============================================================
-- ÍNDICES ESTRATÉGICOS
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_video_snapshots_video_captured ON video_snapshots(video_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_transcriptions_video_id ON transcriptions(video_id);
CREATE INDEX IF NOT EXISTS idx_video_classifications_video_id ON video_classifications(video_id);
CREATE INDEX IF NOT EXISTS idx_latam_pain_points_video_id ON latam_pain_points(source_video_id);
CREATE INDEX IF NOT EXISTS idx_solutions_user_id ON solutions(user_id);
CREATE INDEX IF NOT EXISTS idx_rpm_profiles_user_active ON rpm_profiles(user_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_scraper_runs_channel_id ON scraper_runs(channel_id);

-- ============================================================
-- TRIGGER: auto-update updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_videos_updated_at
    BEFORE UPDATE ON videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_solutions_updated_at
    BEFORE UPDATE ON solutions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_mvt_validations_updated_at
    BEFORE UPDATE ON mvt_validations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- SEED: Canal inicial (Starter Story)
-- ============================================================

INSERT INTO channels (channel_id, name, url, description, is_active)
VALUES (
    'UCp6993wxpWPMfTso0IjxOaQ',
    'Starter Story',
    'https://www.youtube.com/@StarterStory',
    'Interviews with successful entrepreneurs and business founders',
    true
)
ON CONFLICT (channel_id) DO NOTHING;

-- ============================================================
-- FIN DE MIGRACIÓN 001
-- ============================================================
