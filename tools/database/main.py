import os
import sqlite3
import re
import csv
from enum import Enum

# dev mode runs data integrity checks and outputs to console
DEV_MODE = False

WORKING_DIRECTORY = '.'

RESOURCE_PATH = os.path.join(WORKING_DIRECTORY, 'resource')
QUERY_PATH = os.path.join(WORKING_DIRECTORY, 'queries')
DERIVATIONS_PATH = os.path.join(RESOURCE_PATH, 'derivations')
CR_EXCLUSION_PATH = os.path.join(RESOURCE_PATH, 'cr-exclusion')
WIKIPEDIA_PATH = os.path.join(RESOURCE_PATH, 'wikipedia-sourced')
UNICODE_PATH = os.path.join(RESOURCE_PATH, 'unicode-data')
GENERATED_DIR_NAME = 'generated'
GENERATED_DERIVATION_PATH = os.path.join(DERIVATIONS_PATH, GENERATED_DIR_NAME)

NO_PARENT = '\uFFFF'  # a Unicode non-character
DEFAULT_DERIVATION = 1

class Certainty(Enum):
    NEAR_CERTAIN = 1
    LIKELY = 2
    UNCERTAIN = 3
    AUTOMATED = 4
    ASSUMED = 5
    UNSPECIFIED = 6

def get_sql_in_str_list(enumerable):
    return "('" + "','".join(enumerable) + "')"

def get_unique_saved_query(name_prefix):
    queries = [f for f in os.listdir(QUERY_PATH) if f.startswith(name_prefix)]

    if len(queries) == 0:
        raise ValueError(f"No query named {name_prefix} found in {QUERY_PATH}")
    elif len(queries) > 1:
        raise ValueError("Multiple matching queries found: " + str(queries))

    return os.path.join(QUERY_PATH, queries[0])

def pretty_print_saved_query(cursor, query_name, parameters=None):
    def print_data_row(row, pads):
        BIDI_STRONG_ISOLATOR = '\u2068'
        BIDI_ISOLATOR_POP = '\u2069'
        print(f'|  {BIDI_STRONG_ISOLATOR}' + f'{BIDI_ISOLATOR_POP}  |  {BIDI_STRONG_ISOLATOR}'.join([r.ljust(p) for r, p in zip(row, pads)]) + BIDI_ISOLATOR_POP + '  |')
    def print_separator_row(bookend_char, pads):
        print(bookend_char + '--' + '--+--'.join(['-' * p for p in pads]) + '--' + bookend_char)

    with open(get_unique_saved_query(query_name)) as file:
        results = cursor.execute(file.read(), parameters).fetchall() if parameters else cursor.execute(file.read()).fetchall()
        header = [x[0].replace('_', ' ').title() for x in cursor.description]
        results = [[str(field) for field in row] for row in results]
        pads = []
        for i in range(len(header)):
            # TODO - this is going to fail miserably in this project with string length != grapheme apparent length
            pads.append(max([len(x[i]) for x in results + [header]]))

        print_separator_row('+', pads)
        print_data_row(header, pads)
        print_separator_row('|', pads)
        for r in results:
            print_data_row(r, pads)
        print_separator_row('+', pads)

def execute_saved_query(cursor, query_name, parameters=None):
    with open(get_unique_saved_query(query_name)) as file:
        return cursor.execute(file.read(), parameters).fetchall() if parameters else cursor.execute(file.read()).fetchall()

