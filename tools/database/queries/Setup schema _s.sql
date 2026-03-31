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

-- it's a tree structure
CREATE TABLE IF NOT EXISTS sequence_item (
    sequence_id INTEGER REFERENCES sequence(id),
    item_id INTEGER REFERENCES sequence(id),
    order_num INTEGER,
    PRIMARY KEY (sequence_id, item_id, order_num)
) STRICT;

CREATE TABLE IF NOT EXISTS script (
    code TEXT PRIMARY KEY,
    iso_id INT UNIQUE NOT NULL,
    name TEXT,
    u_alias TEXT UNIQUE,
    u_version_added INTEGER,
    u_subversion_added INTEGER,
    canonical_script_code TEXT REFERENCES script(code),
    exemplar_sequence_id INTEGER UNIQUE REFERENCES sequence(id)    
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_s_exemplar_sequence ON script(exemplar_sequence_id) WHERE exemplar_sequence_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS language (
    code TEXT PRIMARY KEY,
    name TEXT,
    default_script_code TEXT REFERENCES script(code),
    macrolanguage_code TEXT REFERENCES language(code)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_l_macrolanguage ON language(macrolanguage_code) WHERE macrolanguage_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fk_l_default_script ON language(default_script_code) WHERE default_script_code IS NOT NULL;

CREATE TABLE IF NOT EXISTS alphabet (
    id INTEGER PRIMARY KEY REFERENCES sequence(id),
    source TEXT,
    lang_code TEXT REFERENCES language(code),
    is_language_exemplar INTEGER, -- This could be on the language table, but then there's some mutually referencing stuff I need to work out the impact for
    script_code TEXT REFERENCES script(code),
    letter_case TEXT
) STRICT;
CREATE INDEX IF NOT EXISTS idx_a_lang ON alphabet(lang_code, is_language_exemplar);
CREATE INDEX IF NOT EXISTS idx_fk_a_script ON alphabet(script_code);

CREATE TABLE IF NOT EXISTS code_point (
    id INTEGER PRIMARY KEY REFERENCES sequence(id),
    text TEXT UNIQUE GENERATED ALWAYS AS (CASE WHEN general_category_code IN ('Cn', 'Cs') THEN NULL ELSE CHAR(id) END) STORED,
    name TEXT GENERATED ALWAYS AS (CASE  -- space saving measure (see Unicode Standard 4.8)
        WHEN alt_name IS NOT NULL THEN alt_name
        WHEN general_category_code = 'Cs' THEN NULL  -- The non-parent character is not conforming right now...
        WHEN id BETWEEN 0xAC00 AND 0xD7A3 THEN CONCAT('HANGUL SYLLABLE ', raw_name)
        WHEN id BETWEEN 0x13460 AND 0x143FA THEN CONCAT('EGYPTIAN HIEROGLYPH-', printf('%X', id))
        WHEN id BETWEEN 0x17000 AND 0x187F7 OR 
             id BETWEEN 0x18D00 AND 0x18D1E THEN CONCAT('TANGUT IDEOGRAPH-', printf('%X', id))
        WHEN id BETWEEN 0x18B00 AND 0x18CD5 THEN CONCAT('KHITAN SMALL SCRIPT CHARACTER-', printf('%X', id))
        WHEN id BETWEEN 0x1B170 AND 0x1B2FB THEN CONCAT('NUSHU CHARACTER-', printf('%X', id))
        WHEN id BETWEEN 0xF900 AND 0xFA6D OR
             id BETWEEN 0xFA70 AND 0XFAD9 OR
             id BETWEEN 0x2F800 AND 0x2FA1D THEN CONCAT('CJK COMPATIBILITY IDEOGRAPH-', printf('%X', id))
        WHEN id BETWEEN 0x3400 AND 0x4DBF OR
             id BETWEEN 0x4E00 AND 0x9FFF OR  -- range a bit of a shortcut, since we don't have unassigned in this DB
             id BETWEEN 0x20000 AND 0x33FFF THEN CONCAT('CJK UNIFIED IDEOGRAPH-', printf('%X', id))
        WHEN id BETWEEN 0x3D000 AND 0x3FFFD THEN CONCAT('SEAL CHARACTER-', printf('%X', id)) --anticipatory
        ELSE raw_name END) VIRTUAL,
    script_code TEXT NOT NULL DEFAULT 'Zzzz' REFERENCES script (code),
    general_category_code TEXT NOT NULL DEFAULT 'Cn',
    bidi_class_code TEXT NOT NULL DEFAULT 'L',
    simple_uppercase_mapping_id INTEGER REFERENCES code_point(id),
    simple_lowercase_mapping_id INTEGER REFERENCES code_point(id),
    equivalent_sequence_id INTEGER REFERENCES sequence(id),
    is_alphabetic INTEGER NOT NULL DEFAULT 0,
    is_lowercase INTEGER NOT NULL DEFAULT 0,
    is_uppercase INTEGER NOT NULL DEFAULT 0,
    raw_name TEXT,
    alt_name TEXT
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_cp_script ON code_point(script_code) WHERE script_code <> 'Hani'; -- no point indexing ~2/3 of the database;
CREATE INDEX IF NOT EXISTS idx_cp_general_category ON code_point(general_category_code) WHERE general_category_code <> 'Lo';  -- even more of the DB 
CREATE INDEX IF NOT EXISTS idx_fk_cp_equivalent_sequence ON code_point(equivalent_sequence_id) WHERE equivalent_sequence_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fk_cp_simple_lowercase_mapping ON code_point(simple_lowercase_mapping_id) WHERE simple_lowercase_mapping_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fk_cp_simple_uppercase_mapping ON code_point(simple_uppercase_mapping_id) WHERE simple_uppercase_mapping_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cp_raw_name ON code_point(raw_name) WHERE raw_name IS NOT NULL;

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
    multiplicity INTEGER DEFAULT 1,
    source TEXT,
    notes TEXT,
    PRIMARY KEY (child_id, parent_id)
) STRICT;
-- This is a table likely to be looked up in either direction child<->parent
CREATE INDEX IF NOT EXISTS idx_cpd_parent_derivation_type ON code_point_derivation(parent_id);
