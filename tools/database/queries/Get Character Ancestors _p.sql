WITH RECURSIVE ancestor(character, name, ancestor_level) AS (
    SELECT text, name, 0 FROM code_point WHERE text = ?
    UNION ALL
    SELECT cp2.text, cp2.name, a.ancestor_level + 1
    FROM 
        ancestor a
	    INNER JOIN code_point cp1 ON a.character = cp1.text
	    INNER JOIN code_point_derivation deriv ON deriv.child_id = cp1.id 
	    INNER JOIN code_point cp2 ON cp2.id = deriv.parent_id
)
SELECT DISTINCT character, name, MIN(ancestor_level) OVER (PARTITION BY character) AS ancestor_level FROM ancestor ORDER BY ancestor_level, name 

