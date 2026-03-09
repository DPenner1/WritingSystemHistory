-- Not a "production" query, internal use for finding characters to add to the derivations table
SELECT * FROM code_point cp WHERE script_code = ?
AND cp.general_category_code NOT LIKE 'C_' AND cp.general_category_code NOT LIKE 'Z_'
AND cp.id NOT IN (SELECT child_id FROM code_point_derivation)
ORDER BY id
