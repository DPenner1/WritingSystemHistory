-- This query will get weird if there's a diamond inheritance in the data and the two sides of the diamond are different lengths
WITH RECURSIVE ancestor(character, name, ancestor_level) AS (
    SELECT text, name, 0 FROM code_point WHERE text = ?
    UNION
    SELECT cp2.text, cp2.name, a.ancestor_level + 1
    FROM 
        ancestor a
	    INNER JOIN code_point cp1 ON a.character = cp1.text
	    INNER JOIN code_point_derivation deriv ON deriv.child_id = cp1.id 
	    INNER JOIN code_point cp2 ON cp2.id = deriv.parent_id
)
SELECT character, name, ancestor_level FROM ancestor ORDER BY ancestor_level 

