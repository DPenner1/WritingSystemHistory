-- Note: This schema favours use of script and language codes over the integer ids - this is simply more readable and more in line with the purposes of this project

CREATE TABLE IF NOT EXISTS sequence_type (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS alphabet_type (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS script_type (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS process_type (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    description TEXT,
    notes TEXT
) STRICT;

CREATE TABLE IF NOT EXISTS sequence (
    id INTEGER PRIMARY KEY,
    type_id INTEGER NOT NULL REFERENCES sequence_type(id)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_seq_type ON sequence(type_id);

-- it's a tree structure
CREATE TABLE IF NOT EXISTS sequence_item (
    sequence_id INTEGER REFERENCES sequence(id) ON DELETE CASCADE,
    order_num INTEGER,
    item_id INTEGER REFERENCES sequence(id),
    PRIMARY KEY (sequence_id, order_num)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_seq_item ON sequence_item(item_id);

CREATE TABLE IF NOT EXISTS source (
    id INTEGER PRIMARY KEY,
    citation_key TEXT UNIQUE NOT NULL,
    parent_id INTEGER REFERENCES source(id),
    authors TEXT,
    title TEXT NOT NULL,
    url TEXT
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_parent_source ON source(parent_id) WHERE parent_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS process_source (
    process_type_id INTEGER REFERENCES process_type(id),
    source_id INTEGER REFERENCES source(id),
    section TEXT,
    access_date INTEGER,
    PRIMARY KEY(process_type_id, source_id)
) STRICT;

CREATE TABLE IF NOT EXISTS script (
    code TEXT PRIMARY KEY,
    iso_id INT UNIQUE NOT NULL,
    name TEXT,
    type_id INTEGER NOT NULL REFERENCES script_type(id),
    u_alias TEXT UNIQUE,
    u_version_added INTEGER,
    u_subversion_added INTEGER,
    canonical_script_code TEXT REFERENCES script(code),
    main_parent_code TEXT REFERENCES script(code),
    main_lang_code TEXT REFERENCES language(code),
    exemplar_sequence_id INTEGER UNIQUE REFERENCES sequence(id)    
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_scr_type ON script(type_id);
CREATE INDEX IF NOT EXISTS idx_fk_main_parent_script ON script(main_parent_code) WHERE main_parent_code IS NOT NULL; 
CREATE INDEX IF NOT EXISTS idx_fk_scr_lang ON script(main_lang_code) WHERE main_lang_code IS NOT NULL;

CREATE TABLE IF NOT EXISTS language (
    code TEXT PRIMARY KEY,
    name TEXT,
    default_script_code TEXT REFERENCES script(code),
    macrolanguage_code TEXT REFERENCES language(code)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_lang_macrolanguage ON language(macrolanguage_code) WHERE macrolanguage_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fk_lang_default_script ON language(default_script_code) WHERE default_script_code;  -- most would have a default script, so indexing null might not be a bad idea

CREATE TABLE IF NOT EXISTS alphabet (
    sequence_id INTEGER REFERENCES sequence(id),
    lang_code TEXT REFERENCES language(code),
    -- These next two can't be NULL - use an applicable special code if needed
    script_code TEXT NOT NULL REFERENCES script(code),
    letter_case TEXT NOT NULL,
    notes TEXT,
    PRIMARY KEY (sequence_id, lang_code)
) STRICT;
-- CREATE UNIQUE INDEX IF NOT EXISTS idxu_alpha_determiners ON alphabet(script_code, letter_case, type_id, lang_code);
-- CREATE INDEX IF NOT EXISTS idx_fk_alpha_source ON alphabet(source_id);

CREATE TABLE IF NOT EXISTS alphabet_source (
    sequence_id INTEGER,
    lang_code TEXT,
    alphabet_type_id INTEGER REFERENCES alphabet_type(id),
    source_id INTEGER REFERENCES source(id),
    section TEXT,
    access_date INTEGER,
    FOREIGN KEY (sequence_id, lang_code) REFERENCES alphabet(sequence_id, lang_code) ON DELETE CASCADE,
    PRIMARY KEY (sequence_id, lang_code, alphabet_type_id)
) STRICT;

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
             id BETWEEN 0x4E00 AND 0x9FFF OR  -- range a bit of a shortcut for these last 2, since we don't have unassigned in this DB
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
    is_independently_graphical INTEGER NOT NULL DEFAULT 1,
    is_lowercase INTEGER NOT NULL DEFAULT 0,
    is_uppercase INTEGER NOT NULL DEFAULT 0,
    raw_name TEXT,
    alt_name TEXT,
    word_count TEXT GENERATED ALWAYS AS (LENGTH(name) - LENGTH(REPLACE(name, ' ', '')) + 1) VIRTUAL
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_cp_script ON code_point(script_code) WHERE script_code <> 'Hani'; -- no point indexing ~2/3 of the table;
CREATE INDEX IF NOT EXISTS idx_cp_general_category ON code_point(general_category_code) WHERE general_category_code <> 'Lo';  -- even more of the table 
CREATE INDEX IF NOT EXISTS idx_fk_cp_equivalent_sequence ON code_point(equivalent_sequence_id) WHERE equivalent_sequence_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fk_cp_simple_lowercase_mapping ON code_point(simple_lowercase_mapping_id) WHERE simple_lowercase_mapping_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_fk_cp_simple_uppercase_mapping ON code_point(simple_uppercase_mapping_id) WHERE simple_uppercase_mapping_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cp_raw_name ON code_point(raw_name) WHERE raw_name IS NOT NULL;

CREATE TABLE IF NOT EXISTS name_indexer (
    code_point_id INTEGER REFERENCES code_point(id),
    order_num INTEGER,
    word TEXT,
    PRIMARY KEY (code_point_id, order_num)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_name_word ON name_indexer(word);

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

-- The established derivations should be a DAG (directed acyclic graph, multiple edges implied via multiplicity)
-- Code point != character/grapheme, but close enough for the purposes of this project
CREATE TABLE IF NOT EXISTS code_point_derivation (
    child_id INTEGER REFERENCES code_point (id),
    parent_id INTEGER REFERENCES code_point (id),
    derivation_type_id INTEGER NOT NULL DEFAULT 1 REFERENCES derivation_type (id),
    certainty_type_id INTEGER NOT NULL DEFAULT -1 REFERENCES certainty_type (id),
    process_type_id INTEGER NOT NULL REFERENCES process_type (id),
    multiplicity INTEGER DEFAULT 1 NOT NULL,
    notes TEXT,
    PRIMARY KEY (child_id, parent_id)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fk_cpd_parent ON code_point_derivation(parent_id); -- This is a table likely to be looked up in either direction child<->parent
CREATE INDEX IF NOT EXISTS idx_fk_cpd_certainty ON code_point_derivation(certainty_type_id);
CREATE INDEX IF NOT EXISTS idx_fk_cpd_process ON code_point_derivation(process_type_id);

CREATE TABLE IF NOT EXISTS manual_derivation_source (
    child_id INTEGER,
    parent_id INTEGER,
    source_id INTEGER REFERENCES source (id),
    section TEXT,
    access_date INTEGER,
    FOREIGN KEY (child_id, parent_id) REFERENCES code_point_derivation (child_id, parent_id) ON DELETE CASCADE,
    PRIMARY KEY (child_id, parent_id, source_id)
) STRICT;
