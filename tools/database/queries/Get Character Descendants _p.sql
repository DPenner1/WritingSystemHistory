-- This query will get weird if there's a diamond inheritance in the data and the two sides of the diamond are different lengths
WITH RECURSIVE descendant(character, name, descendant_level) AS (
    SELECT text, name, 0 FROM code_point WHERE text = ?
    UNION
    SELECT cp2.text, cp2.name, d.descendant_level + 1
    FROM 
        descendant d
	    INNER JOIN code_point cp1 ON d.character = cp1.text
	    INNER JOIN code_point_derivation deriv ON deriv.parent_id = cp1.id 
	    INNER JOIN code_point cp2 ON cp2.id = deriv.child_id
)
SELECT character, name, descendant_level FROM descendant ORDER BY descendant_level 

