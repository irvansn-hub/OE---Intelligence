SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    item_id VARCHAR PRIMARY KEY, item_name VARCHAR NOT NULL, category VARCHAR NOT NULL,
    specification VARCHAR NOT NULL, brand VARCHAR NOT NULL, unit VARCHAR NOT NULL,
    UNIQUE(item_name, category, specification, brand, unit)
);
CREATE TABLE IF NOT EXISTS reference_sources (
    source_id VARCHAR PRIMARY KEY, source_type VARCHAR NOT NULL, source_name VARCHAR NOT NULL,
    source_year INTEGER NOT NULL, effective_date DATE NOT NULL, version VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT current_timestamp,
    UNIQUE(source_type, source_name, source_year, version)
);
CREATE TABLE IF NOT EXISTS price_observations (
    price_observation_id VARCHAR PRIMARY KEY, item_id VARCHAR NOT NULL REFERENCES items(item_id),
    source_id VARCHAR NOT NULL REFERENCES reference_sources(source_id), vendor VARCHAR NOT NULL,
    quantity DOUBLE PRECISION, price DOUBLE PRECISION, normalized_unit_price DOUBLE PRECISION, location VARCHAR NOT NULL,
    region VARCHAR NOT NULL, observation_date DATE NOT NULL, url_reference VARCHAR NOT NULL,
    notes VARCHAR NOT NULL, is_demo BOOLEAN NOT NULL, fingerprint VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT current_timestamp
);
CREATE TABLE IF NOT EXISTS inflation_indices (
    index_name VARCHAR NOT NULL, year INTEGER NOT NULL, adjustment_rate DOUBLE PRECISION NOT NULL,
    is_demo BOOLEAN NOT NULL, created_at TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY(index_name, year, is_demo)
);
CREATE TABLE IF NOT EXISTS analyses (
    analysis_id VARCHAR PRIMARY KEY, analysis_name VARCHAR NOT NULL, item_name VARCHAR NOT NULL,
    analysis_date DATE NOT NULL, target_date DATE NOT NULL, benchmark DOUBLE PRECISION,
    actual_unit_price DOUBLE PRECISION, observation_count INTEGER NOT NULL, outlier_count INTEGER NOT NULL,
    is_demo BOOLEAN NOT NULL, snapshot JSONB NOT NULL, created_at TIMESTAMP DEFAULT current_timestamp
);
CREATE TABLE IF NOT EXISTS analysis_observations (
    analysis_id VARCHAR NOT NULL REFERENCES analyses(analysis_id),
    price_observation_id VARCHAR NOT NULL REFERENCES price_observations(price_observation_id),
    decision VARCHAR NOT NULL CHECK (decision IN ('INCLUDE','EXCLUDE','REVIEW')),
    justification VARCHAR NOT NULL, is_comparable BOOLEAN NOT NULL, is_outlier BOOLEAN NOT NULL,
    evidence_snapshot JSONB NOT NULL, PRIMARY KEY(analysis_id, price_observation_id)
);
CREATE TABLE IF NOT EXISTS initialization (name VARCHAR PRIMARY KEY);
CREATE OR REPLACE VIEW observation_details AS
SELECT o.*, i.item_name, i.category, i.specification, i.brand, i.unit,
       s.source_type, s.source_name, s.source_year AS effective_year, s.effective_date, s.version
FROM price_observations o JOIN items i USING (item_id) JOIN reference_sources s USING (source_id);
"""
