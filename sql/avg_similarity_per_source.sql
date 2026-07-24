CREATE OR REPLACE VIEW gold.vw_avg_similarity_per_source AS
SELECT
    source_chembl_id,
    AVG(similarity_score) AS avg_similarity_score
FROM gold.fact_similarity
GROUP BY source_chembl_id;