def setup_schema(cursor):

    # Note: This schema frequently favours use of text codes over integers - this is simply more readable and more in line with the purposes of this project
    #       This can change in the future field-by-field as deemed necessary (eg. if a lookup gets created for them; they are of a similar format with an integer id)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS script (
            code TEXT PRIMARY KEY,
            iso_id INT UNIQUE NOT NULL,
            u_name TEXT UNIQUE,
            u_version_added INTEGER,
            u_subversion_added INTEGER
        ) STRICT""")

    # TODO - separate out std_order_num
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS code_point (
            id INTEGER PRIMARY KEY,
            text TEXT UNIQUE,
            name TEXT,
            script_code TEXT NOT NULL DEFAULT 'Zzzz' REFERENCES script (code),
            general_category_code TEXT NOT NULL DEFAULT 'Cn',
            bidi_class_code TEXT NOT NULL DEFAULT 'L',
            simple_uppercase_mapping_id INTEGER REFERENCES code_point(id),
            simple_lowercase_mapping_id INTEGER REFERENCES code_point(id),
            decomposition_type TEXT,
            std_order_num INTEGER
        ) STRICT""")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fk_script_code ON code_point(script_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_general_category_code ON code_point(general_category_code)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decomposition_mapping (
            code_point_id INTEGER REFERENCES code_point (id),
            decomposition_id INTEGER REFERENCES code_point (id),
            order_num INTEGER,
            PRIMARY KEY (code_point_id, decomposition_id, order_num)
        ) STRICT""")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS derivation_type (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            description TEXT
        ) STRICT""")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certainty_type (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            description TEXT
        ) STRICT""")

    # The established derivations should be a multi-DAG (directed acyclic graph, multiple edges permitted)
    # Code point != character/grapheme, but close enough for the purposes of this project
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS code_point_derivation (
            child_id INTEGER REFERENCES code_point (id),
            parent_id INTEGER REFERENCES code_point (id),
            derivation_type_id INTEGER NOT NULL DEFAULT 1 REFERENCES derivation_type (id),
            certainty_type_id INTEGER NOT NULL DEFAULT 6 REFERENCES certainty_type (id),
            source TEXT,
            notes TEXT,
            PRIMARY KEY (child_id, parent_id, derivation_type_id)
        ) STRICT""")
    # This is a table likely to be looked up in either direction child<->parent
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pk_inverse ON code_point_derivation(parent_id, child_id, derivation_type_id)")

def load_scripts(cursor):
    # see https://www.unicode.org/iso15924/iso15924-codes.html
    with open(os.path.join(RESOURCE_PATH, 'iso15924.csv'), 'r') as file:
        for row in csv.DictReader(file):
            code = row['Code']
            id = int(row['ISO ID'])
            name = row['Unicode Alias'] if row['Unicode Alias'] else None
            version = row['Unicode Version'] if row['Unicode Version'] else None
            subversion = row['Unicode Subversion'] if row['Unicode Subversion'] else None
            cursor.execute("""
                INSERT INTO script (code, u_name, iso_id, u_version_added, u_subversion_added) 
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (code) DO UPDATE SET
                    u_name = ?,
                    u_version_added = ?,
                    u_subversion_added = ?""",
                (code, name, id, version, subversion, name, version, subversion)) # TODO: check stability policy

def update_code_point(cursor, id, name, general_category, bidi_class, upper_mapping, lower_mapping, decom_str):
    decom_pattern = re.compile(r'^(?:<([a-zA-Z]+)> )?([\s0-9A-F]+)$')
    decom_type = None
    decom_ids = []

    if decom_str:
        match = decom_pattern.match(decom_str)
        decom_ids = [int(id, 16) for id in match.group(2).split(' ')]
        decom_type = match.group(1) if match.group(1) else 'canonical'

    cursor.execute("""
        UPDATE code_point
        SET 
            name = ?,
            general_category_code = ?,
            bidi_class_code = ?,
            simple_uppercase_mapping_id = ?,
            simple_lowercase_mapping_id = ?,
            decomposition_type = ?
        WHERE id = ?""",
        (name, general_category, bidi_class, upper_mapping, lower_mapping, decom_type, id))

    for i, decom_id in enumerate(decom_ids):
        cursor.execute("""
            INSERT INTO decomposition_mapping (code_point_id, decomposition_id, order_num)
            VALUES (?, ?, ?)
            ON CONFLICT DO NOTHING""",  # stability policy, these won't change
            (id, decom_id, i + 1))  # 1-index order number (I don't foresee a particular use for it in this project anyway)

