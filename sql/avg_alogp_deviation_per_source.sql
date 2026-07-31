CREATE OR REPLACE VIEW gold.vw_avg_alogp_deviation_per_source AS
SELECT
    fs.source_chembl_id,
    AVG(ABS(target_dim.alogp - source_dim.alogp)) AS avg_alogp_deviation
FROM gold.fact_similarity fs
JOIN gold.dim_molecule source_dim
    ON fs.source_chembl_id = source_dim.chembl_id
JOIN gold.dim_molecule target_dim
    ON fs.target_chembl_id = target_dim.chembl_id
WHERE source_dim.alogp IS NOT NULL
    AND target_dim.alogp IS NOT NULL
GROUP BY fs.source_chembl_id;
