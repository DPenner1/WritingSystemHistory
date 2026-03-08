SELECT *, ROUND(100.0 * num_derivations / num_letters, 2) AS coverage FROM (
	SELECT 
	    script_code, 
		s.u_name AS script_name,
		COUNT(DISTINCT cp.id) AS num_letters, 
		COUNT(DISTINCT deriv.child_id) AS num_derivations
	FROM code_point cp LEFT JOIN code_point_derivation deriv ON cp.id = deriv.child_id INNER JOIN script s ON s.code = cp.script_code
	WHERE cp.general_category_code NOT LIKE 'C_' AND cp.general_category_code NOT LIKE 'Z_'
	GROUP BY script_code
)
ORDER BY coverage
