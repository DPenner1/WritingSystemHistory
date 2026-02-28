import os
import sqlite3
import re
import csv
from enum import Enum

DEFAULT_DERIVATION = 1
NO_PARENT_CHARACTER = '\uFFFF'  # a Unicode non-character

class ScriptDatabase:

    _GENERATED_DIR_NAME = 'generated'
    _INDIC_ORDER = ['A', 'Ā', 'I', 'Ī', 'U', 'Ū', 'Ṛ', 'Ṝ', 'Ḷ', 'Ḹ', 'E', 'Ai', 'O', 'Au',
                    'Ka', 'Kha', 'Ga', 'Gha', 'Ṅa', 'Ca', 'Cha', 'Ja', 'Jha', 'Ña', 'Ṭa', 'Ṭha', 'Ḍa', 'Ḍha', 'Ṇa', 'Ta',
                   'Tha', 'Da', 'Dha', 'Na', 'Pa', 'Pha', 'Ba', 'Bha', 'Ma', 'Ya', 'Ra', 'La', 'Va', 'Śa', 'Ṣa', 'Sa','Ha']
    _SEMITIC_ORDER = ['Aleph', 'Bet', 'Gimel', 'Dalet', 'He', 'Waw', 'Zayin', 'Heth', 'Teth', 'Yodh', 'Kaph', 'Lamedh',
                     'Mem', 'Nun', 'Samekh', 'Ayin', 'Pe', 'Tsade', 'Qoph', 'Resh', 'Shin', 'Taw']
    _PROTO_SINAITIC_ORDER = ['ALP', 'BAYT', 'GAML', 'DALT', 'DAG', 'HAW', 'WAW', 'ZAYN', 'HASIR', 'HAYT', 'TAB', 'YAD', 'KAP',
                              'LAMD', 'MAYM', 'NAHS', 'SAMK', 'AYN', 'PAY', 'PIT', 'SAD', 'QUP', 'QAW', 'RAS', 'SAMS', 'TAD', 'TAW']
    _CODE_POINT_STARTS = {'kawi': 0x11F04, 'qabp': 0xE104, 'qabk': 0xE204, 'qabl': 0xE304, 'qabn': 0xE404, 'qabd': 0xE504, 'qabg': 0xE604, 'psin': 0xF000}

    # Brahmi, Kharoshti, Arabic, Phoenician which will be manually specified and the Aramaic code point not generally being included in Indic source
    # Can abo, Hangul, Kayah Li, Masaram Gondi, Sorang Sompeng, Pau cin hau will be manually specified due to higher independence or contribution from other scripts
    # Soyombo excluded due to elevated probability of script relationships being modified
    # Non-unicode scripts Gupta, Ranjana, Pallava, Tocharian, 'asho', 'kush' excluded
    _EXCLUDED_GEN_CODES = ['brah', 'khar', 'hang', 'cans', 'kali', 'soyo', 'gonm', 'sora', 'pauc', 'gupt', 'plav',
                           'ranj', 'asho', 'kush', 'toch', 'grek', 'latn', 'cyrl', 'arab', 'phnx', 'psin', 'armi']

    # i really wish i properly title-cased these, it's hurt a few times already. I'll get around to it at some point...
    _SCRIPT_PARENTS = {
        'kawi': 'qabp',
        'tibt': 'qabg',
        'bhks': 'qabg',
        'sidd': 'qabg',
        'shrd': 'qabg',
        'deva': 'qabn',
        'beng': 'qabd',
        'telu': 'qabk',
        'orya': 'qabd',
        'knda': 'qabk',
        'mlym': 'gran',
        'gujr': 'qabn',
        'gran': 'qabp',
        'phag': 'tibt',
        'zanb': 'phag',
        'newa': 'qabd',
        'mymr': 'qabp',
        'khmr': 'qabp',
        'laoo': 'thai',
        'thai': 'khmr',
        'ahom': 'mymr',
        'modi': 'qabn',
        'nand': 'qabn',
        'sylo': 'kthi',
        'kthi': 'qabn',
        'tirh': 'qabd',
        'lepc': 'tibt',
        'limb': 'lepc',
        'mtei': 'tibt',
        'marc': 'tibt',
        'takr': 'shrd',
        'dogr': 'takr',
        'khoj': 'qabl',
        'sind': 'qabl',
        'mahj': 'qabl',
        'mult': 'qabl',
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
        'guru': 'qabl',
        'lana': 'mymr',
        'talu': 'lana',
        'tavt': 'thai',
        'sinh': 'gran',
        'cakm': 'mymr',
        'gong': 'qabn',
        'maka': 'kawi',
        'taml': 'qabp',
        'tale': 'mymr',
        'saur': 'gran',
        'cham': 'qabp',
        'diak': 'gran',
        'qabp': 'brah',
        'qabk': 'brah',
        'qabl': 'shrd',
        'qabn': 'sidd',
        'qabd': 'sidd',
        'qabg': 'brah',
         # semitic
        'arab': 'nbat',
        'syrc': 'armi',
        'hebr': 'armi',
        'nbat': 'armi',
        'armi': 'phnx',
        'ethi': 'sarb',
        'ugar': 'psin',
        'narb': 'psin',
        'sarb': 'psin',
        'samr': 'phnx',
        'phnx': 'psin'
    }

    def __init__(self, name='scripts.db', path='.'):
        self._db_name = name
        self._db_path = path
        self._set_connection()
        self._set_resource_paths()
        self._query_path = os.path.join(self._db_path, 'queries')


    def _set_connection(self):
        self._cxn = sqlite3.connect(os.path.join(self._db_path, self._db_name))


    def _set_resource_paths(self, resource_path=None):
        self._resource_path = resource_path if resource_path else os.path.join(self._db_path, 'resource')
        self._derivations_path = os.path.join(self._resource_path, 'derivations')
        self._wikipedia_path = os.path.join(self._resource_path, 'wikipedia-sourced')
        self._unicode_path = os.path.join(self._resource_path, 'unicode-data')
        self._generated_derivation_path = os.path.join(self._derivations_path, ScriptDatabase._GENERATED_DIR_NAME)


    def _get_sql_in_str_list(self, enumerable):
        return "('" + "','".join(enumerable) + "')"


    def _get_unique_saved_query(self, name_prefix):
        queries = [f for f in os.listdir(self._query_path) if f.startswith(name_prefix)]

        if len(queries) == 0:
            raise ValueError(f"No query named {name_prefix} found in {self._query_path}")
        elif len(queries) > 1:
            raise ValueError("Multiple matching queries found: " + str(queries))

        return os.path.join(self._query_path, queries[0])


    def pretty_print_query(self, cursor, query, parameters=None):
        def print_data_row(row, pads):
            BIDI_STRONG_ISOLATOR = '\u2068'
            BIDI_ISOLATOR_POP = '\u2069'
            print(f'|  {BIDI_STRONG_ISOLATOR}' + f'{BIDI_ISOLATOR_POP}  |  {BIDI_STRONG_ISOLATOR}'.join(
                [r.ljust(p) for r, p in zip(row, pads)]) + BIDI_ISOLATOR_POP + '  |')

        def print_separator_row(bookend_char, pads):
            print(bookend_char + '--' + '--+--'.join(['-' * p for p in pads]) + '--' + bookend_char)

        results = cursor.execute(query, parameters).fetchall() if parameters else cursor.execute(query).fetchall()
        header = [x[0].replace('_', ' ').title() for x in cursor.description]
        results = [['' if field is None else str(field) for field in row] for row in results]
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


    def pretty_print_saved_query(self, cursor, query_name, parameters=None):
        with open(self._get_unique_saved_query(query_name)) as file:
            self.pretty_print_query(cursor, file.read(), parameters)


    def execute_query(self, cursor, query, parameters=None):
        return cursor.execute(query, parameters).fetchall() if parameters else cursor.execute(query).fetchall()


    def execute_saved_query(self, cursor, query_name, parameters=None):
        with open(self._get_unique_saved_query(query_name)) as file:
            return self.execute_query(cursor, file.read(), parameters)


    def _setup_schema(self, cursor):
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
                text TEXT UNIQUE GENERATED ALWAYS AS (CASE WHEN general_category_code IN ('Cn', 'Cs') THEN NULL ELSE CHAR(id) END),
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
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_pk_inverse ON code_point_derivation(parent_id, child_id, derivation_type_id)")


    def _load_scripts(self, cursor):
        # see https://www.unicode.org/iso15924/iso15924-codes.html
        with open(os.path.join(self._resource_path, 'iso15924.csv'), 'r') as file:
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
                        (code, name, id, version, subversion, name, version, subversion))  # TODO: check stability policy


    def _update_code_point(self, cursor, id, name, general_category, bidi_class, upper_mapping, lower_mapping, decom_str):
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
                           (id, decom_id,
                            i + 1))  # 1-index order number (I don't foresee a particular use for it in this project anyway)


    def _load_code_point_data(self, cursor):
        pattern = re.compile(r'^([0-9A-F]+)(?:\.\.([0-9A-F]+))?\s*; ([_a-zA-Z]+) #')

        cursor.execute(
            "INSERT INTO code_point (id, name, bidi_class_code) VALUES (?, 'NO PARENT CHARACTER', 'Bn') ON CONFLICT DO NOTHING",
            (ord(NO_PARENT_CHARACTER),))

        with open(os.path.join(self._unicode_path, 'Scripts.txt'), 'r') as file:
            for line in file:
                if not line.isspace() and not line.startswith('#'):
                    match = pattern.match(line)
                    start = int(match.group(1), 16)
                    end = int(match.group(2), 16) if match.group(2) else start
                    script_name = match.group(3)
                    script_code = cursor.execute("SELECT code FROM script WHERE u_name = ?", (match.group(3),)).fetchone()[0]

                    for i in range(start, end + 1):
                        cursor.execute("""
                            INSERT INTO code_point (id, script_code) 
                            VALUES (?, ?)
                            ON CONFLICT (id) DO NOTHING""",
                                       (i, script_code))  # TODO: double check stability policy

        with open(os.path.join(self._unicode_path, 'UnicodeData.txt'), 'r') as csvfile:
            special_name_pattern = re.compile('^<(.+)>$')
            in_range = False

            for line in csv.reader(csvfile, delimiter=';'):

                if in_range:
                    for i in range(code_point + 1, int(line[0], 16) + 1):
                        # TODO: this is not strictly conforming for Hangul
                        self._update_code_point(cursor, i, name + '-' + hex(i)[2:].upper(), general_category, bidi_class,
                                          upper_mapping, lower_mapping, decom_str)
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

                    self._update_code_point(cursor, code_point, name + '-' + line[0] if in_range else name, general_category,
                                      bidi_class, upper_mapping, lower_mapping, decom_str)

        with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'private_use.csv'), 'r') as file:
            for row in csv.DictReader(file):
                cursor.execute("""
                    INSERT INTO code_point (id, script_code, name, general_category_code)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (id) DO UPDATE SET script_code = ?, name = ?, general_category_code = ?""",
                    (int(row['Id']), row['Script Code'], row['Name'], row['General Category'], row['Script Code'], row['Name'], row['General Category']))

        cursor.execute("UPDATE code_point SET std_order_num = NULL")
        with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'r') as file:
            for row in csv.DictReader(file):
                for i, c in enumerate(row['Alphabet']):
                    cursor.execute("UPDATE code_point SET std_order_num = ? WHERE text = ?", (i + 1, c))  # 1-index for readability
        with open(os.path.join(self._resource_path, 'standard_alphabets.csv'), 'r') as file:
            for row in csv.DictReader(file):
                for i, c in enumerate(row['Alphabet']):
                    cursor.execute("UPDATE code_point SET std_order_num = ? WHERE text = ?", (i + 1, c))  # 1-index for readability


    def _load_lookups(self, cursor):
        def load_lookup(cursor, table_name, lookup_data):
            for lu in lookup_data:
                cursor.execute(
                    f"INSERT INTO {table_name} (id, name, description)" + """
                    VALUES (?, ?, ?)
                    ON CONFLICT (id) DO UPDATE SET name = ?, description = ?""",
                    (lu[0], lu[1], lu[2], lu[1], lu[2]))

        data = [
            (DEFAULT_DERIVATION, "Derivation", "Standard/default/non-specific"),
            (2, "Portion copy",
             "Child is a copy of a portion of the parent, allowing for stretch-distortion due to size change"),
            (3, "Simplification", "Child is a simplification of parent"),
            (4, "From cursive", "Child is derived from cursive form of the parent (who is typically non-cursive)"),
            (5, "Copy", "Child is a copy of the parent"),
            # Generally either child script copying or lowercase just a small version of uppercase
            (6, "Duplicate", "Child is a duplicate of the parent"),  # Unicode duplicate code points
            (7, "Portion derivation", "Child is a derivation from a portion of the parent"),
            (8, "Rotation", "Child is a rotation of the parent"),
            (9, "Reflection", "Child is a reflection of the parent")]
        load_lookup(cursor, 'derivation_type', data)

        # For this project, sourcing is generally just for the derivation fact, not necessarily for derivation type
        # Even having this feels like overkill, but I was mostly specifying it in Notes anyways and the special values (4+) are useful in the code
        data = [
            (Certainty.NEAR_CERTAIN.value, "Near Certain", "Sources almost all agree, or disagreeing sources are suspect"),
            (Certainty.LIKELY.value, "Likely", "Sources mostly agree, or a singular weak source"),
            # For the purposes of this project, Wikipedia does not automatically count as a weak: it usually cites other sources
            (Certainty.UNCERTAIN.value, "Uncertain", "Sources disagree or are hesitant"),
            (Certainty.AUTOMATED.value, "Automated", "Derived without manual review, usually from Unicode Consortium data"),
            (Certainty.ASSUMED.value, "Assumed", "Derivation assumed, usually by sound value and/or glyph similarity"),
            (Certainty.UNSPECIFIED.value, "Unspecified", "Not specified in data files - this is a missing data error")]
        load_lookup(cursor, 'certainty_type', data)


    def _load_derivations(self, cursor, indic_letter_data, semitic_letter_data, verify_script):
        def resolve_default(defaults_dict, script, data_row, field, overriding_default=None, override_condition=False,
                            last_resort=None):
            if field in data_row and data_row[field] and not data_row[field].isspace():
                return data_row[field].strip()
            if override_condition:
                return overriding_default
            if script in defaults_dict and field in defaults_dict[script] and defaults_dict[script][field]:
                return defaults_dict[script][field]
            return last_resort

        # Mende Kikakui is a bit of an exception here: Unicode Encoding Proposal suggests Vai-derived characters are a small minority
        # Not including Chinese here: ideally will eventually do so for Oracle bone
        independent_scripts = {'Mend', 'Egyp', 'Lina', 'Hluw', 'Xsux', 'Xpeo', 'Ogam', 'Elba', 'Dupl', 'Sgnw', 'Shaw', 'Vith',
                               'Vaii', 'Bamu', 'Berf', 'Nkoo', 'Wara', 'Gonm', 'Toto', 'Osma', 'Adlm', 'Gara', 'Medf', 'Bass',
                               'Yezi', 'Tnsa', 'Olck', 'Thaa', 'Tols', 'Nagm', 'Sora', 'Wcho', 'Mroo', 'Onao', 'Sunu', 'Yiii', 'Tang'}
        copy_decompositions = {'noBreak', 'small', 'sub', 'super'}

        pattern = re.compile(r'^U\+([0-9A-F]+)\tkTraditionalVariant\tU\+([0-9A-F]+)')

        cursor.execute("DELETE FROM code_point_derivation")  # updates generally expected on this table, just clear

        self._load_letter_derivation_data(cursor, indic_letter_data, ScriptDatabase._INDIC_ORDER, False, options.verify_data_sources)
        self._load_letter_derivation_data(cursor, semitic_letter_data, ScriptDatabase._SEMITIC_ORDER, True, options.verify_data_sources)

        # Identify all the independently-derived characters
        cursor.execute(f"""
                INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, notes)
                SELECT id, ?, ?, ?, 'Independent script: Assume independent character'
                FROM code_point 
                WHERE script_code IN {self._get_sql_in_str_list(independent_scripts)}""",
                       (ord(NO_PARENT_CHARACTER), DEFAULT_DERIVATION, Certainty.AUTOMATED.value))

        # add derivations from decomposition mappings, assuming the decomposed characters are the base building blocks (the parent)
        # Formatting/control/space characters are not eligible
        cursor.execute(f"""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
            SELECT
                code_point_id,
                decomposition_id,
                CASE WHEN COUNT(decomposition_id) OVER (PARTITION BY code_point_id) = 1
                    THEN CASE WHEN cp1.decomposition_type = 'canonical' THEN 6
                              WHEN cp1.decomposition_type IN {self._get_sql_in_str_list(copy_decompositions)} THEN 5
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

        with open(os.path.join(self._unicode_path, 'Unihan_Variants.txt'), 'r') as file:
            for line in file:
                if not line.isspace() and not line.startswith('#'):
                    match = pattern.match(line)
                    if match:
                        child = int(match.group(1), 16)
                        parent = int(match.group(2), 16)

                        if child != parent:  # it's possible for a simplified character to map to itself
                            cursor.execute("""
                                INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
                                VALUES (?, ?, ?, ?, ?)""",
                                           (child, parent, 3, Certainty.AUTOMATED.value, 'Unihan Database'))

        defaults = {}
        with open(os.path.join(self._derivations_path, 'defaults.csv'), 'r') as file:
            for row in csv.DictReader(file):
                defaults[row['Script'].strip()] = {
                    'Source': row['Source'].strip(),
                    'Derivation Type': row['Derivation Type'].strip(),
                    'Certainty Type': row['Certainty Type'].strip()
                }

        for s in os.listdir(self._derivations_path):
            if s != 'defaults.csv':
                script_file = os.path.join(self._derivations_path, s)
                script = script_file.split(os.path.sep)[-1].split('.')[0]
                with open(script_file, 'r') as file:
                    for row in csv.DictReader(file):
                        child = row['Child'].strip()
                        parents = row['Parent'].strip() if row[
                            'Parent'] else NO_PARENT_CHARACTER  # This won't be in the defaults dictionary

                        # Logic for defaulting to Uncertain on no parent: For historical scripts, this is usually more a function of a lack of records
                        # For modern scripts, the inventor is generally aware of existing writing systems, and may have been inspired
                        certainty = int(resolve_default(defaults, script, row, 'Certainty Type',
                                                        overriding_default=str(Certainty.UNCERTAIN.value),
                                                        override_condition=(parents == NO_PARENT_CHARACTER),
                                                        last_resort=str(Certainty.UNSPECIFIED.value)))

                        # Overriding default here is for convenience: An Assumed certainty means there is no source, so allows us to specify a source in defaults for all else.
                        source = resolve_default(defaults, script, row, 'Source', overriding_default=None,
                                                 override_condition=(certainty == Certainty.ASSUMED.value))

                        notes = resolve_default(defaults, script, row, 'Notes')
                        derivation_types = resolve_default(defaults, script, row, 'Derivation Type',
                                                           last_resort=str(DEFAULT_DERIVATION))

                        # ensure that child character is always the expected script
                        if verify_script:
                            script_in_file = cursor.execute(
                                "SELECT u_name FROM code_point cp INNER JOIN script s ON s.code = cp.script_code WHERE text = ?", child).fetchone()[0]
                            if script != script_in_file:
                                raise ValueError(
                                    f"resource file error in {script}.csv with child character {child} detected to be {script_in_file} instead")

                        for parent in parents.split('/'):
                            if verify_script:
                                if child == parent:
                                    raise ValueError("Attempted to add self-derivation of " + child)
                                if cursor.execute("SELECT * FROM code_point_derivation WHERE parent_id = ? AND child_id = ?",
                                                  (ord(child), ord(parent))).fetchall():
                                    raise ValueError("Attempted to add a 2-cycle with " + child + " and " + parent)

                            # File-specified data overrides the automatically generated data
                            cursor.execute(
                                "DELETE FROM code_point_derivation WHERE parent_id = ? AND child_id = ? AND certainty_type_id = ?",
                                (ord(parent), ord(child), Certainty.AUTOMATED.value))

                            for derivation_type in derivation_types.split('/'):
                                cursor.execute("""
                                    INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source, notes)
                                    VALUES (?, ?, ?, ?, ?, ?)""",
                                               (ord(child), ord(parent), int(derivation_type), certainty, source, notes))


    def get_code_to_script_dict(self):
        retval = {}
        cursor = self._cxn.cursor()
        results = cursor.execute("SELECT code, u_name FROM script WHERE u_name IS NOT NULL").fetchall()
        for row in results:
            retval[row[0]] = row[1]
        cursor.close()
        return retval


    def _generate_private_use_data(self, indic_letter_data):
        def get_private_use_indic_name(script_code, wiki_letter_name):
            script_name = self.get_code_to_script_dict()[script_code.title()]
            replacements = {'Ā': 'AA', 'Ī': 'II', 'Ū': 'UU', 'Ṛ': 'vocalic R', 'Ṝ': 'vocalic RR', 'Ḷ': 'vocalic L', 'Ḹ': 'vocalic LL',
                            'Ṅa': 'Nga', 'Ña': 'Nya', 'Ṭa': 'Tta', 'Ṭha': 'Ttha', 'Ḍa': 'Dda', 'Ḍha': 'Ddha', 'Ṇa': 'Nna', 'Va': 'Wa', 'Śa': 'Sha', 'Ṣa': 'Ssa'}
            if wiki_letter_name in replacements:
                wiki_letter_name = replacements[wiki_letter_name]
            return (script_name + ' letter ' + wiki_letter_name).upper()

        with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'private_use.csv'), 'w') as file:
            file.write('Id,Script Code,Name,General Category')

            for script_code in indic_letter_data:
                if script_code.startswith('q'):
                    for letter_class in indic_letter_data[script_code]:
                        letter = indic_letter_data[script_code][letter_class][0] # generated only has one
                        file.write(f'\n{ord(letter)},{script_code.title()},{get_private_use_indic_name(script_code, letter_class)},Lo') # TODO: Assuming Lo for now

            for i, letter in enumerate(ScriptDatabase._PROTO_SINAITIC_ORDER):
                file.write(f'\n{i + ScriptDatabase._CODE_POINT_STARTS['psin']},Psin,PROTO-SINAITIC LETTER {letter},Lo')

    # format: { script_code (lowercase): { Generic Indic Letter: [letters] } }
    def _get_indic_letter_dict(self, verify):
        wdata = {}
        hex_pattern = re.compile('^[0-9A-F]+$')
        replacements = {'gupt': 'qabg', 'kdmb': 'qabk', 'plav': 'qabp'}
        for letter in ScriptDatabase._INDIC_ORDER:
            with open(os.path.join(self._wikipedia_path, 'indic-letters', letter + '.txt'), 'r') as file:
                for match in re.findall(r'\|\s*([a-z0-9]+)(cp|img)\s*=([^\|]+)', file.read()):
                    script_code = match[0][0:4]  # a few have multiple codepoints indicated by appended numbers
                    if script_code in replacements:
                        script_code = replacements[script_code]

                    if script_code not in wdata:
                        wdata[script_code] = {}
                    if letter not in wdata[script_code]:
                        wdata[script_code][letter] = []
                    if match[1] == 'cp':  # code point exists for the script
                        value = match[2].strip()
                        if '&#x' in value:
                            value = value[value.index('x') + 1:]
                        if hex_pattern.match(value):  # there's one entry in Tibetan that has three codepoints and I don't understand the intention
                            letter_to_add = chr(int(value, 16))
                            if letter_to_add == 'ᜢ' and letter == 'O':
                                if verify:
                                    print("Data generation error: Hanunoo letter ᜢ in two Indic letter files")  # a likely error in the source files
                            elif letter_to_add not in wdata[script_code][letter]:
                                wdata[script_code][letter].append(letter_to_add)

        # kawi a bit of a special case in that it exists in Unicode, but probably because its one of the newer ones, Wikipedia source files didn't have code points yet
        # in unicode, currently all indic letters exist in Kawi except for vowel Au, so just manually made sure that one wasn't added by the code
        fill_in_scripts = ['kawi', 'qabp', 'qabk', 'qabl', 'qabn', 'qabd', 'qabg']

        # if it existed as an image in Wikipedia (it would have got created as an empty list) OR 50% + 1 have the Indic letter, we assume it exists
        for fill_in_script in fill_in_scripts:
            if fill_in_script not in wdata:
                wdata[fill_in_script] = {}
            for letter in ScriptDatabase._INDIC_ORDER:
                fill_in_letter = False
                if letter in wdata[fill_in_script] and wdata[fill_in_script][letter] is not None:
                    fill_in_letter = (len(wdata[fill_in_script][letter]) == 0) # in theory letter could already have be there, so don't touch it
                else:
                    descendant_scripts = [x for x in self._SCRIPT_PARENTS if self._SCRIPT_PARENTS[x] == fill_in_script]
                    count = 0
                    for descendant_script in descendant_scripts:
                        if letter in wdata[descendant_script] and wdata[descendant_script][letter]:
                            count += 1
                    if count >= len(descendant_scripts)/2 + 1:
                        fill_in_letter = True

                if fill_in_letter:
                    id = ScriptDatabase._CODE_POINT_STARTS[fill_in_script] + self._INDIC_ORDER.index(letter)
                    wdata[fill_in_script][letter] = [chr(id)]

        return wdata


    def _generate_std_alphabets(self, indic_letter_dict, semitic_letter_dict):
        # aramaic a bit of a hack because I want it generated in the Semitic list and not Indic
        def generate_std_alphabet(letter_dict, letter_order):
            script_dict = self.get_code_to_script_dict()
            with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'a') as alpha_file:
                for script_code in letter_dict:
                    if script_code not in ScriptDatabase._EXCLUDED_GEN_CODES:
                        script_name = script_dict[script_code.title()]
                        alpha_file.write('\n' + script_name + ',')
                        for letter_class in letter_order:
                            if letter_class in letter_dict[script_code]:
                                for letter in letter_dict[script_code][letter_class]:
                                    alpha_file.write(letter)

        with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'w') as file:
            file.write('Script,Alphabet')

        generate_std_alphabet(indic_letter_dict, ScriptDatabase._INDIC_ORDER)
        generate_std_alphabet(semitic_letter_dict, ScriptDatabase._SEMITIC_ORDER)

    # exclude aramaic a bit of a hack because I want it generated in the Semitic list and not Indic
    def _load_letter_derivation_data(self, cursor, letter_dict, letter_order, include_aramaic, verify):
        script_dict = self.get_code_to_script_dict()
        for script_code in letter_dict:
            if script_code not in ScriptDatabase._EXCLUDED_GEN_CODES or (script_code == 'armi' and include_aramaic):
                script_name = script_dict[script_code.title()]

                #with open(os.path.join(self._generated_derivation_path, script_name + '.csv'), 'w') as script_file:
                 #   script_file.write('Child,Parent,Derivation Type,Certainty Type,Source,Notes\n')

                parent_code = ScriptDatabase._SCRIPT_PARENTS[script_code]
                for letter_class in letter_order:
                    if letter_class in letter_dict[script_code]:
                        if letter_class in letter_dict[parent_code]:
                            parent_letters = letter_dict[parent_code][letter_class]  # final parent scripts should be in excluded codes
                            if (len(parent_letters) == 1):
                                for letter in letter_dict[script_code][letter_class]:
                                    cursor.execute("""
                                        INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source, notes)
                                        VALUES (?,?,?,?,?,?)""",
                                        (ord(letter), ord(parent_letters[0]), DEFAULT_DERIVATION, Certainty.AUTOMATED.value,'Wikipedia letter cognate charts','Not necessarily graphical derivation but likely'))
                            elif verify:  # temporary, for later manual work
                                print(f"Data generation warning: {len(parent_letters)} parent letters found for {letter_class} in {script_code}")

    # format: { script_code (lowercase): { Generic Semitic Letter: [letters] } }
    def _get_semitic_letter_dict(self):
        code_map = {
            'ar': 'arab',
            'sy': 'syrc',
            'he': 'hebr',
            'sm': 'samr',
            'am': 'armi',
            'nb': 'nbat',
            'ge': 'ethi',
            'ug': 'ugar',
            'ph': 'phnx',
            'na': 'narb',
            'sa': 'sarb',
            'gr': 'grek',
            'la': 'latn',
            'cy': 'cyrl',
        }
        wdata = {}
        for letter in ScriptDatabase._SEMITIC_ORDER:
            with open(os.path.join(self._wikipedia_path, 'semitic-letters', letter + '.txt'), 'r') as file:
                for match in re.findall(r'\|\s*([a-z]{2})char\s*=([^\|]+)', file.read()):
                    script_code = code_map[match[0]]
                    if script_code not in wdata:
                        wdata[script_code] = {}
                    # there's a few ways these data files format multiple characters, this should cover it
                    wdata[script_code][letter] = list(match[1].strip().replace('\u200E', '').replace('/', ''))

        # manually curated Semitic general->proto-Sinaitic list.
        # Basically going to allow only the ones that have an unambiguous Phoenician descendant to be automatically generated
        letter_map = {'Aleph': 'ALP', 'Bet': 'BAYT', 'Gimel': 'GAML', 'He': 'HAW', 'Waw': 'WAW', 'Zayin': 'ZAYN', 'Yodh': 'YAD',
                      'Kaph': 'KAP', 'Lamedh': 'LAMD', 'Mem': 'MAYM', 'Nun': 'NAHS', 'Ayin': 'AYN', 'Tsade': 'SAD', 'Resh': 'RAS', 'Taw': 'TAW'}

        wdata['psin'] = {}
        for letter in letter_map:
            wdata['psin'][letter] = [chr(ScriptDatabase._PROTO_SINAITIC_ORDER.index(letter_map[letter]) + ScriptDatabase._CODE_POINT_STARTS['psin'])]

        return wdata


    def _verify_script_coverage(self, cursor):
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

        with open(os.path.join(self._resource_path, 'standard_alphabets.csv'), 'r') as csvfile:
            for row in csv.DictReader(csvfile):
                verify_script(row['Script'])
        with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'r') as csvfile:
            for row in csv.DictReader(csvfile):
                verify_script(row['Script'])

    # dev mode runs additional checks and outputs some data to console
    def load_database(self, load_options=None):
        options = load_options if load_options else LoadOptions()

        if options.force_overwrite:
            if os.path.isfile(os.path.join(self._db_path, self._db_name)):
                os.remove(os.path.join(self._db_path, self._db_name))
            if os.path.isfile(os.path.join(self._db_path, self._db_name + '-journal')):
                os.remove(os.path.join(self._db_path, self._db_name + '-journal'))
            self._set_connection()
        if options.resource_path:
            self._set_resource_paths()
        if options.saved_query_path:
            self._query_path = options.saved_query_path

        cur = self._cxn.cursor()
        if options.verify_data_sources:
            cur.execute("PRAGMA foreign_keys = ON")
        else:
            cur.execute("PRAGMA foreign_keys = OFF")

        self._setup_schema(cur)

        self._load_lookups(cur)
        self._cxn.commit()

        self._load_scripts(cur)
        self._cxn.commit()

        indic_letter_data = self._get_indic_letter_dict(options.verify_data_sources)
        semitic_letter_data = self._get_semitic_letter_dict()

        self._generate_private_use_data(indic_letter_data)
        self._generate_std_alphabets(indic_letter_data, semitic_letter_data)

        self._load_code_point_data(cur)
        self._cxn.commit()

        self._load_derivations(cur, indic_letter_data, semitic_letter_data, options.verify_data_sources)
        self._cxn.commit()

        if options.output_debug_info:
            self._verify_script_coverage(cur)
            self.pretty_print_saved_query(cur, 'Total derivation statistics')

        cur.execute("PRAGMA foreign_keys = ON")

        return cur


class Certainty(Enum):
    NEAR_CERTAIN = 1
    LIKELY = 2
    UNCERTAIN = 3
    AUTOMATED = 4
    ASSUMED = 5
    UNSPECIFIED = 6


class LoadOptions:
    def __init__(self):
        self.force_overwrite = False
        self.verify_data_sources = False
        self.output_debug_info = False
        # path None = Default to leaving previous path alone, DB working subdirectories if not previously specified
        self.resource_path = None
        self.saved_query_path = None


if __name__ == '__main__':
    db = ScriptDatabase()
    options = LoadOptions()
    options.force_overwrite = True
    options.verify_data_sources = True
    options.output_debug_info = True

    cursor = db.load_database(None)  # replace with options for development run

    # do stuff here if you want, for example:
    # db.pretty_print_saved_query(cursor, 'Get Character Ancestors', 'a')

    cursor.close()