SELECT 
    'All scripts' AS included,
	letters,
    derivations,	
	ROUND(100.0 * derivations / letters, 1) AS coverage,
    manual_derivations,	
	ROUND(100.0 * manual_derivations / letters, 1) AS manual_coverage
FROM (
	SELECT
		COUNT(DISTINCT cp.id) AS letters,
		COUNT(DISTINCT deriv.child_id) AS derivations,
		COUNT(DISTINCT CASE WHEN deriv.certainty_type_id = 4 THEN NULL ELSE deriv.child_id END) AS manual_derivations
	FROM code_point cp LEFT JOIN code_point_derivation deriv ON cp.id = deriv.child_id
	WHERE cp.equivalent_sequence_id IS NULL AND cp.general_category_code LIKE 'L_'
)
UNION ALL
SELECT 
    'Non-Han (Chinese)' AS included,
	letters,
    derivations,	
	ROUND(100.0 * derivations / letters, 1) AS coverage,
    manual_derivations,	
	ROUND(100.0 * manual_derivations / letters, 1) AS manual_coverage
FROM (
	SELECT
		COUNT(DISTINCT cp.id) AS letters,
		COUNT(DISTINCT deriv.child_id) AS derivations,
		COUNT(DISTINCT CASE WHEN deriv.certainty_type_id = 4 THEN NULL ELSE deriv.child_id END) AS manual_derivations
	FROM code_point cp LEFT JOIN code_point_derivation deriv ON cp.id = deriv.child_id
	WHERE cp.equivalent_sequence_id IS NULL AND cp.general_category_code LIKE 'L_' AND script_code <> 'Hani'
)
UNION ALL
SELECT 
    'Han (Chinese)' AS included,
	letters,
    derivations,	
	ROUND(100.0 * derivations / letters, 1) AS coverage,
    manual_derivations,	
	ROUND(100.0 * manual_derivations / letters, 1) AS manual_coverage
FROM (
	SELECT
		COUNT(DISTINCT cp.id) AS letters,
		COUNT(DISTINCT deriv.child_id) AS derivations,
		COUNT(DISTINCT CASE WHEN deriv.certainty_type_id = 4 THEN NULL ELSE deriv.child_id END) AS manual_derivations
	FROM code_point cp LEFT JOIN code_point_derivation deriv ON cp.id = deriv.child_id
	WHERE cp.equivalent_sequence_id IS NULL AND cp.general_category_code LIKE 'L_' AND script_code = 'Hani'
)
ORDER BY letters DESC

