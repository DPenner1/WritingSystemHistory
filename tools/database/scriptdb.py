import os
import sqlite3
import re
import csv
import time
from enum import Enum
from zipfile import ZipFile




class ScriptDatabase:

    INHERITED_SCRIPT = 'Zinh'
    COMMON_SCRIPT = 'Zyyy'
    UNICODE_MAX = 0x10FFFF
    NO_PARENT_CHARACTER = '\uFFFF'  # a Unicode non-character

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
    # Non-unicode scripts Ranjana, Tocharian, Brahmic variants 'asho', 'kush' excluded
    _EXCLUDED_GEN_CODES = ['brah', 'khar', 'hang', 'cans', 'kali', 'soyo', 'gonm', 'sora', 'pauc', 'gupt', 'plav',
                           'ranj', 'asho', 'kush', 'toch', 'grek', 'latn', 'cyrl', 'arab', 'phnx', 'psin']

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

    def __init__(self, path='.', name='scripts.db'):
        self._db_name = name
        self._db_path = path
        self._set_connection()
        self._set_resource_paths()
        self._query_path = os.path.join(self._db_path, 'queries')
        self._next_sequence_id = ScriptDatabase.UNICODE_MAX


    def _set_connection(self):
        self._cxn = sqlite3.connect(os.path.join(self._db_path, self._db_name))


    def _set_resource_paths(self, resource_path=None):
        self._resource_path = resource_path if resource_path else os.path.join(self._db_path, 'resource')
        self._derivations_path = os.path.join(self._resource_path, 'derivations')
        self._wikipedia_path = os.path.join(self._resource_path, 'wikipedia-sourced')
        self._unicode_path = os.path.join(self._resource_path, 'unicode-data')

    @staticmethod
    def _get_sql_in_str_list(enumerable):
        return "('" + "','".join([x.replace("'", "''") for x in enumerable]) + "')"


    def _get_unique_saved_query(self, name_prefix):
        queries = [f for f in os.listdir(self._query_path) if f.startswith(name_prefix)]

        if len(queries) == 0:
            raise ValueError(f"No query named {name_prefix} found in {self._query_path}")
        elif len(queries) > 1:
            raise ValueError("Multiple matching queries found: " + str(queries))

        return os.path.join(self._query_path, queries[0])

    @staticmethod
    def print_table(data, has_header=True):
        def print_data_row(row, pads):
            BIDI_STRONG_ISOLATOR = '\u2068'
            BIDI_ISOLATOR_POP = '\u2069'
            print(f'|  {BIDI_STRONG_ISOLATOR}' + f'{BIDI_ISOLATOR_POP}  |  {BIDI_STRONG_ISOLATOR}'.join(
                [r.ljust(p) for r, p in zip(row, pads)]) + BIDI_ISOLATOR_POP + '  |')

        def print_separator_row(bookend_char, pads):
            print(bookend_char + '--' + '--+--'.join(['-' * p for p in pads]) + '--' + bookend_char)

        table_header = None
        table_data = [['' if field is None else str(field) for field in row] for row in data]
        if has_header:
            table_header = table_data[0]
            table_data = table_data[1:]

        pads = []
        for i in range(len(table_header)):
            # TODO - this is going to fail miserably in this project with string length != grapheme apparent length
            pads.append(max([len(x[i]) for x in table_data + [table_header]]))

        print_separator_row('+', pads)
        if has_header:
            print_data_row(table_header, pads)
            print_separator_row('|', pads)
        for r in table_data:
            print_data_row(r, pads)
        print_separator_row('+', pads)


    def execute_query(self, query, parameters=None, return_headers=True):
        cursor = self._cxn.cursor()
        results = cursor.execute(query, parameters).fetchall() if parameters else cursor.execute(query).fetchall()
        header = [x[0].replace('_', ' ').title() for x in cursor.description]
        cursor.close()
        if return_headers:
            return [header] + results
        return results


    def execute_saved_query(self, query_name, parameters=None, return_headers=True):
        with open(self._get_unique_saved_query(query_name)) as file:
            return self.execute_query(file.read(), parameters, return_headers)


    def _setup_schema(self, cursor):
        with open(self._get_unique_saved_query('Setup schema')) as file:
            cursor.executescript(file.read())


    def _try_unzip_sources(self, zip_dir_path, output_debug=False):
        def unzip_file(zip_file, file_wanted, destination_file):
            try:
                with ZipFile(zip_file, 'r') as zf:
                    content = zf.read(file_wanted)
                    with open(destination_file, 'w') as dest_file:
                        dest_file.write(content.decode())
            except FileNotFoundError:
                if output_debug:
                    print(f'Warning: Unable to unzip {file_wanted} from {zip_file.split(os.path.sep)[-1]}, relying on source file being in {self._resource_path}')
                return False
            return True

        unzip_results = [
            unzip_file(os.path.join(zip_dir_path, 'UCD.zip'), 'UnicodeData.txt', os.path.join(self._unicode_path, 'UnicodeData.txt')),
            unzip_file(os.path.join(zip_dir_path, 'UCD.zip'), 'Scripts.txt', os.path.join(self._unicode_path, 'Scripts.txt')),
            unzip_file(os.path.join(zip_dir_path, 'UCD.zip'), 'Unikemet.txt', os.path.join(self._unicode_path, 'Unikemet.txt')),
            unzip_file(os.path.join(zip_dir_path, 'Unihan.zip'), 'Unihan_Variants.txt', os.path.join(self._unicode_path, 'Unihan_Variants.txt')),
        ]

        cldr_pattern = re.compile('cldr-common.+zip')
        cldr_zip_file = [os.path.join(zip_dir_path, f) for f in os.listdir(zip_dir_path) if cldr_pattern.match(f)]
        cldr_success = True
        if not len(cldr_zip_file) == 1:
            cldr_success = False
            if output_debug:
                print(f'Found {len(cldr_zip_file)} cldr common zip files to unzip')
        else:
            # I don't know if path separators within zip files are os-dependent?? so I'm working around that
            cldr_file_pattern = re.compile(r"main.([a-z]{2,3}(?:_[A-Z][a-z]{3})?\.xml)$")
            cldr_file_pattern2 = re.compile(r"[a-z]{2,3}(?:_[A-Z][a-z]{3})?\.xml")
            with ZipFile(cldr_zip_file[0], 'r') as zip_file:
                for zipped_file in zip_file.namelist():
                    match = cldr_file_pattern.search(zipped_file)
                    if match:
                        unzip_file(cldr_zip_file[0], zipped_file, os.path.join(self._unicode_path, 'cldr', match[1]))

        return (not (False in unzip_results)) and cldr_success


    def get_next_sequence_id(self):
        self._next_sequence_id += 1
        return self._next_sequence_id


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

        with open(os.path.join(self._resource_path, 'script_variants.csv'), 'r') as file:
            for row in csv.DictReader(file):
                cursor.execute("UPDATE script SET canonical_script_code = ? WHERE code = ?", (row['Main'], row['Variant']))

    @staticmethod
    def is_private_use(id):
        return (0xE000 <= id <= 0xF8FF) or (0x100000 <= id <= 0x10FFFD)


    def _insert_code_point(self, cursor, id, name, script_code, general_category_code, bidi_class_code):
        if script_code is None: script_code = 'Zzzz'
        if general_category_code is None: general_category_code = 'Cn'
        if bidi_class_code is None: bidi_class_code = 'L'

        cursor.execute("INSERT INTO sequence (id, sequence_type_id) VALUES (?, ?) ON CONFLICT DO NOTHING", (id, SequenceType.BASE.value))
        if self.is_private_use(id):
            cursor.execute("""
                INSERT INTO code_point (id, name, script_code, general_category_code, bidi_class_code)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT DO UPDATE SET name = ?, script_code = ?, general_category_code = ?, bidi_class_code = ?""",
                (id, name, script_code, general_category_code, bidi_class_code, name, script_code, general_category_code, bidi_class_code))
        else:
            cursor.execute("""
                INSERT INTO code_point (id, name, script_code, general_category_code, bidi_class_code)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING""",
                (id, name, script_code, general_category_code, bidi_class_code))
                # TODO double check stability policy


    def _update_code_point(self, cursor, id, name, general_category, bidi_class, upper_mapping, lower_mapping, decom_str):
        decom_pattern = re.compile(r'^(?:<([a-zA-Z]+)> )?([\s0-9A-F]+)$')
        decom_type = None
        decom_ids = []

        seq_id = None
        if decom_str:
            match = decom_pattern.match(decom_str)
            decom_ids = [int(id, 16) for id in match.group(2).split(' ')]
            decom_type = match.group(1) if match.group(1) else 'canonical'
            seq_id = self.get_next_sequence_id()
            cursor.execute("""
                INSERT INTO sequence (id, sequence_type_id) 
                VALUES (?, (SELECT id FROM sequence_type WHERE name LIKE ?))""",
                (seq_id, decom_type.title() + '%'))
            for i, decom_id in enumerate(decom_ids):
                cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?, ?, ?)", (seq_id, decom_id, i + 1))


        cursor.execute("""
            UPDATE code_point
            SET 
                name = ?,
                general_category_code = ?,
                bidi_class_code = ?,
                simple_uppercase_mapping_id = ?,
                simple_lowercase_mapping_id = ?,
                equivalent_sequence_id = ?
            WHERE id = ?""",
            (name, general_category, bidi_class, upper_mapping, lower_mapping, seq_id, id))


    def _load_code_point_data(self, cursor):
        # Hangul constants named similarly to Unicode Standard algorithm
        S_BASE = 0xAC00
        L_BASE = 0x1100
        V_BASE = 0x1161
        T_BASE = 0x11A7
        L_COUNT = 19
        V_COUNT = 21
        T_COUNT = 28
        N_COUNT = V_COUNT * T_COUNT
        S_COUNT = L_COUNT * N_COUNT

        S_END = S_BASE + S_COUNT
        # This is parsable from UCD, but it's short and not likely to change (it would break the Hangul algo), so hard coding is fine and probably a bit more efficient
        JAMO_SHORT_NAME = { 0x1100: 'G', 0x1101: 'GG', 0x1102: 'N', 0x1103: 'D', 0x1104: 'DD', 0x1105: 'R', 0x1106: 'M', 0x1107: 'B', 0x1108: 'BB', 0x1109: 'S',
                            0x110A: 'SS', 0x110B: '', 0x110C: 'J', 0x110D: 'JJ', 0x110E: 'C', 0x110F: 'K', 0x1110: 'T', 0x1111: 'P', 0x1112: 'H', 0x1161: 'A',
                            0x1162: 'AE', 0x1163: 'YA', 0x1164: 'YAE', 0x1165: 'EO', 0x1166: 'E', 0x1167: 'YEO', 0x1168: 'YE', 0x1169: '0', 0x116A: 'WA', 0x116B: 'WAE',
                            0x116C: 'OE', 0x116D: 'YO', 0x116E: 'U', 0x116F: 'WEO', 0x1170: 'WE', 0x1171: 'WI', 0x1172: 'YU', 0x1173: 'EU', 0x1174: 'YI', 0x1175: 'I',
                            0x11A8: 'G', 0x11A9: 'GG', 0x11AA: 'GS', 0x11AB: 'N', 0x11AC: 'NJ', 0x11AD: 'NH', 0x11AE: 'D', 0x11AF: 'L', 0x11B0: 'LG', 0x11B1: 'LM',
                            0x11B2: 'LB', 0x11B3: 'LS', 0x11B4: 'LT', 0x11B5: 'LP', 0x11B6: 'LH', 0x11B7: 'M', 0x11B8: 'B', 0x11B9: 'BS', 0x11BA: 'S', 0x11BB: 'SS',
                            0x11BC: 'NG', 0x11BD: 'J', 0x11BE: 'C', 0x11BF: 'K', 0x11C0: 'T', 0x11C1: 'P', 0x11C2: 'H', }

        pattern = re.compile(r'^([0-9A-F]+)(?:\.\.([0-9A-F]+))?\s*; ([_a-zA-Z]+) #')

        # Reset since sequence ids not stable -> TODO in principle we could be smarter about this
        cursor.execute("DELETE FROM sequence_item")
        cursor.execute("DELETE FROM alphabet")
        cursor.execute("DELETE FROM sequence WHERE id > ?", (ScriptDatabase.UNICODE_MAX,))

        self._insert_code_point(cursor, ord(self.NO_PARENT_CHARACTER), name='NO PARENT CHARACTER', bidi_class_code='Bn', script_code=None, general_category_code=None)

        with open(os.path.join(self._unicode_path, 'Scripts.txt'), 'r') as file:
            for line in file:
                if not line.isspace() and not line.startswith('#'):
                    match = pattern.match(line)
                    start = int(match.group(1), 16)
                    end = int(match.group(2), 16) if match.group(2) else start
                    script_name = match.group(3)
                    script_code = cursor.execute("SELECT code FROM script WHERE u_name = ?", (match.group(3),)).fetchone()[0]

                    for i in range(start, end + 1):
                        self._insert_code_point(cursor, i, name=None, script_code=script_code, bidi_class_code=None, general_category_code=None)


        with open(os.path.join(self._unicode_path, 'UnicodeData.txt'), 'r') as csvfile:
            special_name_pattern = re.compile('^<(.+)>$')
            in_range = False

            for line in csv.reader(csvfile, delimiter=';'):

                if in_range:
                    for i in range(code_point, int(line[0], 16) + 1):
                        if S_BASE <= i < S_END:  # follow along Hangul decomposition algorithm Unicode Standard 3.12.2
                            s_index = i - S_BASE
                            if (i % 28) == (S_BASE % 28): # LV syllable
                                l_index, temp = divmod(s_index, N_COUNT)
                                v_index = temp // T_COUNT
                                l_part = L_BASE + l_index
                                v_part = V_BASE + v_index
                                decom_str = f"<jamo> {hex(l_part)[2:].upper()} {hex(v_part)[2:].upper()}"
                                suffix = " " + JAMO_SHORT_NAME[l_part] + JAMO_SHORT_NAME[v_part]
                            else:
                                temp, t_index = divmod(s_index, T_COUNT)
                                lv_index = temp * T_COUNT
                                lv_part = S_BASE + lv_index
                                t_part = T_BASE + t_index
                                decom_str = f"<jamo> {hex(lv_part)[2:].upper()} {hex(t_part)[2:].upper()}"
                                lv_name = cursor.execute("SELECT name FROM code_point WHERE id = ?", (lv_part,)).fetchone()[0]
                                suffix = " " + lv_name.split(' ')[-1] + JAMO_SHORT_NAME[t_part]
                        else:
                            suffix = '-' + hex(i)[2:].upper()

                        self._update_code_point(cursor, i, name + suffix, general_category, bidi_class, upper_mapping, lower_mapping, decom_str)

                    in_range = False
                else:
                    name = None
                    code_point = int(line[0], 16)
                    decom_str = line[5]
                    general_category = line[2] if line[2] else None
                    bidi_class = line[4] if line[4] else None
                    upper_mapping = int(line[12], 16) if line[12] else None
                    lower_mapping = int(line[13], 16) if line[13] else None

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
                        self._update_code_point(cursor, code_point, name, general_category, bidi_class, upper_mapping, lower_mapping, decom_str)

        with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'private_use.csv'), 'r') as file:
            for row in csv.DictReader(file):
                self._insert_code_point(cursor,
                                        int(row['Id']),
                                        script_code=row['Script Code'],
                                        name=row['Name'],
                                        general_category_code=row['General Category'],
                                        bidi_class_code=None)  # mostly a hack, all current PU are the default L


    """  TODO: reintegrate standard_alphabets to new alphabet architecture (historic scripts only now)
        with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'r') as file:
            for row in csv.DictReader(file):
                for i, c in enumerate(row['Alphabet']):
                    cursor.execute("UPDATE code_point SET std_order_num = ? WHERE text = ?", (i + 1, c))  # 1-index for readability
        with open(os.path.join(self._resource_path, 'standard_alphabets.csv'), 'r') as file:
            for row in csv.DictReader(file):
                for i, c in enumerate(row['Alphabet']):
                    cursor.execute("UPDATE code_point SET std_order_num = ? WHERE text = ?", (i + 1, c))  # 1-index for readability"""

    def _load_lookups(self, cursor):
        def load_lookup(cursor, table_name, lookup_data):
            cursor.executemany(
                f"INSERT INTO {table_name} (id, name, description)" + """
                VALUES (?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET name = ?, description = ?""",
                [(lu[0], lu[1], lu[2], lu[1], lu[2]) for lu in lookup_data])

        data = [
            (DerivationType.DEFAULT.value, "Derivation", "Standard/default/non-specific"),
            (DerivationType.PORTION_COPY.value, "Portion copy", "Child is a copy of a portion of the parent, allowing for stretch-distortion due to size change"),
            (DerivationType.SIMPLIFICATION.value, "Simplification", "Child is a simplification of parent"),
            (DerivationType.FROM_CURSIVE.value, "From cursive", "Child is derived from cursive form of the parent (who is typically non-cursive)"),
            (DerivationType.COPY.value, "Copy", "Child is a copy (or multiple) of the parent"), # Usually child script copying or lowercase just a small version of uppercase
            (DerivationType.DUPLICATE.value, "Duplicate", "Child is a duplicate of the parent"),  # Unicode duplicate code points
            (DerivationType.PORTION.value, "Portion derivation", "Child is a derivation from a portion of the parent"),
            (DerivationType.ROTATION.value, "Rotation", "Child is a rotation of the parent"),
            (DerivationType.REFLECTION.value, "Reflection", "Child is a reflection of the parent")]
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

        data = [
            (SequenceType.BASE.value, 'Base', '"Sequence" representing a single code point. Does not contain items.'),
            (SequenceType.LETTER.value, 'Letter', 'A sequence representing a letter'),
            (SequenceType.ALPHABET.value, 'Alphabet', 'A sequence representing an alphabet'),

            (SequenceType.CANONICAL_DECOMPOSITION.value, 'Canonical Decomposition', 'Unicode decomposition type representing full equivalency in all contexts'),
            (SequenceType.JAMO_CANONICAL_DECOMPOSITION.value, 'Jamo Canonical Decomposition', 'Unicode decomposition type for Hangul syllables'),
            (SequenceType.COMPATIBILITY_DECOMPOSITION.value, 'Compat Decomposition',
                'Unicode decomposition type (all non-canonical decompositions are compatibility decompositions, this is a "other" value)'),
            (SequenceType.NO_BREAK_DECOMPOSITION.value, 'NoBreak Decomposition', 'Unicode decomposition type'),
            (SequenceType.SUPER_DECOMPOSITION.value, 'Super Decomposition', 'Unicode decomposition type'),
            (SequenceType.FRACTION_DECOMPOSITION.value, 'Fraction Decomposition', 'Unicode decomposition type'),
            (SequenceType.SUB_DECOMPOSITION.value, 'Sub Decomposition', 'Unicode decomposition type'),
            (SequenceType.FONT_DECOMPOSITION.value, 'Font Decomposition', 'Unicode decomposition type'),
            (SequenceType.CIRCLE_DECOMPOSITION.value, 'Circle Decomposition', 'Unicode decomposition type'),
            (SequenceType.WIDE_DECOMPOSITION.value, 'Wide Decomposition', 'Unicode decomposition type'),
            (SequenceType.VERTICAL_DECOMPOSITION.value, 'Vertical Decomposition', 'Unicode decomposition type'),
            (SequenceType.SQUARE_DECOMPOSITION.value, 'Square Decomposition', 'Unicode decomposition type'),
            (SequenceType.ISOLATED_DECOMPOSITION.value, 'Isolated Decomposition', 'Unicode decomposition type'),
            (SequenceType.FINAL_DECOMPOSITION.value, 'Final Decomposition', 'Unicode decomposition type'),
            (SequenceType.INITIAL_DECOMPOSITION.value, 'Initial Decomposition', 'Unicode decomposition type'),
            (SequenceType.MEDIAL_DECOMPOSITION.value, 'Medial Decomposition', 'Unicode decomposition type'),
            (SequenceType.SMALL_DECOMPOSITION.value, 'Small Decomposition', 'Unicode decomposition type'),
            (SequenceType.NARROW_DECOMPOSITION.value, 'Narrow Decomposition', 'Unicode decomposition type'),

            (SequenceType.Z_VARIANT.value, 'Z-Variant', 'Unit sequence representing an equivalent or typographical variant Chinese character'),
            (SequenceType.HIEROGLYPHIC_ALTERNATIVE.value, 'Hieroglyphic Alternative', 'Equivalent Hieroglyph sequence')
        ]
        load_lookup(cursor, 'sequence_type', data)


    def _load_derivations(self, cursor, indic_letter_data, semitic_letter_data, verify_script):
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
        independent_scripts = {'Mend', 'Egyp', 'Lina', 'Hluw', 'Xsux', 'Xpeo', 'Ogam', 'Elba', 'Dupl', 'Sgnw', 'Shaw', 'Vith',
                               'Vaii', 'Bamu', 'Berf', 'Nkoo', 'Wara', 'Gonm', 'Toto', 'Osma', 'Adlm', 'Gara', 'Medf', 'Bass',
                               'Yezi', 'Tnsa', 'Olck', 'Thaa', 'Tols', 'Nagm', 'Sora', 'Wcho', 'Mroo', 'Onao', 'Sunu', 'Yiii', 'Tang'}

        cursor.execute("DELETE FROM code_point_derivation")  # updates generally expected on this table, just clear

        self._load_letter_derivation_data(cursor, indic_letter_data, ScriptDatabase._INDIC_ORDER, verify_script)
        self._load_letter_derivation_data(cursor, semitic_letter_data, ScriptDatabase._SEMITIC_ORDER, verify_script)

        # Identify all the independently-derived characters
        cursor.execute(f"""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, notes)
            SELECT id, ?, ?, ?, 'Independent script: Assume independent character'
            FROM code_point 
            WHERE script_code IN {self._get_sql_in_str_list(independent_scripts)}""",
            (ord(self.NO_PARENT_CHARACTER), DerivationType.DEFAULT.value, Certainty.AUTOMATED.value))

        with open(os.path.join(self._unicode_path, 'Unikemet.txt'), 'r') as file:
            for line in file:
                if not line.isspace() and not line.startswith('#'):
                    parts = line.split('\t')

                    if parts[1] == 'kEH_AltSeq':
                        seq_id = self.get_next_sequence_id()
                        child_id = int(parts[0][2:], 16)
                        cursor.execute("INSERT INTO sequence (id, sequence_type_id) VALUES (?, ?)", (seq_id, SequenceType.HIEROGLYPHIC_ALTERNATIVE.value))
                        cursor.execute("UPDATE code_point SET equivalent_sequence_id = ? WHERE id = ?", (seq_id, child_id))
                        # since hieroglyphs were default set to NO_PARENT, remove that:
                        cursor.execute("DELETE FROM code_point_derivation WHERE child_id = ? AND parent_id = ?", (child_id, ord(self.NO_PARENT_CHARACTER)))
                        offset = 1
                        for i, code_point in enumerate(parts[2].split(' ')):
                            if code_point.isspace():
                                offset -= 1  # out of caution, but this seems to be an end-of-line issue
                            else:
                                cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?, ?, ?)", (seq_id, int(code_point, 16), i + offset))

        with open(os.path.join(self._unicode_path, 'Unihan_Variants.txt'), 'r') as file:
            for line in file:
                if not line.isspace() and not line.startswith('#'):
                    parts = line.split('\t')

                    if parts[1] == 'kTraditionalVariant':  # mirror property is kSimplifiedVariant - should only need to check one
                        for parent_code in parts[2].split(' '):
                            if parts[0] != parent_code:  # it's possible for a simplified character to map to itself
                                cursor.execute("""
                                    INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
                                    VALUES (?, ?, ?, ?, ?)""",
                                    (int(parts[0][2:], 16), int(parent_code[2:], 16), DerivationType.SIMPLIFICATION.value, Certainty.AUTOMATED.value, 'Unihan Database'))
                                    # the [2:] slices off the U+

                    # This is a self-mirror property. if X zVariant Y then Y zVariant X.
                    # There's no real indication which should be canonical that I can find, so I'm arbitrarily making it the lowest code point
                    elif parts[1] == 'kZVariant':
                        principal_id = int(parts[0][2:], 16)
                        for sub_parts in parts[2].split(' '):
                            other_id = int(sub_parts[2:].split('<')[0], 16)
                            if principal_id > other_id:
                                seq_id = self.get_next_sequence_id()
                                cursor.execute("INSERT INTO sequence (id, sequence_type_id) VALUES (?, ?)", (seq_id, SequenceType.Z_VARIANT.value))
                                cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?, ?, ?)", (seq_id, other_id, 1))
                                cursor.execute("UPDATE code_point SET equivalent_sequence_id = ? WHERE id = ?", (seq_id, principal_id))

        # add derivations from equivalent sequences, assuming the equivalent characters are the base building blocks (the parent)
        # Formatting/control/space characters are not eligible (they aren't graphical, right? ... right???)
        cursor.execute(f"""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
            SELECT
                cp1.id,
                cp2.id,
                CASE WHEN COUNT(item_id) OVER (PARTITION BY equiv.sequence_id) = 1
                    THEN CASE WHEN sequence_type_id = {SequenceType.CANONICAL_DECOMPOSITION.value} THEN {DerivationType.DUPLICATE.value}
                              WHEN sequence_type_id IN ({SequenceType.NO_BREAK_DECOMPOSITION.value},
                                                        {SequenceType.SUPER_DECOMPOSITION.value}, 
                                                        {SequenceType.SUB_DECOMPOSITION.value}, 
                                                        {SequenceType.SMALL_DECOMPOSITION.value}) THEN {DerivationType.COPY.value}
                              ELSE {DerivationType.DEFAULT.value}
                         END
                    ELSE {DerivationType.DEFAULT.value}
                END,
                {Certainty.AUTOMATED.value},
                CASE WHEN sequence_type_id = {SequenceType.Z_VARIANT.value} THEN 'Unihan database, zVariant'
                     WHEN sequence_type_id = {SequenceType.HIEROGLYPHIC_ALTERNATIVE.value} THEN 'Unicode Character Database Unikemet.txt'
                     ELSE 'Unicode Character Database decomposition data'
                END
            FROM
                sequence_item equiv
                INNER JOIN sequence seq ON seq.id = equiv.sequence_id
                INNER JOIN code_point cp1 ON cp1.equivalent_sequence_id = seq.id
                INNER JOIN code_point cp2 ON cp2.id = equiv.item_id
            WHERE
                sequence_type_id >= 100
                AND cp1.general_category_code NOT LIKE 'Z_'
                AND cp1.general_category_code NOT LIKE 'C_'
                AND cp2.general_category_code NOT LIKE 'Z_'
                AND cp2.general_category_code NOT LIKE 'C_'
            ON CONFLICT DO NOTHING""")
        # sequence_type_id >= 100 is a bit hacky for now, I've basically put the equivalency sequence types at IDs 100+
        # A more "proper" solution would be to have a category associated to a sequence_type, but that feels like over-engineering for the moment
        # conflicts are expected when a character decomposes into multiple copies of a code point,
        # minimal enough that ON CONFLICT DO NOTHING is probably the better query option than advance filtering

        # add derivations from case mapping, assuming lowercase to be derived from uppercase
        cursor.execute("""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
            SELECT id, simple_uppercase_mapping_id, ?, ?, 'Unicode Character Database case mapping data'
            FROM code_point
            WHERE simple_uppercase_mapping_id IS NOT NULL""",
                       (DerivationType.DEFAULT.value, Certainty.AUTOMATED.value))
        # casing isn't 100% 1:1 so need to do mappings in both directions
        cursor.execute("""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, source)
            SELECT simple_lowercase_mapping_id, id, ?, ?, 'Unicode Character Database case mapping data'
            FROM code_point cp1
            WHERE id <> (SELECT simple_uppercase_mapping_id FROM code_point cp2 WHERE cp2.id = cp1.simple_lowercase_mapping_id)""",
                       (DerivationType.DEFAULT.value, Certainty.AUTOMATED.value))

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
                            'Parent'] else self.NO_PARENT_CHARACTER  # This won't be in the defaults dictionary

                        # Logic for defaulting to Uncertain on no parent: For historical scripts, this is usually more a function of a lack of records
                        # For modern scripts, the inventor is generally aware of existing writing systems, and may have been inspired
                        certainty = int(resolve_default(defaults, script, row, 'Certainty Type',
                                                        overriding_default=str(Certainty.UNCERTAIN.value),
                                                        override_condition=(parents == self.NO_PARENT_CHARACTER),
                                                        last_resort=str(Certainty.UNSPECIFIED.value)))

                        # Overriding default here is for convenience: An Assumed certainty means there is no source, so allows us to specify a source in defaults for all else.
                        source = resolve_default(defaults, script, row, 'Source', overriding_default=None,
                                                 override_condition=(certainty == Certainty.ASSUMED.value))

                        notes = resolve_default(defaults, script, row, 'Notes')
                        derivation_types = resolve_default(defaults, script, row, 'Derivation Type',
                                                           last_resort=str(DerivationType.DEFAULT.value))

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

        del wdata['armi']  # Remove aramaic, it's better in Semitic dictionary

        return wdata

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


    def _generate_std_alphabets(self, indic_letter_dict, semitic_letter_dict):
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


    def _load_letter_derivation_data(self, cursor, letter_dict, letter_order, verify):
        script_dict = self.get_code_to_script_dict()
        for script_code in letter_dict:
            if script_code not in ScriptDatabase._EXCLUDED_GEN_CODES:
                script_name = script_dict[script_code.title()]

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
                                        (ord(letter),
                                         ord(parent_letters[0]),
                                         DerivationType.DEFAULT.value,
                                         Certainty.AUTOMATED.value,
                                         'Wikipedia letter cognate charts',
                                         'Not necessarily graphical derivation but likely'))
                            elif verify:  # temporary, for later manual work
                                print(f"Data generation warning: {len(parent_letters)} parent letters found for {letter_class} in {script_code}")

    # TODO: this no longer works with the current alphabet architecture
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

    # The derived parameters are for saving time: if they've been determined by other means, this method has less to compute
    def _load_alphabet(self, cursor, script_exemplars, unicase_languages, alphabet_str, lang_code, script_code, derived_script_code, derived_case, verify):
        def insert_seq_char(cursor, cp_list, seq_id, char, order_num):
            cp_list.append(char)
            cursor.execute("""
                INSERT INTO sequence_item (sequence_id, item_id, order_num)
                VALUES (?, ?, ?)""",
                (seq_id, ord(c), order_num))

        alphabet_id = self.get_next_sequence_id()
        alphabet_order_num = 0
        letter_id = 0
        letter_order_num = 0
        unicode_escape = None
        escape = False
        code_points = []
        alphabet_letters = []
        has_dotted_I = False
        is_unicase = lang_code in unicase_languages

        # The unicase clause is academic: I don't think any language is both unicase and has capital dotted I
        if 'İ' in alphabet_str and not is_unicase:
            has_dotted_I = True
            alphabet_str = alphabet_str.replace('İ', '')

        cursor.execute("INSERT INTO sequence (id, sequence_type_id) VALUES (?, ?)", (alphabet_id, SequenceType.ALPHABET.value))
        for c in alphabet_str:
            if escape:
                escape = False
                if c == 'u':
                    unicode_escape = ''
                elif letter_order_num == 0:
                    insert_seq_char(cursor, code_points, alphabet_id, c, alphabet_order_num)
                    alphabet_letters.append(c)
                else:
                    insert_seq_char(cursor, code_points, letter_id, c, letter_order_num)
                    alphabet_letters[-1] = alphabet_letters[-1] + c
            elif c == '{':
                alphabet_order_num += 1
                letter_order_num += 1
                letter_id = self.get_next_sequence_id()
                alphabet_letters.append('')
                cursor.execute("INSERT INTO sequence (id, sequence_type_id) VALUES (?, ?)", (letter_id, SequenceType.LETTER.value))
                cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?, ?, ?)", (alphabet_id, letter_id, alphabet_order_num))
            elif c == '}':
                letter_order_num = 0
            elif c == '\\':
                alphabet_order_num += 1
                escape = True
            elif c == ' ':
                continue
            elif unicode_escape is not None:
                if len(unicode_escape) == 4:
                    char = chr(int(unicode_escape, 16))
                    unicode_escape = None
                    if letter_order_num == 0:
                        insert_seq_char(cursor, code_points, alphabet_id, char, alphabet_order_num)
                        alphabet_letters.append(c)
                    else:
                        insert_seq_char(cursor, code_points, letter_id, char, letter_order_num)
                        alphabet_letters[-1] = alphabet_letters[-1] + c
                else:
                    unicode_escape += c
            elif letter_order_num == 0:  # stand-alone codepoint
                alphabet_order_num += 1
                insert_seq_char(cursor, code_points, alphabet_id, c, alphabet_order_num)
                alphabet_letters.append(c)
            else:  # code-point constituting part of a letter
                insert_seq_char(cursor, code_points, letter_id, c, letter_order_num)
                alphabet_letters[-1] = alphabet_letters[-1] + c
                letter_order_num += 1

        # finalizing the alphabet

        if verify and len(alphabet_letters) != len(set(alphabet_letters)):
            print(f"Detected duplicate letters in alphabet for {lang_code}, {script_code}: {alphabet_letters}")

        if derived_script_code is None and script_code:
            derived_script_code = script_code

        candidate_script_codes = []
        if derived_script_code is None or verify:  # no script specified, must find it in data
            candidate_script_codes = cursor.execute(f"""
                SELECT DISTINCT script_code FROM code_point
                WHERE text IN {self._get_sql_in_str_list(code_points)}
                AND script_code NOT IN ('{ScriptDatabase.INHERITED_SCRIPT}', '{ScriptDatabase.COMMON_SCRIPT}')""").fetchall()

        if derived_script_code is None and len(candidate_script_codes) == 1:
            derived_script_code = candidate_script_codes[0][0]
        elif verify and len(candidate_script_codes) != 1:  # TODO also check variant data
            print(f"Unable to determine unique script for {lang_code}: {candidate_script_codes}")

        # TODO - implement other lowercase/uppercase Unicode prop
        if lang_code == 'de':
            None
        alphabet_case = derived_case if derived_case else 'Lo'

        if not derived_case or verify:
            letter_cases = cursor.execute(f"""
                SELECT DISTINCT general_category_code FROM code_point
                WHERE text IN {self._get_sql_in_str_list(code_points)}
                AND general_category_code IN ('Lu', 'Ll', 'Lo')""").fetchall()
            letter_cases = [l[0] for l in letter_cases]

            if 'Ll' in letter_cases: # cldr data is generally lower case or uncased
                if verify and 'Lu' in letter_cases and not is_unicase:
                    print(f'Detected both upper and lower case characters in alphabet for {lang_code}, {derived_script_code}')

                alphabet_case = 'Ll'
                if not is_unicase: # languages using a single case of a cased script
                    # We also want to add upper-case alphabet, but first run through a few of special cases of upper-casing cause language is hard
                    if has_dotted_I:
                        alphabet_str = alphabet_str.replace('i', 'İ')
                    if lang_code == 'kaa' and derived_script_code == 'Latn':
                        alphabet_str = alphabet_str.replace('ı', 'Í')  # why?

                    # Per Wikipedia, capital esszett is officially preferred in Standard German as of 2024
                    #  Mimicking that here because having more distinct characters is more in line with this project anyways
                    #  (though later may need to tailor to German varieties - Swiss is fine as it doesn't use esszett to being with)
                    # Greek final sigma will result in duplicate capital sigma, and then a couple that didn't map correctly
                    alphabet_str = alphabet_str.replace('ß', 'ẞ').replace('ς', '').replace('ΐ', '{Ϊ́}').replace('ΰ', '{Ϋ́}')

                    self._load_alphabet(cursor, script_exemplars, unicase_languages, alphabet_str.upper(), lang_code, script_code, derived_script_code, 'Lu', verify)
            elif 'Lu' in letter_cases:
                if verify and 'Ll' in letter_cases and not is_unicase:
                    print(f'Detected both upper and lower case characters in alphabet for {lang_code}, {derived_script_code}')
                alphabet_case = 'Lu'

        is_script_exemplar = None
        if derived_script_code in script_exemplars:
            is_script_exemplar = (script_exemplars[derived_script_code] == lang_code) and (is_unicase or alphabet_case in ('Lo', 'Lu'))
        elif verify:
            print(f"Missing canonical language for script {derived_script_code}")

        cursor.execute("""
            INSERT INTO alphabet (id, lang_code, script_code, letter_case, is_language_exemplar, is_script_exemplar)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (alphabet_id, lang_code, derived_script_code, alphabet_case, script_code is None and (is_unicase or alphabet_case in ('Lo', 'Lu')), is_script_exemplar))


    def _load_alphabet_data(self, cursor, verify):

        script_exemplars = {}
        with open(os.path.join(self._resource_path, 'script_exemplars.csv'), 'r') as csvfile:
            for row in csv.DictReader(csvfile):
                script_exemplars[row['Script']] = row['Language']

        unicase_languages = []
        with open(os.path.join(self._resource_path, 'unicase_languages.txt'), 'r') as file:
            for line in file:
                unicase_languages.append(line.strip())

        # yes an xml parser would be more appropriate, but this is a simple task (and lxml seemed to choke and I don't feel like learning another module...)
        exemplar_pattern = re.compile(r'<exemplarCharacters(?:\s(?:draft|reference)[^>]+)?>\[(.+)]</exemplarCharacters>')
        for file_name in os.listdir(os.path.join(self._unicode_path, 'cldr')):
            with open(os.path.join(self._unicode_path, 'cldr', file_name), 'r') as file:
                exemplar_found = False
                line_number = 0
                for line in file:
                    line_number += 1
                    match = exemplar_pattern.search(line)
                    if match:
                        lang_str = file_name.split('.')[0].split('_')
                        if file_name == 'ja.xml': # special case hack-y handling
                            hiragana = ''
                            katakana = ''
                            kanji = ''
                            for c in match.group(1):
                                if c == 'ー':  # shared character
                                    katakana += c
                                    hiragana += c
                                elif c != ' ':
                                    script_code = cursor.execute("SELECT script_code FROM code_point WHERE text = ?", (c,)).fetchone()[0]
                                    if script_code == 'Kana':
                                        katakana += c
                                    elif script_code == 'Hira':
                                        hiragana += c
                                    elif script_code == 'Hani':
                                        kanji += c
                                    elif verify:
                                        print(f"Error parsing Japanese CLDR data. Unexpected script {script_code} for letter {c}")
                            self._load_alphabet(cursor, script_exemplars, unicase_languages, katakana, 'ja', 'Kana', 'Kana', 'Lo', verify)
                            self._load_alphabet(cursor, script_exemplars, unicase_languages, hiragana, 'ja', 'Hira', 'Hira', 'Lo', verify)
                            self._load_alphabet(cursor, script_exemplars, unicase_languages, kanji, 'ja', None, 'Hani', 'Lo', verify) # none script code for exemplar
                        else:
                            self._load_alphabet(cursor,
                                                script_exemplars,
                                                unicase_languages,
                                                match.group(1),
                                                lang_str[0],
                                                lang_str[1] if len(lang_str) > 1 else None,
                                                None,
                                                None,
                                                verify)
                        exemplar_found = True
                    if exemplar_found:
                        continue  # next file
                if not exemplar_found and verify and line_number > 15:
                    # line number is a blunt tool to avoid excessive reporting on the "stub" entries
                    print(f'Could not find exemplar characters in {file_name}')


    def load_database(self, load_options=None):
        def output_info(message, start_time, lap_time):
            current_time = time.time()
            print(message + f" Elapsed: {current_time - start_time:.2f} s (+{current_time - lap_time:.2f} s)")
            return current_time

        options = load_options if load_options else LoadOptions()
        output = options.output_debug_info

        if options.force_overwrite:
            if os.path.isfile(os.path.join(self._db_path, self._db_name)):
                os.remove(os.path.join(self._db_path, self._db_name))
            if os.path.isfile(os.path.join(self._db_path, self._db_name + '-journal')):
                os.remove(os.path.join(self._db_path, self._db_name + '-journal'))
            self._set_connection()
        if options.resource_path:
            self._set_resource_paths(options.resource_path)
        if options.saved_query_path:
            self._query_path = options.saved_query_path

        path = os.path.join(self._resource_path, 'cr-exclusion')
        if self._try_unzip_sources(os.path.join(self._resource_path, 'cr-exclusion')):
            if output: print(f'Source files unzipped to {self._resource_path}')
        elif output: print(f'At least one zip file not present in {path}, relying on existing files in {self._resource_path}')

        cur = self._cxn.cursor()
        if options.verify_data_sources:
            cur.execute("PRAGMA foreign_keys = ON")
        else:
            cur.execute("PRAGMA foreign_keys = OFF")

        start_time = time.time()
        lap_time = start_time
        if output: print('Setting up schema (starting timer)...')
        self._setup_schema(cur)

        self._load_lookups(cur)
        self._cxn.commit()
        self._load_scripts(cur)
        self._cxn.commit()
        if output: lap_time = output_info("Done loading lookups and script data.", start_time, lap_time)

        indic_letter_data = self._get_indic_letter_dict(options.verify_data_sources)
        semitic_letter_data = self._get_semitic_letter_dict()

        self._generate_private_use_data(indic_letter_data)
        self._generate_std_alphabets(indic_letter_data, semitic_letter_data)
        if output: lap_time = output_info("Done generating letter data.", start_time, lap_time)

        self._load_code_point_data(cur)
        self._cxn.commit()
        if output: lap_time = output_info("Done loading code point data.", start_time, lap_time)

        self._load_derivations(cur, indic_letter_data, semitic_letter_data, options.verify_data_sources)
        self._cxn.commit()
        if output: lap_time = output_info("Done loading derivation data.", start_time, lap_time)

        self._load_alphabet_data(cur, options.verify_data_sources)
        self._cxn.commit()
        if output: lap_time = output_info("Done loading alphabet data.", start_time, lap_time)

        if output:
            print(f'Database loaded. Total time: {time.time() - start_time:.2f} s. Total size: {os.path.getsize(os.path.join(self._db_path, self._db_name)) // 1000000} MB')
            # self._verify_script_coverage(cur) -> TODO this no longer works with new alphabet architecture
            self.print_table(self.execute_saved_query('Total derivation statistics'))

        cur.execute("PRAGMA foreign_keys = ON")

        return cur


class Certainty(Enum):
    NEAR_CERTAIN = 1
    LIKELY = 2
    UNCERTAIN = 3
    AUTOMATED = 4
    ASSUMED = 5
    UNSPECIFIED = 6


class SequenceType(Enum):
    BASE = 1
    LETTER = 2
    ALPHABET = 3


    CANONICAL_DECOMPOSITION = 100
    JAMO_CANONICAL_DECOMPOSITION = 101  # per standard 3.12.2 Hangul syllable decomposition is equivalent to regular decomposition
    COMPATIBILITY_DECOMPOSITION = 102
    NO_BREAK_DECOMPOSITION = 103
    SUPER_DECOMPOSITION = 104
    FRACTION_DECOMPOSITION = 105
    SUB_DECOMPOSITION = 106
    FONT_DECOMPOSITION = 107
    CIRCLE_DECOMPOSITION = 108
    WIDE_DECOMPOSITION = 109
    VERTICAL_DECOMPOSITION = 110
    SQUARE_DECOMPOSITION = 111
    ISOLATED_DECOMPOSITION = 112
    FINAL_DECOMPOSITION = 113
    INITIAL_DECOMPOSITION = 114
    MEDIAL_DECOMPOSITION = 115
    SMALL_DECOMPOSITION = 116
    NARROW_DECOMPOSITION = 117

    Z_VARIANT = 200
    HIEROGLYPHIC_ALTERNATIVE = 201


class DerivationType(Enum):
    DEFAULT = 1
    PORTION_COPY = 2
    SIMPLIFICATION = 3
    FROM_CURSIVE = 4
    COPY = 5
    DUPLICATE = 6
    PORTION = 7
    ROTATION = 8
    REFLECTION = 9


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
    #results = db.execute_saved_query('Get Character Ancestors', parameters=('a',))
    #db.print_table(results)

    cursor.close()