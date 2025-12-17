-- init.sql - Database schema for InTheGrid
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Table 1: Market Prices (the core data)
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL,
    market VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (market, timestamp)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('prices', 'timestamp', if_not_exists => TRUE);

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_prices_market ON prices (market, timestamp DESC);

-- Table 2: Spread Opportunities (calculated arbitrage)
CREATE TABLE IF NOT EXISTS spreads (
    id SERIAL PRIMARY KEY,
    market_pair VARCHAR(20) NOT NULL,  -- e.g., 'DE-FR'
    timestamp TIMESTAMPTZ NOT NULL,
    spread NUMERIC(10, 2) NOT NULL,
    net_opportunity NUMERIC(10, 2) NOT NULL,
    low_market VARCHAR(10) NOT NULL,
    high_market VARCHAR(10) NOT NULL,
    low_price NUMERIC(10, 2) NOT NULL,
    high_price NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Note: Not converting to hypertable yet - needs timestamp in PK

-- Table 3: Alerts (high-value opportunities)
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    market_pair VARCHAR(20) NOT NULL,
    spread NUMERIC(10, 2) NOT NULL,
    net_opportunity NUMERIC(10, 2) NOT NULL,
    priority VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert some seed data for testing
INSERT INTO prices (market, timestamp, price) VALUES
    ('DE', NOW() - INTERVAL '1 hour', 72.50),
    ('FR', NOW() - INTERVAL '1 hour', 85.00),
    ('NL', NOW() - INTERVAL '1 hour', 78.25),
    ('DK', NOW() - INTERVAL '1 hour', 68.00),
    ('BE', NOW() - INTERVAL '1 hour', 81.50),
    ('DE', NOW(), 74.00),
    ('FR', NOW(), 88.50),
    ('NL', NOW(), 79.00),
    ('DK', NOW(), 65.50),
    ('BE', NOW(), 83.00)
ON CONFLICT DO NOTHING;

-- Verify setup
SELECT 'Database initialized successfully!' as status;