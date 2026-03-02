-- Note: This schema favours use of script code over the id - this is simply more readable and more in line with the purposes of this project

CREATE TABLE IF NOT EXISTS script (
    code TEXT PRIMARY KEY,
    iso_id INT UNIQUE NOT NULL,
    u_name TEXT UNIQUE,
    u_version_added INTEGER,
    u_subversion_added INTEGER,
    canonical_script_code TEXT REFERENCES script(code)
) STRICT;

CREATE TABLE IF NOT EXISTS sequence_type (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS sequence (
    id INTEGER PRIMARY KEY,
    sequence_type_id INTEGER NOT NULL REFERENCES sequence_type(id)
) STRICT;

CREATE TABLE IF NOT EXISTS code_point (
    id INTEGER PRIMARY KEY REFERENCES sequence(id),
    text TEXT UNIQUE GENERATED ALWAYS AS (CASE WHEN general_category_code IN ('Cn', 'Cs') THEN NULL ELSE CHAR(id) END) STORED,
    name TEXT,
    script_code TEXT NOT NULL DEFAULT 'Zzzz' REFERENCES script (code),
    general_category_code TEXT NOT NULL DEFAULT 'Cn',
    bidi_class_code TEXT NOT NULL DEFAULT 'L',
    simple_uppercase_mapping_id INTEGER REFERENCES code_point(id),
    simple_lowercase_mapping_id INTEGER REFERENCES code_point(id),
    decomposition_id INTEGER REFERENCES sequence(id)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_cp_script_code ON code_point(script_code);
CREATE INDEX IF NOT EXISTS idx_cp_general_category_code ON code_point(general_category_code);
CREATE INDEX IF NOT EXISTS idx_cp_decomposition_id ON code_point(decomposition_id);

-- it's a tree structure
CREATE TABLE IF NOT EXISTS sequence_item (
    sequence_id INTEGER REFERENCES sequence(id),
    item_id INTEGER REFERENCES sequence(id),
    order_num INTEGER,
    PRIMARY KEY (sequence_id, item_id, order_num)
);

CREATE TABLE IF NOT EXISTS alphabet (
    id PRIMARY KEY REFERENCES sequence(id),
    lang_code TEXT,
    script_code TEXT REFERENCES script (code),
    letter_case TEXT,
    is_language_exemplar INTEGER,
    is_script_exemplar INTEGER
);
-- Currently The "standard-issue" database loads this as unique from the CLDR, but in principle alternate/extended alphabets could be added, so non-unique index
CREATE INDEX IF NOT EXISTS idx_lang_script ON alphabet(lang_code, script_code);
CREATE INDEX IF NOT EXISTS idx_script ON alphabet(script_code, is_script_exemplar);


CREATE TABLE IF NOT EXISTS derivation_type (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS certainty_type (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
) STRICT;

-- The established derivations should be a multi-DAG (directed acyclic graph, multiple edges permitted)
-- Code point != character/grapheme, but close enough for the purposes of this project
CREATE TABLE IF NOT EXISTS code_point_derivation (
    child_id INTEGER REFERENCES code_point (id),
    parent_id INTEGER REFERENCES code_point (id),
    derivation_type_id INTEGER NOT NULL DEFAULT 1 REFERENCES derivation_type (id),
    certainty_type_id INTEGER NOT NULL DEFAULT 6 REFERENCES certainty_type (id),
    source TEXT,
    notes TEXT,
    PRIMARY KEY (child_id, parent_id, derivation_type_id)
) STRICT;
-- This is a table likely to be looked up in either direction child<->parent
CREATE INDEX IF NOT EXISTS idx_pk_inverse ON code_point_derivation(parent_id, child_id, derivation_type_id);
