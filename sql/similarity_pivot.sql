CREATE OR REPLACE VIEW gold.similarity_pivot AS
SELECT
    target_chembl_id,
    MAX(CASE WHEN source_chembl_id = 'CHEMBL1'
        THEN similarity_score END) AS "CHEMBL1",
    MAX(CASE WHEN source_chembl_id = 'CHEMBL10'
        THEN similarity_score END) AS "CHEMBL10",
    MAX(CASE WHEN source_chembl_id = 'CHEMBL100'
        THEN similarity_score END) AS "CHEMBL100",
    MAX(CASE WHEN source_chembl_id = 'CHEMBL1000'
        THEN similarity_score END) AS "CHEMBL1000",
    MAX(CASE WHEN source_chembl_id = 'CHEMBL10000'
        THEN similarity_score END) AS "CHEMBL10000",
    MAX(CASE WHEN source_chembl_id = 'CHEMBL100001'
        THEN similarity_score END) AS "CHEMBL100001",
    MAX(CASE WHEN source_chembl_id = 'CHEMBL100003'
        THEN similarity_score END) AS "CHEMBL100003",
    MAX(CASE WHEN source_chembl_id = 'CHEMBL100004'
        THEN similarity_score END) AS "CHEMBL100004",
    MAX(CASE WHEN source_chembl_id = 'CHEMBL100005'
        THEN similarity_score END) AS "CHEMBL100005",
    MAX(CASE WHEN source_chembl_id = 'CHEMBL100006'
        THEN similarity_score END) AS "CHEMBL100006"
FROM gold.fact_similarity
WHERE source_chembl_id IN (
    'CHEMBL1', 'CHEMBL10', 'CHEMBL100', 'CHEMBL1000', 'CHEMBL10000',
    'CHEMBL100001', 'CHEMBL100003', 'CHEMBL100004', 'CHEMBL100005',
    'CHEMBL100006'
)
GROUP BY target_chembl_id;
