CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS bronze.chembl_id_lookup (
    chembl_id VARCHAR(20),
    entity_type VARCHAR(50),
    entity_id INTEGER,
    status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS bronze.molecule_dictionary (
    molregno INTEGER PRIMARY KEY,
    chembl_id VARCHAR(20) NOT NULL,
    pref_name VARCHAR(255),
    molecule_type VARCHAR(50),
    max_phase NUMERIC,
    therapeutic_flag SMALLINT,
    withdrawn_flag SMALLINT
);

CREATE TABLE IF NOT EXISTS bronze.compound_properties (
    molregno INTEGER PRIMARY KEY,
    mw_freebase NUMERIC,
    full_mwt NUMERIC,
    alogp NUMERIC,
    hba INTEGER,
    hbd INTEGER,
    psa NUMERIC,
    aromatic_rings INTEGER,
    heavy_atoms INTEGER,
    qed_weighted NUMERIC
);

CREATE TABLE IF NOT EXISTS bronze.compound_structures (
    molregno INTEGER PRIMARY KEY,
    canonical_smiles TEXT,
    standard_inchi TEXT,
    standard_inchi_key VARCHAR(27)
);

CREATE INDEX IF NOT EXISTS idx_chembl_id_lookup_chembl_id
    ON bronze.chembl_id_lookup (chembl_id);

CREATE INDEX IF NOT EXISTS idx_molecule_dictionary_chembl_id
    ON bronze.molecule_dictionary (chembl_id);
