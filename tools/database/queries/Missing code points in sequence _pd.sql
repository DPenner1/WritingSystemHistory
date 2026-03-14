WITH RECURSIVE code_points_in_seq(seq_id) AS (
	SELECT ?
	UNION ALL
	SELECT item_id
	FROM code_points_in_seq c INNER JOIN sequence_item si ON c.seq_id = si.sequence_id
)
SELECT DISTINCT cp.id, cp.text FROM code_points_in_seq cps
INNER JOIN code_point cp ON cps.seq_id = cp.id
WHERE cp.id NOT IN (SELECT child_id FROM code_point_derivation)
-- shortcut that all base sequences <= 0x10FFFF, more elegant would be checking sequence.type_id = 1
