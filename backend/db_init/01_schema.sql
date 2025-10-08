-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- GreyOak Score Engine - PostgreSQL Schema
-- Version: 1.0.0
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- Scores table (main output)
CREATE TABLE IF NOT EXISTS scores (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    mode VARCHAR(10) NOT NULL CHECK (mode IN ('Trader', 'Investor')),
    
    -- Final outputs
    score NUMERIC(5,2) NOT NULL CHECK (score >= 0 AND score <= 100),
    band VARCHAR(20) NOT NULL CHECK (band IN ('Strong Buy', 'Buy', 'Hold', 'Avoid')),
    
    -- Pillar scores (0-100 each)
    f_pillar NUMERIC(5,2) CHECK (f_pillar >= 0 AND f_pillar <= 100),
    t_pillar NUMERIC(5,2) CHECK (t_pillar >= 0 AND t_pillar <= 100),
    r_pillar NUMERIC(5,2) CHECK (r_pillar >= 0 AND r_pillar <= 100),
    o_pillar NUMERIC(5,2) CHECK (o_pillar >= 0 AND o_pillar <= 100),
    q_pillar NUMERIC(5,2) CHECK (q_pillar >= 0 AND q_pillar <= 100),
    s_pillar NUMERIC(5,2) CHECK (s_pillar >= 0 AND s_pillar <= 100),
    
    -- Risk & guardrails
    -- CRITICAL: Column name is s_z (NOT sector_z) - matches spec terminology
    risk_penalty NUMERIC(5,2) NOT NULL CHECK (risk_penalty >= 0 AND risk_penalty <= 20),
    guardrail_flags JSONB NOT NULL DEFAULT '[]',
    confidence NUMERIC(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    s_z NUMERIC(6,3) NOT NULL,  -- Sector momentum z-score (weighted)
    
    -- Audit trail for determinism and traceability
    as_of TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    config_hash VARCHAR(64) NOT NULL,
    code_version VARCHAR(20),
    
    -- Constraints
    UNIQUE(ticker, date, mode),
    CHECK (LENGTH(ticker) >= 1)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_scores_ticker_date ON scores(ticker, date);
CREATE INDEX IF NOT EXISTS idx_scores_date_mode ON scores(date, mode);
CREATE INDEX IF NOT EXISTS idx_scores_band ON scores(band);
CREATE INDEX IF NOT EXISTS idx_scores_date_band_mode ON scores(date, band, mode);
CREATE INDEX IF NOT EXISTS idx_scores_as_of ON scores(as_of);

-- Sector mapping table (from CSV)
CREATE TABLE IF NOT EXISTS sector_mapping (
    ticker VARCHAR(20) PRIMARY KEY,
    sector_id VARCHAR(50) NOT NULL,
    sector_group VARCHAR(50) NOT NULL,
    exchange VARCHAR(10)
);

CREATE INDEX IF NOT EXISTS idx_sector_mapping_group ON sector_mapping(sector_group);

-- Config audit table (track configuration changes)
CREATE TABLE IF NOT EXISTS config_audit (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    config_hash VARCHAR(64) NOT NULL,
    config_content JSONB NOT NULL,
    changed_by VARCHAR(100),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_config_audit_hash ON config_audit(config_hash);
CREATE INDEX IF NOT EXISTS idx_config_audit_timestamp ON config_audit(timestamp DESC);

-- Comments for documentation
COMMENT ON TABLE scores IS 'Main output table storing daily scores for all stocks';
COMMENT ON COLUMN scores.s_z IS 'Sector momentum z-score (weighted). Used for SectorBear guardrail threshold (-1.5)';
COMMENT ON COLUMN scores.guardrail_flags IS 'Array of triggered guardrails: LowDataHold, Illiquidity, PledgeCap, HighRiskCap, SectorBear, LowCoverage';
COMMENT ON COLUMN scores.config_hash IS 'SHA-256 hash of YAML configs used for this score calculation (for determinism audit)';
COMMENT ON COLUMN scores.as_of IS 'Timestamp when score was calculated (for audit trail)';

COMMENT ON TABLE sector_mapping IS 'Ticker to sector mapping (from sector_map.csv)';
COMMENT ON TABLE config_audit IS 'Audit log for configuration changes (tracks config_hash + content)';
