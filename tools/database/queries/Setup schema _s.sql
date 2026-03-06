-- Note: This schema favours use of script code over the id - this is simply more readable and more in line with the purposes of this project

CREATE TABLE IF NOT EXISTS sequence_type (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS sequence (
    id INTEGER PRIMARY KEY,
    type_id INTEGER NOT NULL REFERENCES sequence_type(id)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_s_type ON sequence(type_id);

CREATE TABLE IF NOT EXISTS script (
    code TEXT PRIMARY KEY,
    iso_id INT UNIQUE NOT NULL,
    u_name TEXT UNIQUE,
    u_version_added INTEGER,
    u_subversion_added INTEGER,
    canonical_script_code TEXT REFERENCES script(code),
    exemplar_sequence_id INTEGER UNIQUE REFERENCES sequence(id)    
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_s_exemplar_sequence ON script(exemplar_sequence_id);

CREATE TABLE IF NOT EXISTS alphabet (
    id INTEGER PRIMARY KEY REFERENCES sequence(id),
    source TEXT,
    lang_code TEXT,
    is_language_exemplar INTEGER, -- would make sense to move if there was a language table, similar to script
    script_code TEXT REFERENCES script(code),
    letter_case TEXT
) STRICT;
CREATE INDEX IF NOT EXISTS idx_a_lang ON alphabet(lang_code, is_language_exemplar);
CREATE INDEX IF NOT EXISTS idx_fk_a_script ON alphabet(script_code);

CREATE TABLE IF NOT EXISTS code_point (
    id INTEGER PRIMARY KEY REFERENCES sequence(id),
    text TEXT UNIQUE GENERATED ALWAYS AS (CASE WHEN general_category_code IN ('Cn', 'Cs') THEN NULL ELSE CHAR(id) END) STORED,
    name TEXT,
    script_code TEXT NOT NULL DEFAULT 'Zzzz' REFERENCES script (code),
    general_category_code TEXT NOT NULL DEFAULT 'Cn',
    bidi_class_code TEXT NOT NULL DEFAULT 'L',
    simple_uppercase_mapping_id INTEGER REFERENCES code_point(id),
    simple_lowercase_mapping_id INTEGER REFERENCES code_point(id),
    equivalent_sequence_id INTEGER REFERENCES sequence(id)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_cp_script ON code_point(script_code);
CREATE INDEX IF NOT EXISTS idx_cp_general_category ON code_point(general_category_code);
CREATE INDEX IF NOT EXISTS idx_fk_cp_equivalent_sequence ON code_point(equivalent_sequence_id);
CREATE INDEX IF NOT EXISTS idx_fk_cp_simple_lowercase_mapping ON code_point(simple_lowercase_mapping_id);
CREATE INDEX IF NOT EXISTS idx_fk_cp_simple_uppercase_mapping ON code_point(simple_uppercase_mapping_id);

-- it's a tree structure
CREATE TABLE IF NOT EXISTS sequence_item (
    sequence_id INTEGER REFERENCES sequence(id),
    item_id INTEGER REFERENCES sequence(id),
    order_num INTEGER,
    PRIMARY KEY (sequence_id, item_id, order_num)
) STRICT;

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
CREATE INDEX IF NOT EXISTS idx_cpd_parent_derivation_type ON code_point_derivation(parent_id, derivation_type_id);