def load_code_point_data(cursor):
    pattern = re.compile(r'^([0-9A-F]+)(?:\.\.([0-9A-F]+))?\s*; ([_a-zA-Z]+) #')

    cursor.execute("INSERT INTO code_point (id, text, name, bidi_class_code) VALUES (?, ?, 'NO PARENT CHARACTER', 'Bn') ON CONFLICT DO NOTHING", (ord(NO_PARENT), NO_PARENT))

    with open(os.path.join(UNICODE_PATH, 'Scripts.txt'), 'r') as file:
        for line in file:
            if not line.isspace() and not line.startswith('#'):
                match = pattern.match(line)
                start = int(match.group(1), 16)
                end = int(match.group(2), 16) if match.group(2) else start
                script_name = match.group(3)
                script_code = cursor.execute("SELECT code FROM script WHERE u_name = ?", (match.group(3),)).fetchone()[0]

                for i in range(start, end + 1):
                    cursor.execute("""
                        INSERT INTO code_point (id, text, script_code) 
                        VALUES (?, ?, ?)
                        ON CONFLICT (id) DO NOTHING""",
                        (i, chr(i), script_code)) # TODO: double check stability policy

    with open(os.path.join(UNICODE_PATH, 'UnicodeData.txt'), 'r') as csvfile:
        special_name_pattern = re.compile('^<(.+)>$')
        in_range = False

        for line in csv.reader(csvfile, delimiter=';'):

            if in_range:
                for i in range(code_point + 1, int(line[0], 16) + 1):
                    # TODO: this is not strictly conforming for Hangul
                    update_code_point(cursor, i, name + '-' + hex(i)[2:].upper(), general_category, bidi_class, upper_mapping, lower_mapping, decom_str)
                in_range = False
            else:
                name = None
                match = special_name_pattern.match(line[1])
                if match:
                    parts = match.group(1).split(',')
                    if len(parts) > 1:
                        name = parts[0].strip().upper()
                        if 'SURROGATE' in name or 'PRIVATE' in name:
                            continue  # we aren't cataloguing these ranges
                        in_range = True
                else:
                    name = line[1]

                code_point = int(line[0], 16)
                decom_str = line[5]
                general_category = line[2] if line[2] else None
                bidi_class = line[4] if line[4] else None
                upper_mapping = int(line[12], 16) if line[12] else None
                lower_mapping = int(line[13], 16) if line[13] else None

                update_code_point(cursor, code_point, name + '-' + line[0] if in_range else name, general_category, bidi_class, upper_mapping, lower_mapping, decom_str)

    cursor.execute("UPDATE code_point SET std_order_num = NULL")
    with open(os.path.join(RESOURCE_PATH, 'standard_alphabets.csv'), 'r') as file:
        for row in csv.DictReader(file):
            for i, c in enumerate(row['Alphabet']):
                cursor.execute("UPDATE code_point SET std_order_num = ? WHERE text = ?", (i + 1, c))  # 1-index for readability
    with open(os.path.join(RESOURCE_PATH, GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'r') as file:
        for row in csv.DictReader(file):
            for i, c in enumerate(row['Alphabet']):
                cursor.execute("UPDATE code_point SET std_order_num = ? WHERE text = ?", (i + 1, c))  # 1-index for readability


def load_lookups(cursor):
    def load_lookup(cursor, table_name, lookup_data):
        for lu in lookup_data:
            cursor.execute(
                f"INSERT INTO {table_name} (id, name, description)" + """
                VALUES (?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET name = ?, description = ?""",
                (lu[0], lu[1], lu[2], lu[1], lu[2]))

    data = [
        (DEFAULT_DERIVATION, "Derivation", "Standard/default/non-specific"),
        (2, "Portion copy", "Child is a copy of a portion of the parent, allowing for stretch-distortion due to size change"),
        (3, "Simplification", "Child is a simplification of parent"),
        (4, "From cursive", "Child is derived from cursive form of the parent (who is typically non-cursive)"),
        (5, "Copy", "Child is a copy of the parent"), # Generally either child script copying or lowercase just a small version of uppercase
        (6, "Duplicate", "Child is a duplicate of the parent"), # Unicode duplicate code points
        (7, "Portion derivation", "Child is a derivation from a portion of the parent"),
        (8, "Rotation", "Child is a rotation of the parent"),
        (9, "Reflection", "Child is a reflection of the parent")]
    load_lookup(cursor, 'derivation_type', data)

    # For this project, sourcing is generally just for the derivation fact, not necessarily for derivation type
    # Even having this feels like overkill, but I was mostly specifying it in Notes anyways and the special values (4+) are useful in the code
    data = [
        (Certainty.NEAR_CERTAIN.value, "Near Certain", "Sources almost all agree, or disagreeing sources are suspect"),
        (Certainty.LIKELY.value, "Likely", "Sources mostly agree, or a singular weak source"), # For the purposes of this project, Wikipedia does not automatically count as a weak: it usually cites other sources
        (Certainty.UNCERTAIN.value, "Uncertain", "Sources disagree or are hesitant"),
        (Certainty.AUTOMATED.value, "Automated", "Derived without manual review, usually from Unicode Consortium data"),
        (Certainty.ASSUMED.value, "Assumed", "Derivation assumed, usually by sound value and/or glyph similarity"),
        (Certainty.UNSPECIFIED.value, "Unspecified", "Not specified in data files - this is a missing data error")]
    load_lookup(cursor, 'certainty_type', data)

def load_derivations(cursor, verify_script):
    copy_decompositions = {'noBreak', 'small', 'sub', 'super'}
    def resolve_default(defaults_dict, script, data_row, field, overriding_default=None, override_condition=False, last_resort=None):
        if field in data_row and data_row[field] and not data_row[field].isspace():
            return data_row[field].strip()
        if override_condition:
            return overriding_default
        if script in defaults_dict and field in defaults_dict[script] and defaults_dict[script][field]:
            return defaults_dict[script][field]
        return last_resort

    # Mende Kikakui is a bit of an exception here: Unicode Encoding Proposal suggests Vai-derived characters are a small minority
    # Not including Chinese here: ideally will eventually do so for Oracle bone
    independent_scripts = {'Mend','Egyp','Lina','Hluw','Xsux','Xpeo','Ogam','Elba','Dupl','Sgnw','Shaw','Vith','Vaii','Bamu','Berf','Nkoo','Wara','Gonm','Toto'
                           'Osma','Adlm','Gara','Medf','Bass','Yezi','Tnsa','Olck','Thaa','Tols','Nagm','Sora','Wcho','Mroo','Onao','Sunu','Yiii','Tang'}

    pattern = re.compile(r'^U\+([0-9A-F]+)\tkTraditionalVariant\tU\+([0-9A-F]+)')

    cursor.execute("DELETE FROM code_point_derivation")  # updates generally expected on this table, just clear

    # Identify all the independently-derived characters
    cursor.execute(f"""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, notes)
            SELECT id, ?, ?, ?, 'Independent script: Assume independent character'
            FROM code_point 
            WHERE script_code IN {get_sql_in_str_list(independent_scripts)}""", (ord(NO_PARENT), DEFAULT_DERIVATION, Certainty.AUTOMATED.value))

    # add derivations from decomposition mappings, assuming the decomposed characters are the base building blocks (the parent)
    # Formatting/control/space characters are not eligible
    cursor.execute(f"""
        INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
        SELECT
            code_point_id,
            decomposition_id,
            CASE WHEN COUNT(decomposition_id) OVER (PARTITION BY code_point_id) = 1
                THEN CASE WHEN cp1.decomposition_type = 'canonical' THEN 6
                          WHEN cp1.decomposition_type IN {get_sql_in_str_list(copy_decompositions)} THEN 5
                          ELSE ?
                     END
                ELSE ?
            END,
            ?,
            'Unicode Character Database decomposition data'
        FROM
            decomposition_mapping dm
            INNER JOIN code_point cp1 ON cp1.id = dm.code_point_id
            INNER JOIN code_point cp2 ON cp2.id = dm.decomposition_id
        WHERE 
            cp1.general_category_code NOT LIKE 'Z_'
            AND cp1.general_category_code NOT LIKE 'C_'
            AND cp2.general_category_code NOT LIKE 'Z_'
            AND cp2.general_category_code NOT LIKE 'C_'
        ON CONFLICT DO NOTHING""", (DEFAULT_DERIVATION, DEFAULT_DERIVATION, Certainty.AUTOMATED.value))
    # conflicts expected when a character decomposes into multiple copies of a code point,
    # minimal enough that this is probably the better query option than advance filtering

    # add derivations from case mapping, assuming lowercase to be derived from uppercase
    cursor.execute("""
        INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
        SELECT id, simple_uppercase_mapping_id, ?, ?, 'Unicode Character Database case mapping data'
        FROM code_point
        WHERE simple_uppercase_mapping_id IS NOT NULL""",
        (DEFAULT_DERIVATION, Certainty.AUTOMATED.value))
    # casing isn't 100% 1:1 so need to do mappings in both directions
    cursor.execute("""
        INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
        SELECT simple_lowercase_mapping_id, id, ?, ?, 'Unicode Character Database case mapping data'
        FROM code_point cp1
        WHERE id <> (SELECT simple_uppercase_mapping_id FROM code_point cp2 WHERE cp2.id = cp1.simple_lowercase_mapping_id)""",
        (DEFAULT_DERIVATION, Certainty.AUTOMATED.value))

    with open(os.path.join(UNICODE_PATH, 'Unihan_Variants.txt'), 'r') as file:
        for line in file:
            if not line.isspace() and not line.startswith('#'):
                match = pattern.match(line)
                if match:
                    child = int(match.group(1), 16)
                    parent = int(match.group(2), 16)

                    if child != parent: # it's possible for a simplified character to map to itself
                        cursor.execute("""
                            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
                            VALUES (?, ?, ?, ?, ?)""",
                            (child, parent, 3, Certainty.AUTOMATED.value, 'Unihan Database'))

    defaults = {}
    with open(os.path.join(DERIVATIONS_PATH, 'defaults.csv'), 'r') as file:
        for row in csv.DictReader(file):
            defaults[row['Script'].strip()] = {
                'Source' : row['Source'].strip(),
                'Derivation Type' : row['Derivation Type'].strip(),
                'Certainty Type': row['Certainty Type'].strip()
            }

    script_files = (  # generated files first allows manual overrides (untested)
        [os.path.join(GENERATED_DERIVATION_PATH, f) for f in os.listdir(GENERATED_DERIVATION_PATH)]
        + [os.path.join(DERIVATIONS_PATH, f) for f in os.listdir(DERIVATIONS_PATH) if f not in ('defaults.csv', GENERATED_DIR_NAME)])

    for script_file in script_files:
        script = script_file.split(os.path.sep)[-1].split('.')[0]
        with open(script_file, 'r') as file:
            for row in csv.DictReader(file):
                child = row['Child'].strip()
                parents = row['Parent'].strip() if row['Parent'] else NO_PARENT  # This won't be in the defaults dictionary

                # Logic for defaulting to Uncertain on no parent: For historical scripts, this is usually more a function of a lack of records
                # For modern scripts, the inventor is generally aware of existing writing systems, and may have been inspired
                certainty = int(resolve_default(defaults, script, row, 'Certainty Type',
                                                overriding_default = str(Certainty.UNCERTAIN.value),
                                                override_condition = (parents == NO_PARENT),
                                                last_resort = str(Certainty.UNSPECIFIED.value)))

                # Overriding default here is for convenience: An Assumed certainty means there is no source, so allows us to specify a source in defaults for all else.
                source = resolve_default(defaults, script, row, 'Source', overriding_default = None, override_condition = (certainty == Certainty.ASSUMED.value))

                notes = resolve_default(defaults, script, row, 'Notes')
                derivation_types = resolve_default(defaults, script, row, 'Derivation Type', last_resort = str(DEFAULT_DERIVATION))

                # ensure that child character is always the expected script
                if verify_script:
                    script_in_file = cursor.execute("SELECT u_name FROM code_point cp INNER JOIN script s ON s.code = cp.script_code WHERE text = ?", child).fetchone()[0]
                    if script != script_in_file:
                        raise ValueError(f"resource file error in {script}.csv with child character {child} detected to be {script_in_file} instead")

                for parent in parents.split('/'):
                    if verify_script:
                        if child == parent:
                            raise ValueError("Attempted to add self-derivation of " + child)
                        if cursor.execute("SELECT * FROM code_point_derivation WHERE parent_id = ? AND child_id = ?", (ord(child), ord(parent))).fetchall():
                            raise ValueError("Attempted to add a 2-cycle with " + child + " and " + parent)

                    # File-specified data overrides the automatically generated data
                    cursor.execute("DELETE FROM code_point_derivation WHERE parent_id = ? AND child_id = ? AND certainty_type_id = ?", (ord(parent), ord(child), Certainty.AUTOMATED.value))

                    for derivation_type in derivation_types.split('/'):
                        cursor.execute("""
                            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source, notes)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                            ( ord(child), ord(parent), int(derivation_type), certainty, source, notes ))

def get_code_to_script_dict(cursor):
    retval = {}
    results = cursor.execute("SELECT code, u_name FROM script WHERE u_name IS NOT NULL").fetchall()
    for row in results:
        retval[row[0]] = row[1]
    return retval

def generate_data(code_to_script_dict, verify=False):
    indic_order = ['Ka', 'Kha', 'Ga', 'Gha', 'Ṅa', 'Ca', 'Cha', 'Ja', 'Jha', 'Ña', 'Ṭa', 'Ṭha', 'Ḍa', 'Ḍha', 'Ṇa', 'Ta',
                   'Tha', 'Da', 'Dha', 'Na', 'Pa', 'Pha', 'Ba', 'Bha', 'Ma', 'Ya', 'Ra', 'La', 'Va', 'Śa', 'Ṣa', 'Sa',
                   'Ha', 'A', 'Ā', 'I', 'Ī', 'U', 'Ū', 'Ṛ', 'Ṝ', 'Ḷ', 'Ḹ', 'E', 'Ai', 'O', 'Au']

    # kawi is one of the newer scripts added to Unicode, so explains why wikipedia generally did not list the code point
    equivalents = {
        # kawi vowels were not included in any of the charts, may fill in manually later
        'kawi': ['𑼒','𑼓','𑼔','𑼕','𑼖','𑼗','𑼘','𑼙','𑼚','𑼛','𑼜','𑼝','𑼞','𑼟','𑼠','𑼡','𑼢','𑼣','𑼤','𑼥','𑼦','𑼧','𑼨','𑼩','𑼪','𑼫','𑼬','𑼭','𑼮','𑼯','𑼰','𑼱','𑼲','','','','','','','','','','','','','','']
    }

    def generate_indic_letter_data(letter, deriv_data):
        # Aramaic, Brahmi and Kharoshti which will be manually specified due to additional sources available and the Aramaic code point not generally being included
        # Can abo, Hangul, Kayah Li, Masaram Gondi, Sorang Sompeng, Pau cin hau will be manually specified due to higher independence or contribution from other scripts
        # Soyombo excluded due to elevated probability of script relationships being modified
        # Non-unicode scripts Gupta, Ranjana, Pallava, Tocharian, 'asho', 'kush' excluded
        excluded_codes = ['brah','khar','hang','cans','kali','soyo','gonm','sora','pauc','gupt','plav','ranj','armi','asho','kush','toch']
        script_parents = {
            'kawi': 'brah',
            'tibt': 'brah',
            'bhks': 'brah',
            'sidd': 'brah',
            'shrd': 'brah',
            'deva': 'sidd',
            'beng': 'sidd',
            'telu': 'brah',
            'orya': 'sidd',
            'knda': 'brah',
            'mlym': 'gran',
            'gujr': 'sidd',
            'gran': 'brah',
            'phag': 'tibt',
            'zanb': 'phag',
            'newa': 'sidd',
            'mymr': 'brah',
            'khmr': 'brah',
            'laoo': 'khmr',
            'thai': 'khmr',
            'ahom': 'mymr',
            'modi': 'sidd',
            'nand': 'sidd',
            'sylo': 'kthi',
            'kthi': 'sidd',
            'tirh': 'sidd',
            'lepc': 'tibt',
            'limb': 'lepc',
            'mtei': 'tibt',
            'marc': 'tibt',
            'takr': 'shrd',
            'dogr': 'takr',
            'khoj': 'shrd',
            'sind': 'shrd',
            'mahj': 'shrd',
            'mult': 'shrd',
            'bali': 'kawi',
            'batk': 'kawi',
            'bugi': 'kawi',
            'java': 'kawi',
            'rjng': 'kawi',
            'sund': 'kawi',
            'tglg': 'kawi',
            'tagb': 'tglg',
            'hano': 'tglg',
            'buhd': 'tglg',
            'guru': 'shrd',
            'lana': 'mymr',
            'talu': 'lana',
            'tavt': 'khmr',
            'sinh': 'gran',
            'cakm': 'mymr',
            'gong': 'sidd',
            'maka': 'kawi',
            'taml': 'brah',
            'tale': 'mymr',
            'saur': 'gran',
            'cham': 'brah',
            'diak': 'gran',
        }
        hex_pattern = re.compile('^[0-9A-F]+$')

        with open(os.path.join(WIKIPEDIA_PATH, 'indic-letters', letter + '.txt'), 'r') as file:
            wdata = {}
            for match in re.findall(r'\|\s*([a-z0-9]+)(cp|img)\s*=([^\|]+)', file.read()):
                if match[0] not in wdata or match[1] == 'cp':  # code point overrides image
                    value = match[2].strip()
                    if '&#x' in value:
                        value = value[value.index('x')+1:]
                    wdata[match[0]] = value

            for id in wdata:
                script_code = id[0:4] # a few have multiple copies indicated by appended numbers
                value = wdata[id]
                if script_code not in excluded_codes:
                    character = None
                    if hex_pattern.match(value):
                        character = chr(int(value, 16))
                    elif script_code in equivalents:
                        character = equivalents[script_code][indic_order.index(letter)]

                    if character:
                        if script_code in script_parents:
                            parent_script = script_parents[script_code]
                            if not parent_script + '2' in wdata:  # likely at least one is incorrect, don't attempt automatic derivation
                                if script_code not in script_deriv_data:
                                    deriv_data[script_code] = list()

                                if parent_script in wdata:
                                    if hex_pattern.match(wdata[parent_script]):
                                        deriv_data[script_code].append((character, chr(int(wdata[parent_script], 16))))
                                    elif parent_script in equivalents:
                                        equiv = equivalents[parent_script][indic_order.index(letter)]
                                        if equiv:
                                            deriv_data[script_code].append((character, equiv))
                                    elif verify: print(f'Data generation error: No code point found for parent of script {script_code} character {character}')
                                else:
                                    deriv_data[script_code].append((character, ''))
                            # temporary warning pending manual review
                            elif verify: print(f'Data generation warning: Multiple possible parents for script {script_code} character {character}')
                        elif verify: print(f'Data generation error: Parent of script {script_code} is not specified')
                    elif verify: print(f'Data generation error: Character not found for script {script_code}, generic indic letter {letter}')

    # Clear existing data first
    for file in os.listdir(GENERATED_DERIVATION_PATH):
        os.remove(os.path.join(GENERATED_DERIVATION_PATH, file))

    script_deriv_data = {}

    for l in indic_order:
        generate_indic_letter_data(l, script_deriv_data)

    with open(os.path.join(RESOURCE_PATH, GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'w') as file:
        file.write('Script,Alphabet')

    for script in script_deriv_data:
        script_name = code_to_script_dict[script.title()]
        with open(os.path.join(RESOURCE_PATH, GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'a') as file:
            file.write('\n' + script_name + ',')
            for deriv in script_deriv_data[script]:
                file.write(deriv[0])

        with open(os.path.join(GENERATED_DERIVATION_PATH, script_name + '.csv'), 'w') as file:
            file.write('Child,Parent,Derivation Type,Certainty Type,Source,Notes\n')
            for deriv in script_deriv_data[script]:
                if deriv[1]:
                    file.write(f'{deriv[0]},{deriv[1]},{DEFAULT_DERIVATION},{Certainty.AUTOMATED.value},Wikipedia Indic letter cognate charts,Not necessarily graphical derivation but likely\n')

def verify_script_coverage(cursor):
    def verify_script(script):
        missing_chars = cursor.execute("""
            SELECT cp.text FROM code_point cp INNER JOIN script s ON s.code = cp.script_code WHERE s.u_name = ? AND cp.std_order_num IS NOT NULL
            EXCEPT
            SELECT cp.text
            FROM 
                code_point_derivation cpd
                INNER JOIN code_point cp ON cpd.child_id = cp.id
                INNER JOIN script s ON s.code = cp.script_code
            WHERE s.u_name = ?""",
            (script, script)).fetchall()

        # Incomplete data not necessarily an error, we just output to audit it
        num_missing = len(missing_chars)
        if (num_missing > 0):
            message = f"{script.ljust(pad)}|  {f'{num_missing} characters' if num_missing >= 12 else ", ".join([i[0] for i in missing_chars])}"
            print(message)

    pad = 22
    table_header = 'Script'.ljust(pad) + '|  Missing derivations from standard alphabet'
    print('-' * pad + '+' + '-' * (len(table_header) - pad))
    print(table_header)
    print('-' * pad + '+' + '-' * (len(table_header) - pad))

    with open(os.path.join(RESOURCE_PATH, 'standard_alphabets.csv'), 'r') as csvfile:
        for row in csv.DictReader(csvfile):
            verify_script(row['Script'])
    with open(os.path.join(RESOURCE_PATH, GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'r') as csvfile:
        for row in csv.DictReader(csvfile):
            verify_script(row['Script'])

# dev mode runs additional checks and outputs some data to console
def load_database(con, dev_mode=False):
    cur = con.cursor()

    if dev_mode:
        cur.execute("PRAGMA foreign_keys = ON")
    else:
        cur.execute("PRAGMA foreign_keys = OFF")
    
    setup_schema(cur)

    load_lookups(cur)
    con.commit()

    load_scripts(cur)
    con.commit()

    generate_data(get_code_to_script_dict(cur), dev_mode) # this requires script data already being loaded

    load_code_point_data(cur)
    con.commit()

    load_derivations(cur, dev_mode)
    con.commit()

    if dev_mode:
        verify_script_coverage(cur)
        pretty_print_saved_query(cur, 'Total derivation statistics')
    else:
        cur.execute("PRAGMA foreign_keys = ON")

    return cur

if __name__ == '__main__':
    con = sqlite3.connect('scripts.db')
    cursor = load_database(con, dev_mode=DEV_MODE)

    # do stuff here if you want, for example:
    # pretty_print_saved_query(cursor, 'Get Character Ancestors', 'a')

    cursor.close()