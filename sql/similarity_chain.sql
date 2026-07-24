CREATE OR REPLACE VIEW gold.similarity_chain AS
WITH ranked AS (
    SELECT
        source_chembl_id,
        target_chembl_id,
        similarity_score,
        ROW_NUMBER() OVER (
            PARTITION BY source_chembl_id
            ORDER BY similarity_score DESC
        ) AS rank
    FROM gold.fact_similarity
)
SELECT
    first_match.source_chembl_id,
    first_match.target_chembl_id AS most_similar_target,
    first_match.similarity_score AS most_similar_score,
    second_match.target_chembl_id AS next_most_similar_target,
    second_match.similarity_score AS next_most_similar_score
FROM ranked first_match
LEFT JOIN ranked second_match
    ON first_match.source_chembl_id = second_match.source_chembl_id
    AND second_match.rank = first_match.rank + 1
WHERE first_match.rank = 1;
