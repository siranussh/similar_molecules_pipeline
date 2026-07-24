CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_molecule (
    chembl_id VARCHAR(20) PRIMARY KEY,
    molecule_type VARCHAR(50),
    mw_freebase NUMERIC,
    alogp NUMERIC,
    psa NUMERIC,
    cx_logp NUMERIC,
    molecular_species VARCHAR(50),
    full_mwt NUMERIC,
    aromatic_rings INTEGER,
    heavy_atoms INTEGER
);

CREATE TABLE IF NOT EXISTS gold.fact_similarity (
    source_chembl_id VARCHAR(20) NOT NULL REFERENCES gold.dim_molecule (chembl_id),
    target_chembl_id VARCHAR(20) NOT NULL REFERENCES gold.dim_molecule (chembl_id),
    similarity_score NUMERIC NOT NULL,
    has_duplicates_of_last_largest_score BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (source_chembl_id, target_chembl_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_similarity_source
    ON gold.fact_similarity (source_chembl_id);

CREATE INDEX IF NOT EXISTS idx_fact_similarity_score
    ON gold.fact_similarity (source_chembl_id, similarity_score DESC);
