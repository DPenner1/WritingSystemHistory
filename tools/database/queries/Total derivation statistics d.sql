WITH letter AS (
    SELECT id FROM code_point 
    WHERE general_category_code LIKE 'L_' AND decomposition_type IS NULL)
SELECT
    'Distinct letters ...' AS statistic,
	COUNT(*) AS quantity,
	100.0 AS percentage
FROM letter
UNION ALL
SELECT
    '... with derivations ...' AS statistic,
    COUNT(DISTINCT cpd.child_id) AS quantity,
    ROUND(100.0 * COUNT(DISTINCT cpd.child_id)/COUNT(DISTINCT letter.id), 1) AS percentage
FROM letter LEFT JOIN code_point_derivation cpd ON letter.id = cpd.child_id
UNION ALL
SELECT
    '... that are manually specified' AS statistic,
    COUNT(DISTINCT cpd.child_id) AS quantity,
    ROUND(100.0 * COUNT(DISTINCT cpd.child_id)/COUNT(DISTINCT letter.id), 1) AS percentage
FROM letter LEFT JOIN code_point_derivation cpd ON letter.id = cpd.child_id AND cpd.certainty_type_id <> 4
ORDER BY quantity DESC
