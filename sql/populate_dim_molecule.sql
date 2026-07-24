TRUNCATE TABLE gold.fact_similarity, gold.dim_molecule;

INSERT INTO gold.dim_molecule (
    chembl_id,
    molecule_type,
    mw_freebase,
    alogp,
    psa,
    cx_logp,
    molecular_species,
    full_mwt,
    aromatic_rings,
    heavy_atoms
)
SELECT
    md.chembl_id,
    md.molecule_type,
    cp.mw_freebase,
    cp.alogp,
    cp.psa,
    NULL AS cx_logp,
    NULL AS molecular_species,
    cp.full_mwt,
    cp.aromatic_rings,
    cp.heavy_atoms
FROM bronze.molecule_dictionary md
JOIN bronze.compound_properties cp
    ON md.molregno = cp.molregno
JOIN bronze.compound_structures cs
    ON md.molregno = cs.molregno
WHERE cs.canonical_smiles IS NOT NULL;
