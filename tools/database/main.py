import os
import sqlite3
import re
import csv

RESOURCE_PATH = os.path.join('.', 'resource')
DERIVATIONS_PATH = os.path.join(RESOURCE_PATH, 'derivations')
CR_EXCLUSION_PATH = os.path.join(RESOURCE_PATH, 'cr-exclusion')
WIKIPEDIA_PATH = os.path.join(RESOURCE_PATH, 'wikipedia-sourced')
GENERATED_DIR_NAME = 'generated'

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
            script_code TEXT NOT NULL DEFAULT 'Zzzz' REFERENCES script (code),
            general_category_code TEXT NOT NULL DEFAULT 'C',
            bidi_class_code TEXT NOT NULL DEFAULT 'ON',
            simple_uppercase_mapping_id INTEGER REFERENCES code_point(id),
            simple_lowercase_mapping_id INTEGER REFERENCES code_point(id),
            decomposition_type TEXT,  
            std_order_num INTEGER
        ) STRICT""")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fk_script_code ON code_point(script_code)")

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
    # Code point != character, but close enough for the purposes of this project
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

def load_code_point_data(cursor):
    pattern = re.compile(r'^([0-9A-F]+)(?:\.\.([0-9A-F]+))?\s*; ([_a-zA-Z]+) #')

    with open(os.path.join(CR_EXCLUSION_PATH, 'Scripts.txt'), 'r') as file:
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

    with open(os.path.join(CR_EXCLUSION_PATH, 'UnicodeData.txt'), 'r') as csvfile:
        decom_pattern = re.compile(r'^(?:<([a-zA-Z]+)> )?([\s0-9A-F]+)$')

        for line in csv.reader(csvfile, delimiter=';'):
            code_point = int(line[0], 16)
            decom_type = None
            decom_ids = []
            if line[5]:
                match = decom_pattern.match(line[5])
                decom_ids = [int(id, 16) for id in match.group(2).split(' ')]
                if match.group(1): # a compatibility match
                    decom_type = match.group(1)
                elif len(decom_ids) == 1:
                    decom_type = 'singleton'
                else:
                    decom_type = 'canonical'

            cursor.execute("""
                UPDATE code_point
                SET 
                    general_category_code = ?,
                    bidi_class_code = ?,
                    simple_uppercase_mapping_id = ?,
                    simple_lowercase_mapping_id = ?,
                    decomposition_type = ?
                WHERE id = ?""",
                (line[2], line[4], int(line[12], 16) if line[12] else None, int(line[13], 16) if line[13] else None, decom_type, code_point))

            for i, decom_id in enumerate(decom_ids):
                cursor.execute("""
                    INSERT INTO decomposition_mapping (code_point_id, decomposition_id, order_num)
                    VALUES (?, ?, ?)
                    ON CONFLICT DO NOTHING""", # stability policy, these won't change
                    (code_point, decom_id, i + 1))  # 1-index order number (I don't foresee a particular use for it in this project anyway)

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
        (1, "Derivation", "Standard/default/non-specific"),
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
        (1, "Near Certain", "Sources almost all agree, or disagreeing sources are suspect"),
        (2, "Likely", "Sources mostly agree, or a singular weak source"), # For the purposes of this project, Wikipedia does automatically count as a weak: it usually cites other sources
        (3, "Uncertain", "Sources disagree or are hesitant"),
        (4, "Algorithmic", "Derived algorithmically, usually from Unicode Consortium data"),
        (5, "Assumed", "Derivation assumed, usually by sound value and/or glyph similarity"),
        (6, "Unspecified", "Not specified in data files - this is a missing data error")]
    load_lookup(cursor, 'certainty_type', data)

def load_derivations(cursor, verify_script):
    def resolve_default(defaults_dict, row, field, script, final_default=None):
        if field in row and row[field] and not row[field].isspace():
            return row[field].strip()
        if script in defaults_dict and field in defaults_dict[script] and defaults_dict[script][field]:
                return defaults_dict[script][field]
        return final_default

    pattern = re.compile(r'^U\+([0-9A-F]+)\tkTraditionalVariant\tU\+([0-9A-F]+)')

    cursor.execute("DELETE FROM code_point_derivation")  # updates generally expected on this table, just clear

    # add derivations from decomposition mappings, assuming the decomposed characters are the base building blocks (the parent)
    cursor.execute("""
        INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
        SELECT
            cp.id, 
            decomposition_id,
            CASE WHEN decomposition_type = 'singleton' THEN 6 ELSE 1 END,
            4,
            'Unicode Character Database decomposition data'
        FROM code_point cp INNER JOIN decomposition_mapping dm ON cp.id = dm.code_point_id
        ON CONFLICT DO NOTHING""")
    # conflicts expected when a character decomposes into multiple copies of a code point,
    # minimal enough that this is probably the better query option than advance filtering

    # add derivations from case mapping, assuming lowercase to be derived from uppercase
    cursor.execute("""
        INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
        SELECT id, simple_uppercase_mapping_id, 1, 4, 'Unicode Character Database case mapping data'
        FROM code_point
        WHERE simple_uppercase_mapping_id IS NOT NULL""")
    # casing isn't 100% 1:1 so need to do mappings in both directions
    cursor.execute("""
        INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
        SELECT simple_lowercase_mapping_id, id, 1, 4, 'Unicode Character Database case mapping data'
        FROM code_point cp1
        WHERE id <> (SELECT simple_uppercase_mapping_id FROM code_point cp2 WHERE cp2.id = cp1.simple_lowercase_mapping_id)""")

    with open(os.path.join(CR_EXCLUSION_PATH, 'Unihan_Variants.txt'), 'r') as file:
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
                            (child, parent, 3, 4, 'Unihan Database'))

    defaults = {}
    with open(os.path.join(DERIVATIONS_PATH, 'defaults.csv'), 'r') as file:
        for row in csv.DictReader(file):
            defaults[row['Script'].strip()] = {
                'Source' : row['Source'].strip(),
                'Derivation Type' : row['Derivation Type'].strip(),
                'Certainty Type': row['Certainty Type'].strip()
            }

    script_files = (
            [os.path.join(DERIVATIONS_PATH, f) for f in os.listdir(DERIVATIONS_PATH) if f not in ('defaults.csv', GENERATED_DIR_NAME)] +
            [os.path.join(DERIVATIONS_PATH, GENERATED_DIR_NAME, f) for f in os.listdir(os.path.join(DERIVATIONS_PATH, GENERATED_DIR_NAME))])

    for script_file in script_files:
        script = script_file.split(os.path.sep)[-1].split('.')[0]
        with open(script_file, 'r') as file:
            for row in csv.DictReader(file):
                # Child and Parent are mandatory fields, but the rest can be defaulted
                child = row['Child'].strip()
                parents = row['Parent'].strip()
                notes = resolve_default(defaults, row, 'Notes', script)
                source = resolve_default(defaults, row, 'Source', script)
                derivation_types = resolve_default(defaults, row, 'Derivation Type', script, '1')  # final default is generic derivation (1)
                certainty = int(resolve_default(defaults, row, 'Certainty Type', script, '6')) # final default is unspecified (6)

                # Assumed certainty type overrides a default source, but not a specified source (though I can't imagine making a data scenario where the latter applies)
                if certainty == 5 and script in defaults and source == defaults[script]['Source']:
                    source = None

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

                    # File-specified data overrides the algorithmic generated data
                    cursor.execute("DELETE FROM code_point_derivation WHERE parent_id = ? AND child_id = ? AND certainty_type_id = 4", (ord(parent), ord(child)))

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
    GENERATED_DERIVATION_PATH = os.path.join(DERIVATIONS_PATH, GENERATED_DIR_NAME)
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
                    file.write(f'{deriv[0]},{deriv[1]},1,4,Wikipedia Indic letter cognate charts,Not necessarily graphical derivation but likely\n')

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
    else:
        cur.execute("PRAGMA foreign_keys = ON")

    return cur

if __name__ == '__main__':
    con = sqlite3.connect('scripts.db')
    cursor = load_database(con, dev_mode=False)

    # do stuff here if you want

    cursor.close()