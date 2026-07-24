CREATE OR REPLACE VIEW gold.avg_similarity_grouped AS
SELECT
    COALESCE(sd.chembl_id, 'TOTAL') AS source_chembl_id,
    COALESCE(
        (sd.aromatic_rings + sd.heavy_atoms)::TEXT, 'TOTAL'
    ) AS aromatic_rings_plus_heavy_atoms,
    COALESCE(sd.heavy_atoms::TEXT, 'TOTAL') AS heavy_atoms,
    AVG(fs.similarity_score) AS avg_similarity_score
FROM gold.fact_similarity fs
JOIN gold.dim_molecule sd
    ON fs.source_chembl_id = sd.chembl_id
GROUP BY GROUPING SETS (
    (sd.chembl_id),
    ROLLUP (sd.heavy_atoms, sd.aromatic_rings)
);
