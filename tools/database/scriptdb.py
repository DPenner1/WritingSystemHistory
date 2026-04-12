import os
import sqlite3
import re
import csv
import time
from enum import Enum
from zipfile import ZipFile
from urllib.parse import quote


class LoadOptions:
    def __init__(self):
        self.force_overwrite = True  # at the moment a data-update mode is not well supported, this may default back to False when it is
        self.verify_data_sources = False
        self.output_debug_info = False
        self.vacuum_db = False
        # an index that speeds up loading, but that is unlikely to be that helpful (a non-trivial size increase of the DB otherwise)
        self.drop_code_point_name_index = True
        # path None = Default to leaving previous path alone, DB working subdirectories if not previously specified
        self.resource_path = None
        self.saved_query_path = None
        # columns that are less likely to be relevant
        self.drop_bidi_class_column = False
        self.drop_case_columns = False
        # Column and table
        self.drop_derivation_type = False
        # For FK reasons we load the language data first, but a minority are ultimately used (at least until more data is specified)
        self.drop_unused_languages = True

# effectively a tuple, but tuple too error-prone to specifying wrong values (order, expected values)
class SourceInfo:
    def __init__(self, citation_key, section=None, access_date=None):
        self.citation_key = citation_key
        self.section = section
        self.access_date = access_date


class ScriptDatabase:

    INHERITED_SCRIPT = 'Zinh'
    COMMON_SCRIPT = 'Zyyy'
    UNKNOWN_SCRIPT = 'Zzzz'
    UNICODE_MAX = 0x10FFFF
    NO_PARENT_CHARACTER = '\uFFFF'  # a Unicode non-character

    MANUAL_PROCESS_ID = 1
    DECOMPOSITION_PROCESS_ID = 2

    DEFAULT_LOAD = LoadOptions()

    DEBUG_LOAD = LoadOptions()
    DEBUG_LOAD.verify_data_sources = True
    DEBUG_LOAD.output_debug_info = True

    OPTIMIZED_LOAD = LoadOptions()
    OPTIMIZED_LOAD.drop_bidi_class_column = True
    OPTIMIZED_LOAD.drop_case_columns = True
    OPTIMIZED_LOAD.drop_derivation_type = True
    OPTIMIZED_LOAD.vacuum_db = True

    OPTIMIZED_DEBUG_LOAD = LoadOptions()
    OPTIMIZED_DEBUG_LOAD.drop_bidi_class_column = True
    OPTIMIZED_DEBUG_LOAD.drop_case_columns = True
    OPTIMIZED_DEBUG_LOAD.drop_derivation_type = True
    OPTIMIZED_DEBUG_LOAD.verify_data_sources = True
    OPTIMIZED_DEBUG_LOAD.output_debug_info = True
    OPTIMIZED_DEBUG_LOAD.vacuum_db = True

    _GENERATED_DIR_NAME = 'generated'
    _INDIC_ORDER = ['A', 'Ā', 'I', 'Ī', 'U', 'Ū', 'Ṛ', 'Ṝ', 'Ḷ', 'Ḹ', 'E', 'Ai', 'O', 'Au',
                    'Ka', 'Kha', 'Ga', 'Gha', 'Ṅa', 'Ca', 'Cha', 'Ja', 'Jha', 'Ña', 'Ṭa', 'Ṭha', 'Ḍa', 'Ḍha', 'Ṇa', 'Ta',
                    'Tha', 'Da', 'Dha', 'Na', 'Pa', 'Pha', 'Ba', 'Bha', 'Ma', 'Ya', 'Ra', 'La', 'Va', 'Śa', 'Ṣa', 'Sa','Ha']
    # diacritics, punctuation and dependent vowels
    _INDIC_SUPPLEMENT = ['DIGIT ZERO', 'DIGIT ONE', 'DIGIT TWO', 'DIGIT THREE', 'DIGIT FOUR', 'DIGIT FIVE', 'DIGIT SIX', 'DIGIT SEVEN', 'DIGIT EIGHT', 'DIGIT NINE',
                         'CANDRABINDU', 'ANUSVARA', 'VISARGA', 'VIRAMA', 'NUKTA', 'AVAGRAHA', 'DANDA', 'DOUBLE DANDA',
                         'PLACEHOLDER 1', 'PLACEHOLDER 2', 'PLACEHOLDER 3', 'PLACEHOLDER 4', 'PLACEHOLDER 5', 'PLACEHOLDER 6', 'PLACEHOLDER 7', 'PLACEHOLDER 8',
                         'VOWEL SIGN AA', 'VOWEL SIGN I', 'VOWEL SIGN II', 'VOWEL SIGN U', 'VOWEL SIGN UU', 'VOWEL SIGN VOCALIC R', 'VOWEL SIGN VOCALIC RR',
                         'VOWEL SIGN VOCALIC L', 'VOWEL SIGN VOCALIC LL', 'VOWEL SIGN E', 'VOWEL SIGN AI', 'VOWEL SIGN O', 'VOWEL SIGN AU']
    # not part of general Indic letters or automated, but list here is for consistent order of "extras" - only add to end to avoid desyncing with manual files
    _INDIC_MANUAL = ['LETTER EE', 'LETTER OO', 'LETTER RRA', 'VOWEL SIGN EE', 'VOWEL SIGN OO', 'LENGTH MARK', 'AI LENGTH MARK', 'SIGN SIDDHAM',
                     'LETTER LLA', 'LETTER LLLA', 'LETTER VOCALIC LL']
    # sign siddham (not to be confused with the script) is a weird one. Attested in Gupta and Pallava (and presumably Kadamba with Telugu and Kannada having it),
    # yet there's no Brahmi code point for it seemingly. And among the child scripts there's actually not that many named that way to automate it.
    # reference: https://www.unicode.org/L2/L2012/12123r2-devanagari-siddham.pdf
    _SEMITIC_ORDER = ['Aleph', 'Bet', 'Gimel', 'Dalet', 'He', 'Waw', 'Zayin', 'Heth', 'Teth', 'Yodh', 'Kaph', 'Lamedh',
                     'Mem', 'Nun', 'Samekh', 'Ayin', 'Pe', 'Tsade', 'Qoph', 'Resh', 'Shin', 'Taw']
    _DIGIT_ORDER = ['ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE']
    _PROTO_SINAITIC_ORDER = ['ALP', 'BAYT', 'GAML', 'DALT', 'DAG', 'HAW', 'WAW', 'ZAYN', 'HASIR', 'HAYT', 'TAB', 'YAD', 'KAP',
                              'LAMD', 'MAYM', 'NAHS', 'SAMK', 'AYN', 'PAY', 'PIT', 'SAD', 'QUP', 'QAW', 'RAS', 'SAMS', 'TAD', 'TAW']
    # Difficult to find a standard catalog, so I've put them as the translit at https://en.wikipedia.org/wiki/Demotic_Egyptian_script + ancestor hieroglyph
    _DEMOTIC_SUBSET = ['š M8', 'f I9', 'ẖ M12', 'ḥ F18Y1', 'ḏ U29', 'k V31', 't D37X1',  # current Coptic ancestors
                       'ı͗ M17', 'ꜥ O29Y1D36', 'n N35', 'h O4', 'ḥ2 V28', 'ḫ Aa1', 'š2 n37', 'q N29', 'g W11', 'ḏ2 G1U28',  # old coptic ancestors
                       'y Z7M17', 'p Q3', 'm G17']  # a few matched from Meroitic
    # short/long vowels based on the follwing order from Wikipedia: /æ/, /ɛ/, /ɪ/, /ɒ/, /ʌ/, /ʊ/ ... /ɑː/, /eɪ/, /iː/, /ɔː/, /oʊ/, /uː .. diphthongs:  /aɪ/, /ɔɪ/, /aʊ/, /juː/
    _PITMAN_ORDER = ['P', 'B', 'F', 'V', 'T', 'D', 'TH', 'DH', 'CH', 'J', 'S', 'Z' ,'K', 'G', 'SH', 'ZH', 'M', 'N', 'NG', 'H', 'L', 'R1', 'R2', 'W', 'Y',
                     'SHORT AW', 'SHORT A', 'SHORT E', 'SHORT I', 'SHORT O', 'SHORT U', 'LONG AW', 'LONG A', 'LONG E', 'LONG I', 'LONG O', 'LONG U',
                     'DIPHTHONG IE', 'DIPHTHONG OI', 'DIPHTHONG OW', 'DIPHTHONG EW']
    _CODE_POINT_STARTS = {'Kawi': 0x11F04, 'Psin': 0xF000, 'Egyd': 0xF200,
                          'Qabp': 0xE104, 'Qabk': 0xE204, 'Qabl': 0xE304, 'Qabn': 0xE404, 'Qabd': 0xE504, 'Qabg': 0xE604, 'Qaap': 0xEF00}

    # Brahmi, Kharoshti, Arabic, Phoenician which will be manually specified and the Aramaic code point not generally being included in Indic source
    # Can abo, Hangul, Kayah Li, Masaram Gondi, Sorang Sompeng, Pau cin hau will be manually specified due to higher independence or contribution from other scripts
    # Soyombo excluded due to elevated probability of script relationships being modified
    # Non-unicode scripts Ranjana, Tocharian, Brahmic variants 'asho', 'kush' excluded
    # Cuneiform has its own automated process
    _EXCLUDED_GEN_CODES = ['Brah', 'Khar', 'Hang', 'Cans', 'Kali', 'Soyo', 'Gonm', 'Sora', 'Pauc', 'Gupt', 'Plav',
                           'Ranj', 'Asho', 'Kush', 'Toch', 'Grek', 'Latn', 'Cyrl', 'Arab', 'Phnx', 'Psin', 'Xsux']

    def __init__(self, path='.', name='scripts.db'):
        self._db_name = name
        self._db_path = path
        is_existing_db = os.path.isfile(os.path.join(self._db_path, self._db_name))
        self._set_connection()
        self._set_resource_paths()
        self._query_path = os.path.join(self._db_path, 'queries')
        self._next_sequence_id = ScriptDatabase.UNICODE_MAX
        if is_existing_db:
            cursor = self._cxn.cursor()
            self._next_sequence_id = cursor.execute("SELECT MAX(id) FROM sequence").fetchone()[0]
            cursor.close()
            if not self._next_sequence_id or self._next_sequence_id < ScriptDatabase.UNICODE_MAX:
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


    def _get_unique_saved_query(self, query_name):
        query = ''
        for f in os.listdir(self._query_path):
            fileparts = f.split('.')
            if fileparts[1] == 'sql' and len(fileparts) == 2:
                parts = fileparts[0].split(' _')
                if len(parts) <= 2 and parts[0] == query_name:
                    return os.path.join(self._query_path, f)
            else:
                raise ValueError(f'Found non sql file in {self._query_path}')

        raise ValueError(f"No query named {query_name} found in {self._query_path}")

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
            unzip_file(os.path.join(zip_dir_path, 'UCD.zip'), 'NameAliases.txt', os.path.join(self._unicode_path, 'NameAliases.txt')),
            unzip_file(os.path.join(zip_dir_path, 'UCD.zip'), 'PropList.txt', os.path.join(self._unicode_path, 'PropList.txt')),
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
        script_defers = []  # some self-referential and mutually referencing table stuff, need base data in first for later FKs
        with open(os.path.join(self._resource_path, 'scripts.csv'), 'r') as file:
            for row in csv.DictReader(file):
                code = row['Code']
                id = int(row['ISO ID'])
                type = int(row['Type'])
                name = row['Name'] if row['Name'] else None
                alias = row['Unicode Alias'] if row['Unicode Alias'] else None
                version = row['Unicode Version'] if row['Unicode Version'] else None
                subversion = row['Unicode Subversion'] if row['Unicode Subversion'] else None
                parent = row['Parent'] if row['Parent'] else None
                lang = row['Common Lang'] if row['Common Lang'] else None
                script_defers.append((parent, lang, code))

                cursor.execute("""
                    INSERT INTO script (code, name, type_id, u_alias, iso_id, u_version_added, u_subversion_added) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (code) DO UPDATE SET
                        name = ?,
                        type_id = ?,
                        u_alias = ?,
                        u_version_added = ?,
                        u_subversion_added = ?""",
                        (code, name, type, alias, id, version, subversion, name, type, alias, version, subversion))  # TODO: check stability policy

        # at the moment keeping this a distinct file and not merging it into scripts.csv as I'm uncertain of the usefulness of this field
        with open(os.path.join(self._resource_path, 'script_variants.csv'), 'r') as file:
            for row in csv.DictReader(file):
                cursor.execute("UPDATE script SET canonical_script_code = ? WHERE code = ?", (row['Main'], row['Variant']))

        return script_defers


    def _load_deferred_script_fields(self, cursor, deferred_fields):
        cursor.executemany("UPDATE script SET parent_code = ?, main_lang_code = ? WHERE code = ?", deferred_fields)


    def _load_languages(self, cursor):
        with open(os.path.join(self._resource_path, 'iana_lang_subtag.txt'), 'r') as file:
            record = dict()
            macrolanguages = []
            for line in file:
                if line.startswith(" "):
                    continue  # hacky, just assuming that the fields we're interested in aren't the multi-line ones
                elif line.startswith("%%"): # record separator (technically we'll miss the last one but the file seems somewhat ordered and we don't need the end)
                    if "File-Date" in record:
                        None # For now, but could be useful later for update purposes
                    elif record["Type"] == 'language' and 'Deprecated' not in record:  # we don't need any other type
                        lang_name = 'Greek' if record['Subtag'] == 'el' else record['Description'][0].split('(')[0].strip()
                        # Just correcting one language name "Modern Greek" I don't like in file, because that will probably cause unexpected ordering
                        # otherwise, we just remove parentheticals. In theory better language names might be sourced from the en CLDR which we alreayd
                        # have in the resources, but the IANA descriptions seem decent enough and we're already parsing it

                        cursor.execute("INSERT INTO language (code, name, default_script_code) VALUES (?, ?, ?)",
                            (record['Subtag'], lang_name, record['Suppress-Script'] if 'Suppress-Script' in record else None))
                        if 'Macrolanguage' in record:
                             macrolanguages.append((record['Macrolanguage'], record['Subtag']))
                    record = dict()
                else:
                    parts = line.split(":")
                    if len(parts) < 2:
                        raise ValueError("unexpected language file format")
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key == 'Description':  # multiple descriptions possible, capture for now though we aren't really accounting for it yet
                        if key not in record:
                            record[key] = []
                        record[key].append(value)
                    else:
                        record[key] = value

            cursor.executemany("UPDATE language SET macrolanguage_code = ? WHERE code = ?", macrolanguages)


    def _load_source(self, cursor, citation_key, author_str, title, url):
        return cursor.execute("INSERT INTO source (citation_key, authors, title, url) VALUES (?,?,?,?) RETURNING id", (citation_key, author_str, title, url)).fetchone()[0]


    def _load_sources(self, cursor):
        parents = dict()
        with open(os.path.join(self._resource_path, 'sources.csv'), 'r') as csvfile:
            for row in csv.DictReader(csvfile):
                self._load_source(cursor, row["Citation Key"], row['Authors'] if row['Authors'] else None, row["Title"], row["URL"] if row['URL'] else None)
                if row["Parent"]:
                    parents[row["Citation Key"]] = row["Parent"]
        for key in parents:
            parent_id = cursor.execute("SELECT id FROM source WHERE citation_key = ?", (parents[key], )).fetchone()[0]
            cursor.execute("UPDATE source SET parent_id = ? WHERE citation_key = ?", (parent_id, key))


    def _get_or_create_source_id(self, cursor, citation_key):
        if citation_key.startswith('Wikipedia: '):
            # was not consistent in data files with using underscores/spaces
            citation_key = citation_key.replace('_', ' ').strip()
        id = cursor.execute("SELECT id FROM source WHERE citation_key = ?", (citation_key, )).fetchall()
        if id:
            return id[0][0]
        if citation_key.startswith('Wikipedia: '):
            wiki_page = citation_key[len('Wikipedia: '):]
            return self._load_source(cursor, citation_key, None, wiki_page, f"https://en.wikipedia.org/wiki/{quote(wiki_page.replace(' ', '_'))}")

        raise ValueError("No source found for citation key " + citation_key)

    @staticmethod
    def is_private_use(id):
        return (0xE000 <= id <= 0xF8FF) or (0xF0000 <= id <= 0xFFFFD) or (0x100000 <= id <= 0x10FFFD)

    @staticmethod
    def _add_or_increment_dict_entry(dictionary, key, value):
        if key in dictionary:
            dictionary[key] += value
        else:
            dictionary[key] = value


    def _insert_name_indexer(self, cursor, cp_id, name):
        words = name.split(' ')
        for i, word in enumerate(words):
            cursor.execute("INSERT INTO name_indexer (code_point_id, order_num, word) VALUES (?, ?, ?)", (cp_id, i + 1, word))


    def _insert_code_point(self, cursor, id, name, script_code, general_category_code, bidi_class_code, is_other_alphabetic=False, is_graphical_exception=False):
        if script_code is None: script_code = 'Zzzz'
        if general_category_code is None: general_category_code = 'Cn'
        if bidi_class_code is None: bidi_class_code = 'L'

        is_graphical = is_graphical_exception != (general_category_code[0] not in ('C', 'Z'))
        is_alphabetic = general_category_code[0] == 'L' or general_category_code == 'Nl' or is_other_alphabetic
        cursor.execute("INSERT INTO sequence (id, type_id) VALUES (?, ?) ON CONFLICT DO NOTHING", (id, SequenceType.BASE.value))
        if self.is_private_use(id):
            cursor.execute("""
                INSERT INTO code_point (id, raw_name, script_code, general_category_code, bidi_class_code, is_alphabetic, is_independently_graphical)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO 
                UPDATE SET raw_name = ?, script_code = ?, general_category_code = ?, bidi_class_code = ?, is_alphabetic = ?, is_independently_graphical = ?""",
                (id, name, script_code, general_category_code, bidi_class_code, is_alphabetic, is_graphical,
                     name, script_code, general_category_code, bidi_class_code, is_alphabetic, is_graphical))
        else:
            cursor.execute("""
                INSERT INTO code_point (id, raw_name, script_code, general_category_code, bidi_class_code, is_alphabetic, is_independently_graphical)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING""",
                (id, name, script_code, general_category_code, bidi_class_code, is_alphabetic, is_graphical))
            cursor.execute("DELETE FROM name_indexer WHERE code_point_id = ?", (id, ))
                # TODO double check stability policy
        if name:
            self._insert_name_indexer(cursor, id, name)

    @staticmethod
    def _unicode_range(range_str):
        parts = range_str.split('..')
        num_parts = len(parts)
        if num_parts > 2:
            raise ValueError("Bad programmer")
        start = int(parts[0], 16)
        end = start if num_parts == 1 else int(parts[1], 16)
        return range(start, end + 1)


    def _load_code_point_data_basics(self, cursor):
        # Reset since sequence ids not stable -> TODO in principle we could be smarter about this
        cursor.execute("DELETE FROM sequence_item")
        cursor.execute("DELETE FROM alphabet_source")
        cursor.execute("DELETE FROM alphabet")
        cursor.execute("DELETE FROM sequence WHERE id > ?", (ScriptDatabase.UNICODE_MAX,))

        self._insert_code_point(cursor, ord(self.NO_PARENT_CHARACTER), name='NO PARENT CHARACTER', bidi_class_code='Bn', script_code=None, general_category_code=None)

        with open(os.path.join(self._unicode_path, 'Scripts.txt'), 'r') as file:
            for row in csv.reader(filter(lambda r: not r.isspace() and not r.startswith('#'), file), delimiter=';'):
                script_name = row[1].split('#')[0].strip()
                script_code = cursor.execute("SELECT code FROM script WHERE u_alias = ?", (script_name,)).fetchone()[0]
                for i in self._unicode_range(row[0]):
                    self._insert_code_point(cursor, i, name=None, script_code=script_code, bidi_class_code=None, general_category_code=None)


    def _load_code_point_data_main(self, cursor):
        # can't reliably call this outside the outer function (derived props), so insulating it here
        def update_code_point(cursor, id, name, general_category, bidi_class, upper_mapping, lower_mapping, decom_str):
            decom_pattern = re.compile(r'^(?:<([a-zA-Z]+)> )?([\s0-9A-F]+)$')
            decom_type = None
            decom_ids = []

            # these don't take into account exceptions, must be handled separately after
            is_alphabetic = general_category[0] == 'L' or general_category == 'Nl'
            is_graphical = general_category[0] not in ('C', 'Z')

            seq_id = None
            if decom_str:
                match = decom_pattern.match(decom_str)
                decom_ids = [int(id, 16) for id in match.group(2).split(' ')]
                decom_type = match.group(1) if match.group(1) else 'canonical'
                seq_id = self.get_next_sequence_id()
                cursor.execute("""
                            INSERT INTO sequence (id, type_id) 
                            VALUES (?, (SELECT id FROM sequence_type WHERE name LIKE ?))""",
                               (seq_id, decom_type.title() + '%'))
                for i, decom_id in enumerate(decom_ids):
                    cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?, ?, ?)", (seq_id, decom_id, i + 1))

            cursor.execute("""
                UPDATE code_point
                SET 
                    raw_name = ?,
                    general_category_code = ?,
                    bidi_class_code = ?,
                    simple_uppercase_mapping_id = ?,
                    simple_lowercase_mapping_id = ?,
                    equivalent_sequence_id = ?,
                    is_alphabetic = ?,
                    is_independently_graphical = ?
                WHERE id = ?""",
                   (name, general_category, bidi_class, upper_mapping, lower_mapping, seq_id, is_alphabetic, is_graphical, id))
            cursor.execute("DELETE FROM name_indexer WHERE code_point_id = ?", (id, ))
            if name:
                self._insert_name_indexer(cursor, id, name)

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
        JAMO_SHORT_NAME = {0x1100: 'G', 0x1101: 'GG', 0x1102: 'N', 0x1103: 'D', 0x1104: 'DD', 0x1105: 'R', 0x1106: 'M', 0x1107: 'B', 0x1108: 'BB', 0x1109: 'S',
                           0x110A: 'SS', 0x110B: '', 0x110C: 'J', 0x110D: 'JJ', 0x110E: 'C', 0x110F: 'K', 0x1110: 'T', 0x1111: 'P', 0x1112: 'H', 0x1161: 'A',
                           0x1162: 'AE', 0x1163: 'YA', 0x1164: 'YAE', 0x1165: 'EO', 0x1166: 'E', 0x1167: 'YEO', 0x1168: 'YE', 0x1169: '0', 0x116A: 'WA', 0x116B: 'WAE',
                           0x116C: 'OE', 0x116D: 'YO', 0x116E: 'U', 0x116F: 'WEO', 0x1170: 'WE', 0x1171: 'WI', 0x1172: 'YU', 0x1173: 'EU', 0x1174: 'YI', 0x1175: 'I',
                           0x11A8: 'G', 0x11A9: 'GG', 0x11AA: 'GS', 0x11AB: 'N', 0x11AC: 'NJ', 0x11AD: 'NH', 0x11AE: 'D', 0x11AF: 'L', 0x11B0: 'LG', 0x11B1: 'LM',
                           0x11B2: 'LB', 0x11B3: 'LS', 0x11B4: 'LT', 0x11B5: 'LP', 0x11B6: 'LH', 0x11B7: 'M', 0x11B8: 'B', 0x11B9: 'BS', 0x11BA: 'S', 0x11BB: 'SS',
                           0x11BC: 'NG', 0x11BD: 'J', 0x11BE: 'C', 0x11BF: 'K', 0x11C0: 'T', 0x11C1: 'P', 0x11C2: 'H', }

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
                                name = JAMO_SHORT_NAME[l_part] + JAMO_SHORT_NAME[v_part]
                            else:
                                temp, t_index = divmod(s_index, T_COUNT)
                                lv_index = temp * T_COUNT
                                lv_part = S_BASE + lv_index
                                t_part = T_BASE + t_index
                                decom_str = f"<jamo> {hex(lv_part)[2:].upper()} {hex(t_part)[2:].upper()}"
                                lv_name = cursor.execute("SELECT raw_name FROM code_point WHERE id = ?", (lv_part,)).fetchone()[0]
                                name = lv_name + JAMO_SHORT_NAME[t_part]

                        update_code_point(cursor, i, name, general_category, bidi_class, upper_mapping, lower_mapping, decom_str)

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
                            if 'Surrogate' in parts[0] or 'Private' in parts[0]: # we aren't cataloguing these ranges
                                continue
                            in_range = True
                    else:  # Unicode standard 4.8 with some shortcuts taken
                        if ((0x13460 <= code_point <= 0x143FA) or (0x18B00 <= code_point <= 0x18CD5) or (0x1B170 <= code_point <= 0x1B2FB) or
                            (0xF900 <= code_point <= 0xFA6D) or (0xFA70 <= code_point <= 0XFAD9) or (0x2F800 <= code_point <= 0x2FA1D)):
                            name = None
                        else:
                            name = line[1]
                    if not in_range:
                        update_code_point(cursor, code_point, name, general_category, bidi_class, upper_mapping, lower_mapping, decom_str)


    def _load_code_point_data_exceptions(self, cursor):
        with open(os.path.join(self._unicode_path, 'NameAliases.txt'), 'r') as file:
            for row in csv.reader(filter(lambda r: not r.isspace() and not r.startswith('#'), file), delimiter = ';'):
                if row[2].strip() in ['correction', 'figment', 'control']:
                    cursor.execute("UPDATE code_point SET alt_name = CONCAT(alt_name, ' / ', ?) WHERE id = ? AND alt_name IS NOT NULL", (row[1], int(row[0], 16)))
                    cursor.execute("UPDATE code_point SET alt_name = ? WHERE id = ? AND alt_name IS NULL", (row[1], int(row[0], 16)))

        with open(os.path.join(self._unicode_path, 'PropList.txt'), 'r') as file:
            for row in csv.reader(filter(lambda r: not r.isspace() and not r.startswith('#'), file), delimiter = ';'):
                property = row[1].split('#')[0].strip()
                if property == 'Other_Alphabetic':
                    for i in self._unicode_range(row[0]):
                        cursor.execute("UPDATE code_point SET is_alphabetic = 1 WHERE id = ?", (i,))
                elif property == 'Other_Lowercase':
                    for i in self._unicode_range(row[0]):
                        cursor.execute("UPDATE code_point SET is_alphabetic = 1, is_lowercase = 1 WHERE id = ?", (i,))
                elif property == 'Other_Uppercase':
                    for i in self._unicode_range(row[0]):
                        cursor.execute("UPDATE code_point SET is_alphabetic = 1, is_uppercase = 1 WHERE id = ?", (i,))

        with open(os.path.join(self._resource_path, 'graphical_exceptions.txt'), 'r') as file:
            for line in file:
                for i in self._unicode_range(line):
                    cursor.execute("""
                        UPDATE code_point 
                        SET is_independently_graphical = NOT is_independently_graphical
                        WHERE id = ?""", (i,))


    def _load_code_point_data(self, cursor):
        self._load_code_point_data_basics(cursor)      # populates code points from the unicode scripts file (so the self-referential FKs will work on main run)
        self._load_code_point_data_main(cursor)
        self._load_code_point_data_exceptions(cursor)  # derived properties and the like to override main defaults


    def _load_lookups(self, cursor):
        def load_lookup(cursor, table_name, lookup_data):
            cursor.executemany(
                f"INSERT INTO {table_name} (id, name, description)" + """
                VALUES (?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET name = ?, description = ?""",
                [(lu[0], lu[1], lu[2], lu[1], lu[2]) for lu in lookup_data])

        data = [
            (DerivationType.DEFAULT.value, "Derivation", "Standard/default/non-specific"),
            (DerivationType.PORTION_COPY.value,
                "Portion copy", "DEPRECATED. Use COPY or PORTION. Child is a copy of a portion of the parent, allowing for stretch-distortion due to size change"),
            (DerivationType.SIMPLIFICATION.value, "Simplification", "Child is a simplification of parent"),
            (DerivationType.FROM_CURSIVE.value, "From cursive", "Child is derived from cursive form of the parent (who is typically non-cursive)"),
            (DerivationType.COPY.value, "Copy", "Child is a copy (or multiple) of the parent"), # Usually child script copying or lowercase just a small version of uppercase
            (DerivationType.DUPLICATE.value, "Duplicate", "Child is a duplicate of the parent - Unicode canonical singleton"),  # Unicode duplicate code points
            (DerivationType.PORTION.value, "Portion derivation", "Child is a derivation from a portion of the parent"),
            (DerivationType.ROTATION.value, "Rotation", "Child is a rotation of the parent"),
            (DerivationType.REFLECTION.value, "Reflection", "Child is a reflection of the parent"),
            (DerivationType.TRANSLATION.value, "Translation", "Child is translation (position change) of the parent")]
        load_lookup(cursor, 'derivation_type', data)

        # For this project, sourcing is generally just for the derivation fact, not necessarily for derivation type
        # this lookup mostly expected to be complete. There may be additions if other derivation sources are found.
        data = [
            (Certainty.UNSPECIFIED.value, "Unspecified", "Not specified in data files"),
            (Certainty.NEAR_CERTAIN.value, "Near Certain", "Sources almost all agree, or disagreeing sources are suspect"),
            (Certainty.LIKELY.value, "Likely", "Sources mostly agree, or a singular weak source"),
            # For the purposes of this project, Wikipedia does not automatically count as a weak: it usually cites other sources
            (Certainty.UNCERTAIN.value, "Uncertain", "Sources disagree or are hesitant"),
            # TODO - Previous assumption field bifurcated into two, with id conservatively retained for Weak. Review manual files to bump some to strong.
            (Certainty.STRONG_ASSUMPTION.value, "Strong Assumption", "Derivation assumed, generally by strong glyph and sound value similarity"),
            (Certainty.WEAK_ASSUMPTION.value, "Weak Assumption", "Derivation assumed, usually by sound value and/or glyph similarity"),
            (Certainty.VARIED.value, "Variable", "Generally an automated derivation where individual certainty cannot be automatically determined"),
        ]
        load_lookup(cursor, 'certainty_type', data)

        data = [
            (SequenceType.BASE.value, 'Base', 'A "Sequence" representing a single code point. Does not contain items.'),
            (SequenceType.GENERAL.value, 'General', 'A general sequence'),
            (SequenceType.LETTER.value, 'Letter', 'A sequence of code points representing a letter'),
            (SequenceType.SIMPLE_ALPHABET.value, 'Simple Alphabet', 'A sequence consisting only of letters and code points'),

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

            (SequenceType.POSITION_DISTINCTION.value, "Positional Distinction",
             "Unit sequence representing the same glyph, but in a differing position and not already a Unicode decomposition"),

            (SequenceType.Z_VARIANT.value, 'Z-Variant', 'Unit sequence representing an equivalent or typographical variant Chinese character'),
            (SequenceType.HIEROGLYPHIC_ALTERNATIVE.value, 'Hieroglyphic Alternative', 'Equivalent Hieroglyph sequence')
        ]
        load_lookup(cursor, 'sequence_type', data)

        data = [
            (AlphabetType.UNSPECIFIED.value, "Unspecified", "Ideally should not be used"),
            (AlphabetType.BASIC.value, "Basic", "The canonical, independent letters"),
            # eg. accents, depending on language
            (AlphabetType.FULL.value, "Full", "The canonical or independent letters along with accepted variants"),
            # basically, the CLDR main exemplar set
            (AlphabetType.EXTENDED.value, "Extended", "Full set of letter glyphs generally needed to write a language"),
            # basically, the CLDR main exemplar plus auxiliary exemplar set (which we currently do not load)
            # (AlphabetType.AUXILIARY.value, "Auxiliary", "Full set of letter glyphs needed to write a language along with expected foreign borrowings"),
            # at some point there's also the question of whether non-letter symbols should be included
        ]
        load_lookup(cursor, 'alphabet_type', data)

        data = [
            (ScriptType.UNKNOWN.value, "Unknown", "Unknown / Missing data"),
            (ScriptType.NOT_APPLICABLE.value, "Not Applicable", "Non-script code"),
            (ScriptType.MIXED.value, "Mixed", "Mixed script code"),
            (ScriptType.ALPHABET.value, "Alphabet", "True alphabet - vowels are on par with consonants"),
            (ScriptType.ABUGIDA.value, "Abugida", "Vowels are secondary to consonants (usually diacritics)"),
            (ScriptType.ABJAD.value, "Abjad", "Vowels are optional or non-existent"),
            (ScriptType.SYLLABARY.value, "Syllabary", "Each syllable is a generally distinct glyph"),
            (ScriptType.LOGOGRAPH.value, "Logograph", "Each word is a generally distinct glyph"),
        ]
        load_lookup(cursor, 'script_type', data)

        data = [
            (self.MANUAL_PROCESS_ID, "Manually specified", "Manually specified in database source files"),
            (self.DECOMPOSITION_PROCESS_ID, "Unicode decomposition", "Technical derivation based on Unicode decomposition"),
        ]
        load_lookup(cursor, 'process_type', data)


    def create_process_type(self, name, description, sources=None, notes=None):
        cursor = self._cxn.cursor()
        id = cursor.execute("INSERT INTO process_type (name, description, notes) VALUES (?,?,?) RETURNING id", (name, description, notes)).fetchone()[0]
        self._load_table_sources(cursor, sources, 'process', ['process_type_id'], [id])
        cursor.close()
        return id


    def _load_equivalent_unit_sequence(self, cursor, seq_type, principal_id, equivalent_id):
        seq_id = self._create_sequence(cursor, seq_type)
        cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?, ?, ?)", (seq_id, principal_id, 1))
        cursor.execute("UPDATE code_point SET equivalent_sequence_id = ? WHERE id = ?", (seq_id, equivalent_id))

    # key_names & key_values are parallel lists
    def _load_table_sources(self, cursor, sources, table_name_prefix, key_names, key_values):
        if len(key_names) != len(key_values):
            raise ValueError("Bad programmer")
        if sources:
            for source in sources:
                parameters = [self._get_or_create_source_id(cursor, source.citation_key), source.section, source.access_date]
                parameters.extend(key_values)
                cursor.execute(f"INSERT INTO {table_name_prefix}_source (source_id, section, access_date, {','.join(key_names)}) VALUES (?,?,?{',?'*len(key_values)})",
                               parameters)


    def _load_single_manual_derivation(self, cursor, child_id, parent_id, derivation_type, certainty_type, sources, notes, multiplicity=1):
        cursor.execute("""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, process_type_id, notes, multiplicity) 
            VALUES (?,?,?,?,?,?,?)""", (child_id, parent_id, derivation_type.value, certainty_type.value, self.MANUAL_PROCESS_ID, notes, multiplicity))
        self._load_table_sources(cursor, sources, 'manual_derivation', ['child_id', 'parent_id'], [child_id, parent_id])


    # TODO - undecided if processes will ever specify separate notes to separate derivations
    def _load_single_derivation(self, cursor, child_id, parent_id, derivation_type, certainty_type, process_type_id, multiplicity=1):
        cursor.execute("""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, process_type_id, multiplicity) 
            VALUES (?,?,?,?,?,?)""",        (child_id, parent_id, derivation_type.value, certainty_type.value, process_type_id, multiplicity))


    def _load_arabic_derivations(self, cursor, verify):
        process_id = self.create_process_type('Arabic Unicode name',
                                              'Derivation of Arabic code points based on Unicode name',
                                              [SourceInfo('UCD', 'UnicodeData.txt name property')])
        arabic_map = {'ALEF': 1575, 'BEH': 1576, 'TEH': 1578, 'JEEM': 1580, 'HAH': 1581, 'DAL': 1583, 'REH': 1585, 'ZAIN': 1586,
                      'SEEN': 1587, 'SHEEN': 1588, 'SAD': 1589, 'DAD': 1590, 'TAH': 1591, 'AIN': 1593, 'GHAIN': 1594, 'FEH': 1601,
                      'QAF': 1602, 'KAF': 1603, 'LAM': 1604, 'MEEM': 1605, 'NOON': 1606, 'HEH': 1607, 'WAW': 1608, 'YEH': 1610, 'FATHA': 1614, 'KASRA': 1616,
                      'TTEH': 1657, 'PEH': 1662, 'TCHEH': 1670, 'KEHEH': 1705, 'GAF': 1711, 'FARSI YEH': 1740, 'YEH BARREE': 1746, 'AFRICAN QAF': 2236,
                      'EXTENDED ARABIC-INDIC DIGIT TWO': 1778, 'EXTENDED ARABIC-INDIC DIGIT THREE': 1779, 'EXTENDED ARABIC-INDIC DIGIT FOUR': 1780}
        arabic_note_text = "Based on Unicode name"

        def try_arabic_text_load_deriv(cursor, child_id, search_name, text):
            if " " + search_name in text:
                self._load_single_derivation(cursor, child_id, arabic_map[search_name], DerivationType.DEFAULT, Certainty.STRONG_ASSUMPTION, process_id)
                return True
            return False

        arabic_pattern = re.compile("ARABIC LETTER ([- A-Z]+?) WITH([- A-Z]+)")

        arabic_letters = cursor.execute("""
                    SELECT id, raw_name FROM code_point 
                    WHERE script_code = 'Arab' AND general_category_code = 'Lo' AND equivalent_sequence_id IS NULL""").fetchall()

        for arabic_letter in arabic_letters:
            match = arabic_pattern.match(arabic_letter[1])
            if match:
                child_id = int(arabic_letter[0])
                self._load_single_derivation(cursor, child_id, arabic_map[match.group(1)], DerivationType.DEFAULT, Certainty.STRONG_ASSUMPTION, process_id)

                with_text = match.group(2)
                found_other = False
                if "HAMZA" in with_text:
                    found_other = True
                    if "WAVY" in with_text:
                        # This ID is for wavy hamza below - there doesn't appear to be an above or standalone
                        self._load_single_derivation(cursor, child_id, 1631, DerivationType.DEFAULT, Certainty.STRONG_ASSUMPTION, process_id)
                    else:
                        hamza_id = 1621 if "HAMZA BELOW" in with_text else 1620
                        self._load_single_derivation(cursor, child_id, hamza_id, DerivationType.DEFAULT, Certainty.STRONG_ASSUMPTION, process_id)

                found_other = try_arabic_text_load_deriv(cursor, child_id, "KASRA", with_text) or found_other
                found_other = try_arabic_text_load_deriv(cursor, child_id, "FATHA", with_text) or found_other
                found_other = try_arabic_text_load_deriv(cursor, child_id, "MEEM", with_text) or found_other
                found_other = try_arabic_text_load_deriv(cursor, child_id, "NOON", with_text) or found_other
                found_other = try_arabic_text_load_deriv(cursor, child_id, "TAH", with_text) or found_other
                found_other = try_arabic_text_load_deriv(cursor, child_id, "EXTENDED ARABIC-INDIC DIGIT TWO", with_text) or found_other
                found_other = try_arabic_text_load_deriv(cursor, child_id, "EXTENDED ARABIC-INDIC DIGIT THREE", with_text) or found_other
                found_other = try_arabic_text_load_deriv(cursor, child_id, "EXTENDED ARABIC-INDIC DIGIT FOUR", with_text) or found_other
                # in theory this kind of clause should also apply to the others, but the data doesn't have it so don't want to overcomplicate
                if match.group(1) == "TEH" and "TEH" in with_text:
                    cursor.execute("UPDATE code_point_derivation SET multiplicity = ? WHERE child_id = ? AND parent_id = ?", (2, child_id, arabic_map["TEH"]))
                else:
                    found_other = try_arabic_text_load_deriv(cursor, child_id, "TEH", with_text) or found_other

                if "DOT" in with_text or "STROKE" in with_text or "BAR" in with_text or "RING" in with_text:
                    # TODO skip these for now, but maybe some could be derived from diacritics?
                    found_other = True
                if "SMALL V" in with_text or "INVERTED V" in with_text or "LOOP" in with_text or "TAIL" in with_text or "TEH" in with_text:
                    # These ones don't really have a code point to target (or in TEH's case is already targeted)
                    found_other = True

                if not found_other and verify:
                    print("Did not fully derive Arabic letter: " + arabic_letter[1])


    def _load_geez_derivations(self, cursor):
        process_id = self.create_process_type("Ge'ez Unicode name",
                                              "Derivation of Ge'ez code points by identifying the inherent vowel parent based on Unicode name",
                                              [SourceInfo('UCD', 'UnicodeData.txt name property'),
                                               SourceInfo('Wikipedia: Geʽez script', 'Geʽez_abugida')])
        base_pattern = re.compile('^(ETHIOPIC SYLLABLE (?:[A-Z]+ )?[^ AEIOU]*)([AEIOU]+)$')
        ethiopic = cursor.execute("SELECT id, raw_name FROM code_point WHERE script_code = 'Ethi' AND raw_name LIKE 'ETHIOPIC SYLLABLE%'").fetchall()
        base_ethiopic_names = {}
        for x in ethiopic:
            match = base_pattern.match(x[1])
            if match.group(2) == 'A':
                base_ethiopic_names[match.group(1)] = x[0]
        for x in ethiopic:
            match = base_pattern.match(x[1])
            if match.group(2) != 'A' and match.group(1) in base_ethiopic_names:
                self._load_single_derivation(cursor, x[0], base_ethiopic_names[match.group(1)], DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, process_id)


    def _load_sogdian_derivations(self, cursor):
        process_id = self.create_process_type('Sogdian Unicode name',
                                              'Derivation of Sogdian code points based on matching Old Sogdian Unicode names',
                                              [SourceInfo('UCD', 'UnicodeData.txt name property')])
        # This ones ~20 characters, should just manually specify at some point
        cursor.execute("""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, process_type_id)
            SELECT newsog.id, oldsog.id, ?, ?, ?
            FROM 
                code_point newsog 
                INNER JOIN code_point oldsog ON newsog.raw_name = substr(oldsog.raw_name, 5)
                WHERE newsog.script_code = 'Sogd' AND oldsog.script_code = 'Sogo'""",
            (DerivationType.DEFAULT.value, Certainty.STRONG_ASSUMPTION.value, process_id))


    def _load_latin_derivations(self, cursor):
        process_id = self.create_process_type('Latin Unicode name',
                                              'Derivation of Latin code points based on Unicode name',
                                              [SourceInfo('UCD', 'UnicodeData.txt name property')])
        latin_pattern = re.compile(r'([A-Z]{2,} )?([A-Z])( [A-Z]{2,}[ A-Z]*)?')
        capitals = cursor.execute("""
                    SELECT id, substr(raw_name, 22) FROM code_point 
                    WHERE 
                        script_code = 'Latn' 
                        AND general_category_code = 'Lu' 
                        AND raw_name LIKE 'LATIN CAPITAL LETTER%'
                        AND equivalent_sequence_id IS NULL""").fetchall()
        for capital in capitals:
            match = latin_pattern.match(capital[1])
            if match and (match.group(1) or match.group(3)):  # needs to match one of these groups or it's the base letter itself
                self._load_single_derivation(cursor, capital[0], ord(match.group(2)), DerivationType.DEFAULT, Certainty.STRONG_ASSUMPTION, process_id)

        lowercases = cursor.execute("""
                    SELECT id, substr(name, 20) FROM code_point 
                    WHERE 
                        script_code = 'Latn' 
                        AND general_category_code = 'Ll' 
                        AND raw_name LIKE 'LATIN SMALL LETTER%'
                        AND simple_uppercase_mapping_id IS NULL
                        AND equivalent_sequence_id IS NULL""").fetchall()
        for lowercase in lowercases:
            match = latin_pattern.match(lowercase[1])
            if match and (match.group(1) or match.group(3)):  # needs to match one of these groups or it's the base letter itself
                self._load_single_derivation(cursor, lowercase[0], ord(match.group(2).lower()), DerivationType.DEFAULT, Certainty.STRONG_ASSUMPTION, process_id)


    def _load_equivalents_from_names(self, cursor):
        # a few graphical equivalents
        equivalent_ids = cursor.execute("""
                    SELECT sym.id, mark.id AS equivalent_id 
                    FROM code_point sym INNER JOIN code_point mark ON substr(mark.name, 11) = sym.name
                    WHERE
                        mark.general_category_code = 'Mn' 
                        AND sym.general_category_code LIKE 'S_' 
                        AND mark.raw_name LIKE 'COMBINING%'
                        AND sym.equivalent_sequence_id IS NULL
                    """).fetchall()
        # most of the rest seem to be combining letters / digits where that would be the canonical character
        equivalent_ids.extend(cursor.execute("""
                    SELECT mark.id, other.id AS equivalent_id 
                    FROM code_point other INNER JOIN code_point mark ON substr(mark.name, 11) = other.name
                    WHERE
                        mark.general_category_code = 'Mn' 
                        AND other.general_category_code NOT LIKE 'S_' 
                        AND mark.raw_name LIKE 'COMBINING%'
                        AND mark.equivalent_sequence_id IS NULL
                    """).fetchall())
        # Hangul final->initial positional distinction
        equivalent_ids.extend(cursor.execute("""
                    SELECT finals.id, initials.id AS equivalent_id
                    FROM code_point finals INNER JOIN code_point initials ON substr(finals.name, 18) = substr(initials.name, 17)
                    WHERE 
                        finals.script_code = 'Hang'
                        AND initials.script_code = 'Hang'
                        AND finals.raw_name LIKE 'HANGUL JONGSEONG%'
                        AND initials.raw_name LIKE 'HANGUL CHOSEONG%'
                        AND finals.equivalent_sequence_id IS NULL
                    """).fetchall())
        # modifier letters which are different from combining characters... (Unicode Standard 7.8)
        # Could be added here, but seems not worth it based on quantity and difficulty in doing so in performant manner, just manually specify

        for equivalency in equivalent_ids:
            self._load_equivalent_unit_sequence(cursor, SequenceType.POSITION_DISTINCTION, equivalency[1], equivalency[0])


    def _load_data_from_names(self, cursor, verify=False):
        self._load_equivalents_from_names(cursor)

        # add derivations based on name
        # may later name as *_from_name if necessary to distinguish from other automatic processes
        # a lot of these will use the strong assumption certainty due to the names implying straightforward glyph relationships
        self._load_geez_derivations(cursor)
        self._load_sogdian_derivations(cursor)
        self._load_latin_derivations(cursor)
        self._load_arabic_derivations(cursor, verify)
        self._load_cuneiform_derivations(cursor)

        # set of ids to exclude from the independent derivations
        exception_ids = set()
        # Anatolian hieroglyphs tag format is mostly A[0-9]{3}[A-Z]?, so checking for longer than 4 for what turns out to likely be script-internal variants
        cursor.execute("""
            SELECT id FROM code_point cp INNER JOIN name_indexer ni ON cp.id = ni.code_point_id 
            WHERE cp.script_code = ? AND order_num = ? AND LENGTH(word) > ?""", ('Hluw', 3, 4))
        for id in cursor:
            exception_ids.add(id[0])
        return exception_ids


    def _load_independent_derivations(self, cursor):
        process_notes = 'General assumption for independent scripts, could be incorrect due to script-internal derivations (mitigated for some scripts).'
        process_notes += 'Additionally by convention, this database treats independent derivations as low certainty unless overwhelming evidence exists otherwise.'
        process_id = self.create_process_type('Independent scripts - general', 'Set characters from independent scripts to independently derived', notes=process_notes)

        # Mende Kikakui is a bit of an exception here: Unicode Encoding Proposal suggests Vai-derived characters are a small minority
        # Not including Chinese here: ideally will eventually do so for Oracle bone. Similar for modern Yi vs classical Yi
        results = cursor.execute("SELECT code FROM script WHERE parent_code = ?", (self.UNKNOWN_SCRIPT,)).fetchall()
        independent_scripts = [x[0] for x in results if x[0] not in self._EXCLUDED_GEN_CODES]

        cursor.execute(f"""
            INSERT INTO code_point_derivation (child_id, parent_id, certainty_type_id, process_type_id)
            SELECT id, ?, ?, ?
            FROM code_point 
            WHERE 
                script_code IN {self._get_sql_in_str_list(independent_scripts)}
                AND id NOT IN (SELECT child_id FROM code_point_derivation)""",
               (ord(self.NO_PARENT_CHARACTER), Certainty.WEAK_ASSUMPTION.value, process_id))


    def _load_from_unikemet(self, cursor, verify):
        process_note = 'This process reads Hieroglyph references in text descriptions. This can result in derivation chains being inaccurately portrayed if only base'
        process_note += ' Hieroglyphs are mentioned. Eg. a derivation chain for hieroglyph C such as (A->B; B->C) could render as (A->C; B->C) depending on the descriptions.'
        process_sources = [SourceInfo('Ritner 1996'), SourceInfo('UCD', 'Unikemet.txt kEH_Desc property')]
        process_id = self.create_process_type('Compound Egyptian Hieroglyphs',
                                              'Hieroglyph ligatures composed from base hieroglyphs',
                                              process_sources,
                                              process_note)
        code_dict = dict()
        code_parents = dict()
        code_pattern = '(?:HJ )?[A-Z][A-Za-z]?[0-9]{1,3}[A-Z]?|US[0-9][0-9A-Z]{4}[A-Z]+'  # not entirely sure where the US format codes come from; empirical format matching
        code_regex = re.compile(code_pattern)
        alph_id = self._create_sequence(cursor, SequenceType.SIMPLE_ALPHABET)
        alph_order = 1
        conflict_codes = set()
        with open(os.path.join(self._unicode_path, 'Unikemet.txt'), 'r') as file:
            for row in csv.reader(filter(lambda r: not r.isspace() and not r.startswith('#'), file), delimiter = '\t'):
                id = int(row[0][2:], 16)  # the [2:] slices off the U+
                if row[1] == 'kEH_AltSeq':
                    seq_id = self._create_sequence(cursor, SequenceType.HIEROGLYPHIC_ALTERNATIVE)
                    child_id = id
                    cursor.execute("UPDATE code_point SET equivalent_sequence_id = ? WHERE id = ?", (seq_id, child_id))
                    offset = 1
                    for i, code_point in enumerate(row[2].strip().split(' ')):
                        if code_point.isspace():
                            offset -= 1  # out of caution, but this seems to be an end-of-line issue
                        else:
                            cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?, ?, ?)", (seq_id, int(code_point, 16), i + offset))
                elif row[1] == 'kEH_Core':
                    if row[2].strip() == 'C':  # core
                        cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?,?,?)", (alph_id, id, alph_order))
                        alph_order += 1
                elif row[1] in ('kEH_JSesh', 'kEH_UniK', 'kEH_HG'): # various identifier codes
                    code = row[2]
                    if verify and not code_regex.match(code):
                        print('Unexpected format for Egyptian hieroglyph code: ' + code)
                    if code in code_dict and code_dict[code] != id:
                        conflict_codes.add(code)
                        if verify:
                            print(f'Egyptian hieroglyph code conflict: {code} maps to int ids {id} and {code_dict[code]}')
                    code_dict[code] = int(row[0][2:], 16)
                elif row[1] == 'kEH_Desc':
                    parent_codes = re.findall(code_pattern, row[2])
                    if parent_codes:
                        unique_parent_codes = set(parent_codes)
                        if verify and len(parent_codes) != len(unique_parent_codes):
                            # can't automatically determine if it's an actual multiple derivation of same parent or its just referencing a single figure twice
                            print(f'Parent of potential multiple multiplicity for hieroglyph int id: {id}')
                        code_parents[id] = unique_parent_codes

        self._insert_alphabet(cursor, alph_id, 'egy', 'Egyp', 'Lo', AlphabetType.EXTENDED, SourceInfo('UCD', 'Unikemet.txt kEH_Core property'))

        for code in conflict_codes:
            del code_dict[code]

        # mark ids where there was a parent, but we just weren't able to find them (very sad)
        orphaned_ids = set()
        for id in code_parents:
            for parent in code_parents[id]:
                if parent in code_dict:
                    self._load_single_derivation(cursor, id, code_dict[parent], DerivationType.DEFAULT, Certainty.LIKELY, process_id)
                    # likely certainty due to that chain thing: We're at least correctly getting the base hieroglyph
                else:
                    orphaned_ids.add(id)
                    if verify and parent not in conflict_codes: # no need to double error a code
                        print(f"Unknown referenced code {parent} on int id {id}")

        return orphaned_ids


    def _load_from_unihan(self, cursor):
        process_id = self.create_process_type('Simplified Chinese',
                                              'Derivation of Simplified Chinese code points from their corresponding Traditional Chinese code points',
                                              [SourceInfo('UCD', 'Unihan.zip/Unihan_Variants.txt kTraditionalVariant property')])
        with open(os.path.join(self._unicode_path, 'Unihan_Variants.txt'), 'r') as file:
            for row in csv.reader(filter(lambda r: not r.isspace() and not r.startswith('#'), file), delimiter = '\t'):

                if row[1] == 'kTraditionalVariant':  # mirror property is kSimplifiedVariant - should only need to check one
                    for parent_code in row[2].strip().split(' '):
                        if row[0] != parent_code:  # it's possible for a simplified character to map to itself
                            self._load_single_derivation(cursor, int(row[0][2:], 16), int(parent_code[2:], 16),
                                                         DerivationType.SIMPLIFICATION, Certainty.VARIED, # tentative certainty, I'm not expert enough to evaluate this
                                                         process_id)

                # This is a self-mirror property. if X zVariant Y then Y zVariant X.
                # There's no real indication which should be canonical that I can find, so I'm arbitrarily making it the lowest code point
                elif row[1] == 'kZVariant':
                    principal_id = int(row[0][2:], 16)
                    for parts in row[2].strip().split(' '):
                        other_id = int(parts[2:].split('<')[0], 16)
                        if principal_id > other_id:  #TODO i definitely mixed up the naming here, but this one makes my brain hurt trying to fix it
                            self._load_equivalent_unit_sequence(cursor, SequenceType.Z_VARIANT, other_id, principal_id)


    def _load_derivations_from_equivalencies(self, cursor):
        process_note = 'This is a technical derivation rather than a historical one. Rarely, it is possible that the derivation goes in the wrong historical direction.'
        cursor.execute("UPDATE process_type SET notes = ? WHERE id = ?", (process_note, self.DECOMPOSITION_PROCESS_ID))
        cursor.execute("INSERT INTO process_source (process_type_id, source_id, section) VALUES (?, ?, ?)",
                       (self.DECOMPOSITION_PROCESS_ID, self._get_or_create_source_id(cursor, 'UCD'), 'UnicodeData.txt decomposition property'))
        position_process_id = self.create_process_type("Equivalencies from name",
                                                       "Derivations based on equivalencies inferred from Unicode name",
                                                       [SourceInfo('UCD', 'UnicodeData.txt name property')])

        # add derivations from equivalent sequences, assuming the equivalent characters are the base building blocks (the parent)
        # Formatting/control/space characters are not eligible (they aren't graphical, right? ... right???)
        cursor.execute(f"""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, process_type_id)
            SELECT
                cp1.id,
                cp2.id,
                CASE WHEN COUNT(item_id) OVER (PARTITION BY equiv.sequence_id) = 1
                    THEN CASE WHEN seq.type_id = {SequenceType.CANONICAL_DECOMPOSITION.value} THEN {DerivationType.DUPLICATE.value}
                              WHEN seq.type_id IN ({SequenceType.POSITION_DISTINCTION.value},
                                                   {SequenceType.NO_BREAK_DECOMPOSITION.value},
                                                   {SequenceType.SUPER_DECOMPOSITION.value}, 
                                                   {SequenceType.SUB_DECOMPOSITION.value}, 
                                                   {SequenceType.SMALL_DECOMPOSITION.value}) THEN {DerivationType.TRANSLATION.value}
                              ELSE {DerivationType.DEFAULT.value}
                         END
                    ELSE {DerivationType.DEFAULT.value}
                END,
                CASE WHEN seq.type_id = {SequenceType.POSITION_DISTINCTION.value} THEN {Certainty.STRONG_ASSUMPTION.value}
                     ELSE {Certainty.NEAR_CERTAIN.value}
                END,
                CASE WHEN seq.type_id = {SequenceType.POSITION_DISTINCTION.value} THEN {position_process_id}
                     ELSE {self.DECOMPOSITION_PROCESS_ID}
                END
            FROM
                sequence_item equiv
                INNER JOIN sequence seq ON seq.id = equiv.sequence_id
                INNER JOIN code_point cp1 ON cp1.equivalent_sequence_id = seq.id
                INNER JOIN code_point cp2 ON cp2.id = equiv.item_id
            WHERE
                seq.type_id >= 100
                AND cp1.is_independently_graphical
                AND cp2.is_independently_graphical
            ON CONFLICT DO NOTHING""")
        # seq.type_id >= 100 is a bit hacky for now, I've basically put the equivalency sequence types at IDs 100+
        # A more "proper" solution would be to have a category associated to a sequence_type, but that feels like over-engineering for the moment
        # conflicts are expected when a character decomposes into multiple copies of a code point,
        # minimal enough that ON CONFLICT DO NOTHING is probably the better query option than advance filtering
        # About 10 conflicts are characters simultaneously being Z-variants and trad/simp derivations

        # manual equivalency
        # TODO - add verification for not overriding decomposition and maybe other manuals overriding this
        with open(os.path.join(self._resource_path, 'position_distinction.csv')) as csvfile:
            for row in csv.DictReader(csvfile):
                self._load_equivalent_unit_sequence(cursor, SequenceType.POSITION_DISTINCTION, ord(row["Equiv"]), ord(row["Char"]))
                self._load_single_manual_derivation(cursor, ord(row["Char"]), ord(row["Equiv"]),
                                                    DerivationType.TRANSLATION, Certainty.STRONG_ASSUMPTION, None, "Based in part on Unicode name")


    def _load_derivations_from_case_data(self, cursor, drop_case_columns=False):
        process_id = self.create_process_type('Case',
                                              'General assumption that the lowercase form derives from the uppercase',
                                              [SourceInfo('UCD', 'UnicodeData.txt simple upper/lower case mapping property')])
        # add derivations from case mapping, assuming lowercase to be derived from uppercase
        cursor.execute("""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, process_type_id)
            SELECT id, simple_uppercase_mapping_id, ?, ?, ?
            FROM code_point
            WHERE simple_uppercase_mapping_id IS NOT NULL""",
               (DerivationType.DEFAULT.value, Certainty.STRONG_ASSUMPTION.value, process_id))

        # casing isn't 100% 1:1 so need to do mappings in both directions
        cursor.execute("""
            INSERT INTO code_point_derivation (child_id, parent_id, derivation_type_id, certainty_type_id, process_type_id)
            SELECT simple_lowercase_mapping_id, id, ?, ?, ?
            FROM code_point cp1
            WHERE id <> (SELECT simple_uppercase_mapping_id FROM code_point cp2 WHERE cp2.id = cp1.simple_lowercase_mapping_id)""",
               (DerivationType.DEFAULT.value, Certainty.STRONG_ASSUMPTION.value, process_id))

        if drop_case_columns:
            cursor.execute("DROP INDEX idx_fk_cp_simple_uppercase_mapping")
            cursor.execute("ALTER TABLE code_point DROP COLUMN simple_uppercase_mapping_id")
            cursor.execute("DROP INDEX idx_fk_cp_simple_lowercase_mapping")
            cursor.execute("ALTER TABLE code_point DROP COLUMN simple_lowercase_mapping_id")
            cursor.execute("ALTER TABLE code_point DROP COLUMN is_lowercase")
            cursor.execute("ALTER TABLE code_point DROP COLUMN is_uppercase")


    def _parse_raw_source(self, cursor, raw_source_str):
        # the format wasn't really planned in advance
        parts = raw_source_str.split(' - ')
        access_date = int(cursor.execute("SELECT JULIANDAY(?)", (parts[1].strip(),)).fetchone()[0]) if len(parts) > 1 else None

        parts = parts[0].split('#')
        section = parts[1].strip() if len(parts) > 1 else None

        return SourceInfo(parts[0].strip(), section, access_date)


    def _load_manually_specified_derivations(self, cursor, verify_script):
        def resolve_default(defaults_dict, script, data_row, field, overriding_default=None, override_condition=False, last_resort=None):
            if field in data_row and data_row[field] and not data_row[field].isspace():
                return data_row[field].strip()
            if override_condition:
                return overriding_default
            if script in defaults_dict and field in defaults_dict[script] and defaults_dict[script][field]:
                return defaults_dict[script][field]
            return last_resort

        defaults = {}
        with open(os.path.join(self._resource_path, 'derivation_defaults.csv'), 'r') as file:
            for row in csv.DictReader(file):
                defaults[row['Script'].strip()] = {
                    'Source': row['Source'].strip(),
                    'Derivation Type': row['Derivation Type'].strip(),
                    'Certainty Type': row['Certainty Type'].strip()
                }

        for s in os.listdir(self._derivations_path):
            script_file = os.path.join(self._derivations_path, s)
            script = script_file.split(os.path.sep)[-1].split('.')[0]
            with open(script_file, 'r') as file:
                for row in csv.DictReader(file):
                    child = row['Child'].strip()
                    parents = row['Parent'].strip()

                    # Logic for defaulting to Uncertain on no parent: For historical scripts, this is usually more a function of a lack of records
                    # For modern scripts, the inventor is generally aware of existing writing systems, and may have been inspired
                    certainty = int(resolve_default(defaults, script, row, 'Certainty Type',
                                                    overriding_default=str(Certainty.UNCERTAIN.value),
                                                    override_condition=(parents.isspace()),
                                                    last_resort=str(Certainty.UNSPECIFIED.value)))

                    multiplicity = int(resolve_default(defaults, script, row, 'Multiplicity', last_resort=1))

                    # Overriding default here is for convenience:
                    # An Assumed certainty means there is usually no source, so allows us to specify a source in defaults for all else.
                    raw_sources = resolve_default(defaults, script, row, 'Source', overriding_default=None,
                                             override_condition=(certainty in (Certainty.STRONG_ASSUMPTION.value, Certainty.WEAK_ASSUMPTION.value)))
                    sources = []
                    if raw_sources:
                        for raw_source in raw_sources.split('/'):
                            sources.append(self._parse_raw_source(cursor, raw_source))

                    notes = resolve_default(defaults, script, row, 'Notes')
                    derivation_type = int(resolve_default(defaults, script, row, 'Derivation Type', last_resort=str(DerivationType.DEFAULT.value)))

                    # File-specified data overrides the automatically generated data
                    # TODO - with the manual split, it should be easier to first delete from manual_derivation_source without relying on CASCADE
                    cursor.execute("DELETE FROM code_point_derivation WHERE child_id = ? AND process_type_id <> ?", (ord(child), self.MANUAL_PROCESS_ID))
                    # TODO: also reverse deletion for decomposition

                    # ensure that child character is always the expected script
                    if verify_script:
                        script_in_db = cursor.execute(
                            "SELECT code FROM code_point cp INNER JOIN script s ON s.code = cp.script_code WHERE text = ?", child).fetchone()[0]
                        if script != script_in_db:
                            print(f"resource file error in {script}.csv with child character {child} detected to be {script_in_db} instead")

                    for parent in parents.split('/'):
                        if not parent: parent = self.NO_PARENT_CHARACTER

                        if verify_script:
                            if child == parent:
                                raise ValueError("Attempted to add self-derivation of " + child)
                            if cursor.execute("SELECT * FROM code_point_derivation WHERE parent_id = ? AND child_id = ?",
                                              (ord(child), ord(parent))).fetchall():
                                raise ValueError("Attempted to add a 2-cycle with " + child + " and " + parent)

                        self._load_single_manual_derivation(cursor, ord(child), ord(parent), DerivationType(derivation_type),
                                                            Certainty(certainty), sources, notes, multiplicity)

        # stuff that's confusing or might break csv format (commas, quotes, slashes)
        awkward_data = [
            (ord('/'), ord(self.NO_PARENT_CHARACTER), DerivationType.DEFAULT, Certainty.LIKELY, 'OED 1933 # Volume 12 p. 235',
             'Derived from medieval virgule, essentially the same graphical symbol but used as a comma', 1),
            (ord('⸗'), ord('/'), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Slash', None, 2),
            (ord('\\'), ord(self.NO_PARENT_CHARACTER), DerivationType.DEFAULT, Certainty.UNCERTAIN, 'Wikipedia: Backslash', None, 1),
            (ord("'"), ord("’"), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Apostrophe', None, 1),
            (ord('"'), ord('“'), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Apostrophe / Wikipedia: Quotation Mark', None, 1),
            (ord('"'), ord('”'), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Apostrophe / Wikipedia: Quotation Mark', None, 1),
            (ord(','), ord('/'), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Comma', None, 1),
            (ord(';'), ord(','), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Semicolon', None, 1),
            (ord(';'), ord(':'), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Semicolon', None, 1),
            (ord('⅍'), ord('A'), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Aktieselskab', None, 1),
            (ord('⅍'), ord('/'), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Aktieselskab', None, 1),
            (ord('⅍'), ord('S'), DerivationType.DEFAULT, Certainty.NEAR_CERTAIN, 'Wikipedia: Aktieselskab', None, 1),
        ]

        for row in awkward_data:
            sources = [self._parse_raw_source(cursor, s) for s in row[4].split('/')]
            self._load_single_manual_derivation(cursor, row[0], row[1], row[2], row[3], sources, row[5], row[6])


    def _load_cuneiform_derivations(self, cursor):
        process_id = self.create_process_type('Cuneiform Unicode name',
                                              'Derivation of Cuneiform code points based on Unicode name',
                                              [SourceInfo('UCD', 'UnicodeData.txt name property'),
                                               SourceInfo('UTR 56'),
                                               SourceInfo('Cooper 1996')],
                                              'For atomic signs, Cuneiform has no known parent script (Proto-Cuneiform not in DB or Unicode yet)')
        # TODO - this one is more notes on certain derivations than notes on the process

        cursor.execute("""
            INSERT INTO code_point_derivation (child_id, parent_id, certainty_type_id, process_type_id)
            SELECT id, ?, ?, ? FROM code_point
            WHERE script_code = ? AND name LIKE ? AND word_count = ?""",
            (ord(self.NO_PARENT_CHARACTER), Certainty.UNCERTAIN.value, process_id, 'Xsux', 'CUNEIFORM SIGN%', 3))


    def _load_derivations(self, cursor, indic_supp_data, indic_letter_data, semitic_letter_data, load_options):
        supp_process_id = self.create_process_type('Supplementary Indic',
                                                   'Indic derivations inferred by Unicode name and known script ancestors',
                                                   [SourceInfo("UCD", "UnicodeData.txt name property")])
        indic_process_id = self.create_process_type('Indic letters',
                                                    'Indic derivations from cognate letters and known script ancestors',
                                                    [SourceInfo("Wikipedia: Indic letter pages")])
        semitic_process_id = self.create_process_type('Semitic letters',
                                                      'Semitic derivations from cognate letters and known script ancestors',
                                                      [SourceInfo("Wikipedia: Semitic letter pages")])
        exception_ids = self._load_data_from_names(cursor, load_options.verify_data_sources)
        # we want to drop this as soon as possible so that the freed space can be used
        if load_options.drop_code_point_name_index:
            cursor.execute("DROP TABLE name_indexer")
            cursor.execute("DROP INDEX idx_cp_raw_name")
            cursor.execute("ALTER TABLE code_point DROP COLUMN word_count")

        self._load_derivations_from_case_data(cursor, load_options.drop_case_columns)
        self._load_from_unihan(cursor)  # derivation and equivalency data
        exception_ids |= self._load_from_unikemet(cursor, load_options.verify_data_sources) # derivation, equivalency data and an alphabet
        self._load_derivations_from_equivalencies(cursor)
        self._load_independent_derivations(cursor) # after equivalency loading to allow that to take priority

        for id in exception_ids:
            cursor.execute("DELETE FROM code_point_derivation WHERE child_id = ? AND parent_id = ?", (id, ord(self.NO_PARENT_CHARACTER)))

        self._load_letter_derivation_data(cursor, indic_supp_data, self._INDIC_SUPPLEMENT, supp_process_id, load_options.verify_data_sources)
        self._load_letter_derivation_data(cursor, indic_letter_data, self._INDIC_ORDER, indic_process_id, load_options.verify_data_sources)
        self._load_letter_derivation_data(cursor, semitic_letter_data, self._SEMITIC_ORDER, semitic_process_id, load_options.verify_data_sources)

        # Currently, this is a field used for internal generation only, don't want it to be taken literally
        cursor.execute("DROP INDEX idx_fk_parent_script")
        cursor.execute("ALTER TABLE script DROP COLUMN parent_code")

        self._load_manually_specified_derivations(cursor, load_options.verify_data_sources)

        if load_options.drop_derivation_type:
            cursor.execute("ALTER TABLE code_point_derivation DROP COLUMN derivation_type_id")
            cursor.execute("DROP TABLE derivation_type")


    def get_code_to_script_dict(self):
        retval = {}
        cursor = self._cxn.cursor()
        results = cursor.execute("SELECT code, name FROM script WHERE name IS NOT NULL").fetchall()
        for row in results:
            retval[row[0]] = row[1]
        cursor.close()
        return retval


    def _get_indic_supplement_dict(self, cursor, indic_scripts):
        supp_data = {}
        for script_code in indic_scripts:
            supp_data[script_code] = {}
            for supp_name in self._INDIC_SUPPLEMENT:
                if not supp_name.startswith('PLACEHOLDER'):
                    query = "SELECT DISTINCT(text) FROM code_point cp "
                    supp_name_parts = supp_name.split(' ')
                    supp_name_length = len(supp_name_parts)
                    for i, supp_word in enumerate(supp_name_parts):
                        query += f" INNER JOIN name_indexer ni{i} ON ni{i}.code_point_id = cp.id AND ni{i}.word = '{supp_word}'"
                        query += f" AND ni{i}.order_num = cp.word_count - {supp_name_length - 1 - i}"
                    query += " WHERE script_code = ?"
                    supp_code_point = cursor.execute(query, (script_code,)).fetchall()

                    if len(supp_code_point) == 1:  # more than one is too risky for automatic derivation based on name
                        supp_data[script_code][supp_name] = [supp_code_point[0][0]]
        return supp_data


    def _load_private_use_data(self, cursor, indic_letter_data):
        script_names = self.get_code_to_script_dict()
        def get_private_use_indic_name(script_code, wiki_letter_name):
            script_name = script_names[script_code]
            replacements = {'Ā': 'AA', 'Ī': 'II', 'Ū': 'UU', 'Ṛ': 'vocalic R', 'Ṝ': 'vocalic RR', 'Ḷ': 'vocalic L', 'Ḹ': 'vocalic LL',
                            'Ṅa': 'Nga', 'Ña': 'Nya', 'Ṭa': 'Tta', 'Ṭha': 'Ttha', 'Ḍa': 'Dda', 'Ḍha': 'Ddha', 'Ṇa': 'Nna', 'Va': 'Wa', 'Śa': 'Sha', 'Ṣa': 'Ssa'}

            if wiki_letter_name in replacements:
                wiki_letter_name = replacements[wiki_letter_name]
            return (script_name + ' letter ' + wiki_letter_name).upper()
        def check_other_alphabetic(general_category_code, indic_char_class_name):
            return general_category_code[0] == 'M' and indic_char_class_name not in ['NUKTA', 'VIRAMA']
        def load_indic_manual(script_code, char_name):
            script_name = script_names[script_code]
            category_code = 'Mn' # rough
            if char_name == 'SIGN SIDDHAM':
                category_code = 'Po'
            elif  char_name.startswith('LETTER'):
                category_code = 'Lo'
            self._insert_code_point(cursor,
                                    self._CODE_POINT_STARTS[script_code] + len(self._INDIC_ORDER) + len(self._INDIC_SUPPLEMENT) + self._INDIC_MANUAL.index(char_name),
                                    f"{script_names[script_code].upper().replace("'", "")} {char_name}",
                                    script_code,
                                    category_code,
                                    bidi_class_code='NSM' if category_code == 'Mn' else 'L', # probably
                                    is_other_alphabetic = check_other_alphabetic(category_code, char_name))

        dem_replacements = {'š': 'sh', 'ẖ': 'x', 'ḥ': 'h-dot', 'ḥ2': 'h2-dot', 'ḏ': 'd-underbar', 'ḏ2': 'd2-underbar',
                            'ı͗': 'i-halfring', 'ꜥ': 'ain', 'ḫ': 'h-underbar', 'š2': 'sh2'}

        offset = len(self._INDIC_ORDER)
        for script_code in indic_letter_data:
            if script_code.startswith('Qab'):
                for letter_class in indic_letter_data[script_code]:
                    letter = indic_letter_data[script_code][letter_class][0] # generated only has one
                    self._insert_code_point(cursor, ord(letter), get_private_use_indic_name(script_code, letter_class), script_code, 'Lo', bidi_class_code = None)

                # we assume these symbols exist then filter manually later
                # the opposite approach seemed trickier (see the fill-in script stuff for the indic letters for that...)
                for i, supp_name in enumerate(self._INDIC_SUPPLEMENT):
                    if 'PLACEHOLDER' in supp_name:
                        continue

                    insert_code_point = True
                    category_code = 'Mn'
                    if supp_name == 'VISARGA':
                        category_code = 'Mc'
                    elif supp_name == 'CANDRABINDU' and script_code == 'Qabp':
                        insert_code_point = False
                    elif supp_name == 'NUKTA' and script_code == 'Qabp':
                        insert_code_point = False
                    elif supp_name == 'AVAGRAHA':
                        category_code = 'Lo'
                        if script_code in ('Qabp', 'Qabl'):
                            insert_code_point = False
                    elif supp_name in ['DANDA', 'DOUBLE DANDA']:
                        category_code = 'Po'
                        if script_code not in ('Qabp', 'Qabg'):
                            insert_code_point = False
                    elif supp_name.startswith('DIGIT'):
                        category_code = 'Nd'
                    elif supp_name.startswith('VOWEL'):
                        # turns out this could be a mess going forward
                        # eyeballing it for Mc vs Mn
                        if script_code == 'Qabg':
                            if supp_name == 'VOWEL SIGN UU':
                                category_code = 'Mc'
                            elif 'VOCALIC' in supp_name and supp_name != 'VOWEL SIGN VOCALIC R':
                                insert_code_point = False
                        elif script_code == 'Qabp':
                            if 'VOCALIC' in supp_name:
                                insert_code_point = False
                            elif 'SIGN I' in supp_name or 'SIGN U' in supp_name:  # intentionally including long vowels
                                category_code = 'Mc'
                        elif script_code == 'Qabl':
                            if 'VOCALIC' in supp_name:
                                insert_code_point = False
                            elif 'SIGN I' in supp_name or 'SIGN AA' in supp_name: # intentionally including long II
                                category_code = 'Mc'
                        elif script_code == 'Qabd':
                            if 'VOCALIC L' in supp_name: # intentionally including "long" L
                                insert_code_point = False
                            elif 'SIGN U' not in supp_name and 'VOCALIC R' not in supp_name: # intentional again
                                category_code = 'Mc'
                        elif script_code == 'Qabn':
                            if 'VOCALIC L' in supp_name: # intentionally including "long" L
                                insert_code_point = False
                            elif 'SIGN I' in supp_name or supp_name in ('VOWEL SIGN AA', 'VOWEL SIGN AI', 'VOWEL SIGN O', 'VOWEL SIGN AU'):
                                category_code = 'Mc'
                        elif script_code == 'Qabk':
                            if 'VOCALIC L' in supp_name: # intentionally including "long" L
                                insert_code_point = False
                            elif supp_name not in ('VOWEL SIGN I', 'VOWEL SIGN VOCALIC R', 'VOWEL SIGN E'):
                                category_code = 'Mc'

                    # Nagari removals based on less than 2/3 of Siddham, Devanagari, Nandiningari having it
                    # Gaudi removals based on less than 2/3 of Siddham, Bengali, Odia having it
                    # Landa removals based on less than 2/3 of Sharada, Khudabadi and Gurmukhi having it
                    # Landa Danda: While there are Danda code points for Sharada, they are lacking in Khudabadi and Gurmukhi.
                    # Intent seems to be to use generic Devanagari Danda: https://www.unicode.org/L2/L2020/20183-gurmukhi-chg.pdf and https://panjabilab.com/faq/

                    # Kadamba removals just based on 0 or 1 of Telugu and Kannada having it -
                    # The scripts are so closely related and the parent of Kadamba goes all the way back to Brahmi

                    # Good data on what to remove in Pallava: https://www.unicode.org/L2/L2018/18083-pallava.pdf

                    # dependent vowels for Gupta: https://en.wikipedia.org/wiki/Gupta_script - diacritics TODO

                    if insert_code_point:
                        self._insert_code_point(cursor,
                                                self._CODE_POINT_STARTS[script_code] + offset + i,
                                                f"{script_names[script_code].upper().replace("'", "")} {supp_name}",
                                                script_code,
                                                category_code,
                                                bidi_class_code = 'NSM' if category_code == 'Mn' else 'L',  # probably
                                                is_other_alphabetic = check_other_alphabetic(category_code, supp_name))

        load_indic_manual('Qabk', 'LETTER VOCALIC LL')
        load_indic_manual('Qabk', 'LETTER EE')
        load_indic_manual('Qabk', 'LETTER OO')
        load_indic_manual('Qabk', 'LETTER RRA')
        load_indic_manual('Qabk', 'LETTER LLA')
        load_indic_manual('Qabk', 'VOWEL SIGN EE')
        load_indic_manual('Qabk', 'VOWEL SIGN OO')
        load_indic_manual('Qabk', 'LENGTH MARK')
        load_indic_manual('Qabk', 'AI LENGTH MARK')
        load_indic_manual('Qabk', 'SIGN SIDDHAM')

        load_indic_manual('Qabp', 'LETTER LLA')
        load_indic_manual('Qabp', 'LETTER LLLA')
        load_indic_manual('Qabp', 'SIGN SIDDHAM')
        load_indic_manual('Qabg', 'SIGN SIDDHAM')
        load_indic_manual('Qabn', 'SIGN SIDDHAM')

        for i, letter in enumerate(self._PROTO_SINAITIC_ORDER):
            self._insert_code_point(cursor, i + self._CODE_POINT_STARTS['Psin'], f"PROTO-SINAITIC LETTER {letter}", "Psin", 'Lo', bidi_class_code=None)
            # TODO double check bidi class code

        for i, letter in enumerate(self._DEMOTIC_SUBSET):
            temp = letter.split(' ')[0]
            l = dem_replacements[temp] if temp in dem_replacements else temp
            self._insert_code_point(cursor, i + self._CODE_POINT_STARTS['Egyd'], f"EGYPTIAN DEMOTIC LETTER {l.upper()}", "Egyd", 'Lo', bidi_class_code=None)
            # TODO bidi class code is rtl

        for i, letter in enumerate(self._PITMAN_ORDER):
            self._insert_code_point(cursor, i + self._CODE_POINT_STARTS['Qaap'], f"PITMAN LETTER {letter}", "Qaap", 'Lo', bidi_class_code=None)
            # TODO - vowels might actually be marks

    # format: { script_code: { Generic Indic Letter: [letters] } }
    # TODO add script verification
    def _get_indic_letter_dict(self, cursor, verify):
        def add_private_use_char(data, script_code, indic_letter):
            id = self._CODE_POINT_STARTS[script_code] + self._INDIC_ORDER.index(indic_letter)
            data[script_code][indic_letter] = [chr(id)]

        wdata = {}
        hex_pattern = re.compile('^[0-9A-F]+$')
        replacements = {'Gupt': 'Qabg', 'Kdmb': 'Qabk', 'Plav': 'Qabp'}
        for letter in ScriptDatabase._INDIC_ORDER:
            with open(os.path.join(self._wikipedia_path, 'indic-letters', letter + '.txt'), 'r') as file:
                for match in re.findall(r'\|\s*([a-z0-9]+)(cp|img)\s*=([^\|]+)', file.read()):
                    script_code = match[0][0:4].title()  # a few have multiple codepoints indicated by appended numbers
                    if script_code in replacements:
                        script_code = replacements[script_code]

                    if script_code not in wdata:
                        wdata[script_code] = {}
                    if match[1] == 'img' and letter not in wdata[script_code]:
                        wdata[script_code][letter] = [] #mark the letter exists though we don't know the code point yet
                    elif match[1] == 'cp':  # code point exists for the script
                        value = match[2].strip()
                        if '&#x' in value:
                            value = value[value.index('x') + 1:]
                        if hex_pattern.match(value):  # there's one entry in Tibetan that has three codepoints and I don't understand the intention
                            letter_to_add = chr(int(value, 16))
                            if letter_to_add == 'ᜢ' and letter == 'O':
                                if verify:
                                    print("Data generation error: Hanunoo letter ᜢ in two Indic letter files")  # a likely error in the source files
                            else:
                                category_code = cursor.execute("SELECT general_category_code FROM code_point WHERE text = ?", (letter_to_add,)).fetchone()[0]
                                if category_code == 'Lo':  # only looking for independent vowels in this method (was otherwise inconsistent data it seemed)
                                    if letter not in wdata[script_code]:
                                        wdata[script_code][letter] = []
                                    if letter_to_add not in wdata[script_code][letter]:
                                        wdata[script_code][letter].append(letter_to_add)

        # kawi a bit of a special case in that it exists in Unicode, but probably because its one of the newer ones, Wikipedia source files didn't have code points yet
        # in unicode, currently all indic letters exist in Kawi except for vowel Au, so just manually made sure that one wasn't added by the code
        for indic_letter in self._INDIC_ORDER:
            add_private_use_char(wdata, 'Kawi', indic_letter)
        del wdata['Kawi']['Au']

        fill_in_scripts = ['Qabp', 'Qabk', 'Qabl', 'Qabn', 'Qabd', 'Qabg']
        # if it existed as an image in Wikipedia (it would have got created as an empty list) OR 50% + 1 have the Indic letter, we assume it exists
        # in hindsight, a simpler (but less accurate) approach would've been to just assumed all the letters existed and then manually remove the ones that don't
        for fill_in_script in fill_in_scripts:
            if fill_in_script not in wdata:
                wdata[fill_in_script] = {}
            for letter in self._INDIC_ORDER:
                fill_in_letter = False
                if letter in wdata[fill_in_script] and wdata[fill_in_script][letter] is not None:
                    fill_in_letter = (len(wdata[fill_in_script][letter]) == 0) # in theory letter could already have be there, so don't touch it
                else:
                    descendant_scripts = cursor.execute(f"SELECT code FROM script WHERE parent_code IN {self._get_sql_in_str_list(fill_in_scripts)}").fetchall()
                    count = 0
                    for descendant_script in descendant_scripts:
                        if letter in wdata[descendant_script[0]] and wdata[descendant_script[0]][letter]:
                            count += 1
                    if count >= len(descendant_scripts)/2 + 1:
                        fill_in_letter = True
                if fill_in_letter:
                    add_private_use_char(wdata, fill_in_script, letter)

        # Add ones that probably existed, but didn't meet the conservative automatic threshold

        # research from Sharada indicates straight development from Gupta, and maybe Siddham as well
        # https://www.scribd.com/document/443095526/%C5%9A%C4%81rad%C4%81-Primer (While Ai is blank in this source, related shape E shows the development)
        add_private_use_char(wdata, 'Qabg', 'Ai')

        # Based on https://en.wikipedia.org/wiki/Gupta_script
        add_private_use_char(wdata, 'Qabg', 'Ḹ')
        add_private_use_char(wdata, 'Qabg', 'Jha')

        # Based on all three of Sharada, Gurmukhi, Khudabadi having it (clearly Landa was too conservative...)
        add_private_use_char(wdata, 'Qabl', 'Ā')
        add_private_use_char(wdata, 'Qabl', 'Ī')
        add_private_use_char(wdata, 'Qabl', 'Ū')
        add_private_use_char(wdata, 'Qabl', 'Ai')
        add_private_use_char(wdata, 'Qabl', 'Au')
        add_private_use_char(wdata, 'Qabl', 'Jha')
        add_private_use_char(wdata, 'Qabl', 'Ṅa')
        add_private_use_char(wdata, 'Qabl', 'Ña')
        add_private_use_char(wdata, 'Qabl', 'Śa')


        del wdata['Armi']  # Remove aramaic, it's better in Semitic dictionary

        return wdata

    # format: { script_code: { Generic Semitic Letter: [letters] } }
    def _get_semitic_letter_dict(self):
        code_map = {
            'ar': 'Arab',
            'sy': 'Syrc',
            'he': 'Hebr',
            'sm': 'Samr',
            'am': 'Armi',
            'nb': 'Nbat',
            'ge': 'Ethi',
            'ug': 'Ugar',
            'ph': 'Phnx',
            'na': 'Narb',
            'sa': 'Sarb',
            'gr': 'Grek',
            'la': 'Latn',
            'cy': 'Cyrl',
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

        wdata['Psin'] = {}
        for letter in letter_map:
            wdata['Psin'][letter] = [chr(ScriptDatabase._PROTO_SINAITIC_ORDER.index(letter_map[letter]) + ScriptDatabase._CODE_POINT_STARTS['Psin'])]

        return wdata


    def _generate_std_alphabets(self, semitic_letter_dict, indic_letter_dict, indic_supp_dict):
        def generate_std_alphabet(letter_dict, source, letter_order):
            with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'a') as alpha_file:
                for script_code in letter_dict:
                    if script_code not in ScriptDatabase._EXCLUDED_GEN_CODES:
                        alpha_file.write('\n' + script_code + ',' + source + ',')
                        for letter_class in letter_order:
                            if letter_class in letter_dict[script_code]:
                                for letter in letter_dict[script_code][letter_class]:
                                    alpha_file.write(letter + ' ')

        with open(os.path.join(self._resource_path, ScriptDatabase._GENERATED_DIR_NAME, 'standard_alphabets.csv'), 'w') as file:
            file.write('Script,Source,Alphabet')

        indic_dict = dict(indic_letter_dict)
        for script_code in indic_supp_dict:
            for letter_class in indic_supp_dict[script_code]:
                indic_dict[script_code][letter_class] = indic_supp_dict[script_code][letter_class]

        indic_order = list(self._INDIC_ORDER)
        indic_order.extend(self._INDIC_SUPPLEMENT[self._INDIC_SUPPLEMENT.index('VOWEL SIGN AA'):])
        generate_std_alphabet(indic_dict, 'Wikipedia: Indic letter pages', indic_order)
        generate_std_alphabet(semitic_letter_dict, 'Wikipedia: Semitic letter pages', self._SEMITIC_ORDER)


    def _drop_unused_languages(self, cursor):
        cursor.execute("""
            DELETE FROM language
            WHERE 
                code NOT IN (SELECT lang_code FROM alphabet) 
                AND code NOT IN (  -- language is not a macro to a sublanguage that is used
                    SELECT macrolanguage_code FROM alphabet a INNER JOIN language lsub ON lsub.code = a.lang_code WHERE macrolanguage_code IS NOT NULL)""")


    def _load_letter_derivation_data(self, cursor, letter_dict, letter_order, process_type_id, verify):
        for script_code in letter_dict:
            if script_code not in ScriptDatabase._EXCLUDED_GEN_CODES:
                parent_code = cursor.execute("SELECT parent_code FROM script WHERE code = ?", (script_code,)).fetchone()[0]
                for letter_class in letter_order:
                    if letter_class in letter_dict[script_code] and letter_class in letter_dict[parent_code]:
                        parent_letters = letter_dict[parent_code][letter_class]  # final parent scripts should be in excluded codes
                        if len(parent_letters) == 1:
                            letters = letter_dict[script_code][letter_class]
                            if len(letters) == 1:  # previously allowed multiple, but this is too inaccurate
                                self._load_single_derivation(cursor, ord(letters[0]), ord(parent_letters[0]), DerivationType.DEFAULT, Certainty.VARIED, process_type_id)


    def _verify_script_coverage(self, cursor):
        results = [('Script', 'Missing characters')]

        def verify_seq(seq_id):
            missing_chars = self.execute_saved_query("Missing code points in sequence", parameters=(seq_id,), return_headers=False)
            if not missing_chars:
                return None # all characters have a derivation
            num_missing = len(missing_chars)
            if num_missing >= 20:
                return f"{num_missing} missing characters"
            return ", ".join([i[1] for i in missing_chars])

        scripts = cursor.execute("SELECT name, code FROM script WHERE code NOT IN (?, ?) AND (u_alias IS NOT NULL OR code like 'Q%') ORDER BY name",
                                 (self.COMMON_SCRIPT, self.INHERITED_SCRIPT)).fetchall()
        for script in scripts:
            sequence_id = self._get_exemplar_sequence_id_with_fallback(cursor, script[1])
            if sequence_id:
                script_result = verify_seq(sequence_id)
                if script_result:
                    results.append((script[0], script_result))
            else:
                results.append((script[0], 'No standard characters specified'))

            # Incomplete data not necessarily an error, we just output to audit it
        self.print_table(results)


    def _parse_cldr_exemplar_set(self, cursor, cldr_str, parse_data, verify):
        def add_char(p_data, char, in_multi_code_point, verify):
            # First, get info from DB about char if needed
            if verify or p_data.script_code is None or p_data.letter_case is None:
                cp_data = cursor.execute("SELECT general_category_code, script_code FROM code_point WHERE id = ?", (ord(char),)).fetchone()
                if verify:
                    if (cp_data[1] not in (self.COMMON_SCRIPT, self.INHERITED_SCRIPT)
                            and p_data.script_code is not None
                            and p_data.script_code not in (cp_data[1], 'Hans', 'Hant')):
                        print(f"Multiple script codes detected in alphabet. Expected script: {p_data.script_code}, encountered script: {cp_data[1]}")
                    if p_data.letter_case in ('Ll', 'Lu') and cp_data[0] in ('Ll', 'Lu') and cp_data[0] != p_data.letter_case:
                        print(f"Multiple cases detected in alphabet. Expected case: {p_data.letter_case}, encountered case: {cp_data[0]}")
                if p_data.letter_case is None and cp_data[0] in ('Ll', 'Lu'):
                    p_data.letter_case = cp_data[0]
                if p_data.script_code is None and cp_data[1] not in (self.COMMON_SCRIPT, self.INHERITED_SCRIPT):
                    p_data.script_code = cp_data[1]

            # There is a question about why we're using python's .upper() and .lower()
            if in_multi_code_point:
                p_data.letters[-1] += char
                if p_data.letter_case is None:
                    p_data.alternate_letters[-1] += char
                elif p_data.letter_case == 'Ll':
                    p_data.alternate_letters[-1] += char.upper()
                elif p_data.letter_case == 'Lu':
                    p_data.alternate_letters[-1] += char.lower()
            else:
                p_data.letters.append(char)
                if p_data.letter_case is None:
                    p_data.alternate_letters.append(char)
                elif p_data.letter_case == 'Ll':
                    p_data.alternate_letters.append(char.upper())
                elif p_data.letter_case == 'Lu':
                    p_data.alternate_letters.append(char.lower())

        escape = False
        in_letter = False
        unicode_escape = None
        for c in cldr_str:
            if escape:
                escape = False
                if c == 'u':
                    unicode_escape = ''
                else:
                    add_char(parse_data, c, in_letter, verify)
            elif c == '{':
                in_letter = True
                parse_data.letters.append('')
                parse_data.alternate_letters.append('') # might be superfluous
            elif c == '}':
                in_letter = False
            elif c == '\\':
                escape = True
            elif c == ' ':
                continue
            elif c == 'İ' and parse_data.letter_case == 'Ll':  # this character is hard to deal with outside the loop, so we check all the time
                if verify:
                    if in_letter:
                        print("Dotted I in multi-codepoint letter not supported cause it's hard")
                    if parse_data.letters[-1] != 'i' or parse_data.alternate_letters[-1] != 'I':
                        print("unexpected preceding letter for dotted I")
                parse_data.alternate_letters[-1] = c  # fix what would have been an incorrect upper-casing on the preceding i
            elif unicode_escape is not None:
                if len(unicode_escape) == 4:
                    add_char(parse_data, chr(int(unicode_escape, 16)), in_letter, verify)
                    unicode_escape = None
                else:
                    unicode_escape += c
            else:
                add_char(parse_data, c, in_letter, verify)

        if parse_data.letter_case is None:
            parse_data.letter_case = 'Lo'


    def _load_sequence_letters(self, cursor, sequence_id, sequence_letters):
        for i, letter in enumerate(sequence_letters):
            num_codepoints = len(letter)
            if num_codepoints == 1:
                cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?, ?, ?)", (sequence_id, ord(letter), i + 1)) # 1-index
            else:
                # try to see if letter already exists (I feel like there's a better way than how I did it, but can't quite get the SQL to work)
                query = f"SELECT id FROM sequence seq WHERE (SELECT COUNT(*) FROM sequence_item si WHERE seq.id = si.sequence_id) = ? AND seq.type_id = ?"
                letter_codepoints = []
                for j, code_point in enumerate(letter):
                    code_point_id = ord(code_point)
                    query += f" AND EXISTS (SELECT * FROM sequence_item si WHERE seq.id = si.sequence_id AND item_id = {code_point_id} AND order_num = {j + 1})"
                    letter_codepoints.append((code_point_id, j + 1))
                results = self.execute_query(query, return_headers=False, parameters=(num_codepoints, SequenceType.LETTER.value))

                if results: # existing letter found!
                    letter_seq_id = results[0][0]
                else:
                    letter_seq_id = self._create_sequence(cursor, SequenceType.LETTER)
                    cursor.executemany(f"INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES ({letter_seq_id}, ?, ?)", letter_codepoints)
                cursor.execute("INSERT INTO sequence_item (sequence_id, item_id, order_num) VALUES (?, ?, ?)", (sequence_id, letter_seq_id, i + 1))  # 1-index


    def _create_sequence(self, cursor, sequence_type):
        seq_id = self.get_next_sequence_id()
        cursor.execute("INSERT INTO sequence (id, type_id) VALUES (?, ?)", (seq_id, sequence_type.value))
        return seq_id


    def _load_japanese_cldr_alphabets(self, cursor, cldr_str):
        hiragana = []
        katakana = []
        kanji = []
        for c in cldr_str:
            if c == 'ー':  # shared character
                katakana.append(c)
                hiragana.append(c)
            elif c != ' ':
                ja_script_code = cursor.execute("SELECT script_code FROM code_point WHERE text = ?", (c,)).fetchone()[0]
                if ja_script_code == 'Kana':
                    katakana.append(c)
                elif ja_script_code == 'Hira':
                    hiragana.append(c)
                elif ja_script_code == 'Hani':
                    kanji.append(c)
                elif verify:
                    print(f"Error parsing Japanese CLDR data. Unexpected script {ja_script_code} for letter {c}")

        # Note: not dealing with script exemplars as the kana will be manually specified for that

        parse_data = self._CLDRParseData()

        parse_data.script_code = 'Kana'
        parse_data.letter_case = 'Lo'
        parse_data.letters = katakana
        self._load_alphabet(cursor, 'ja', parse_data, AlphabetType.EXTENDED, 'CLDR')

        parse_data.letters = hiragana
        parse_data.script_code = 'Hira'
        self._load_alphabet(cursor, 'ja', parse_data, AlphabetType.EXTENDED, 'CLDR')

        parse_data.letters = kanji
        parse_data.script_code = 'Hani'
        self._load_alphabet(cursor, 'ja', parse_data, AlphabetType.EXTENDED, 'CLDR')

        parse_data.letters = kanji[0:len(kanji) // 2]
        self._load_alphabet(cursor, 'ja', parse_data, AlphabetType.FULL, 'CLDR')

        parse_data.letters = kanji[0:len(kanji) // 4]
        self._load_alphabet(cursor, 'ja', parse_data, AlphabetType.BASIC, 'CLDR')

    # return as follows:
    # sequences of type letter and base return as a string
    # Other sequences return as lists (so a mixed sequence could look something like ['ab' ['c'], 'd', ['f', ['g', 'hi']]]
    def get_sequence(self, sequence_id):
        def get_seq_rec(cursor, seq_id):
            seq_type = cursor.execute("SELECT type_id FROM sequence WHERE id = ?", (seq_id,)).fetchone()[0]
            if seq_type == SequenceType.BASE.value:
                return chr(seq_id)
            if seq_type == SequenceType.LETTER.value:
                return cursor.execute("SELECT GROUP_CONCAT(CHAR(item_id),'' ORDER BY order_num) FROM sequence_item WHERE sequence_id = ?", (seq_id,)).fetchone()[0]

            retval = []
            items = cursor.execute("SELECT item_id FROM sequence_item WHERE sequence_id = ? ORDER BY order_num", (seq_id,)).fetchall()
            for item in items:
                retval.append(get_seq_rec(cursor, item[0]))
            return retval

        return get_seq_rec(self._cxn.cursor(), sequence_id)


    def _get_existing_letter_sequence_id(self, cursor, letters):
        # a bit of a hybrid approach - first attempt was joining every single letter, but this ran into a join limit
        # Instead, try just joining a few to significantly filter down the results, then compare in python
        # TODO - we might later consider an approach of trial inserting a sequence and compare two in-DB sequences, then delete duplicate
        COMPARISONS_TO_MAKE = 4
        comparison_count = 0
        query = f"SELECT seq.id FROM sequence seq"
        for i, letter in enumerate(letters):
            if len(letter) == 1: # singular code point, won't bother with multi cp letters here
                comparison_count += 1
                query += f" INNER JOIN sequence_item si_{i} ON si_{i}.order_num = {i + 1} AND seq.id = si_{i}.sequence_id AND si_{i}.item_id = {ord(letter)}"
                if comparison_count == COMPARISONS_TO_MAKE:
                    break

        if comparison_count != 4:
            print(f"Unexpectedly short letter sequence: {letters}")

        query +=  f" WHERE seq.type_id = {SequenceType.SIMPLE_ALPHABET.value}"
        candidate_ids = cursor.execute(query).fetchall()

        for candidate_id in candidate_ids:
            if letters == self.get_sequence(candidate_id[0]):
                return candidate_id[0]

        return None


    def _check_load_letter_sequence(self, cursor, letters):
        seq_id = self._get_existing_letter_sequence_id(cursor, letters)
        if not seq_id:
            seq_id = self._create_sequence(cursor, SequenceType.SIMPLE_ALPHABET)  # in future, maybe compound alphabets
            self._load_sequence_letters(cursor, seq_id, letters)
        return seq_id


    def _insert_alphabet(self, cursor, sequence_id, lang_code, script_code, letter_case, alphabet_type, source, notes=None):
        # TODO - ON CONFLICT DO NOTHING is a legacy of the hack where PK was (sequence_id, lang_code, type_id) on main table
        cursor.execute("INSERT INTO alphabet (sequence_id, lang_code, script_code, letter_case, notes) VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
                       (sequence_id, lang_code, script_code, letter_case, notes))
        self._load_table_sources(cursor, [source], 'alphabet', ['sequence_id', 'lang_code', 'alphabet_type_id'], [sequence_id, lang_code, alphabet_type.value])

    # is_index_load: quite hacky as we're really reaching into the calling context to make decisions here,
    #   but I've not otherwise figured out how to incorporate it while still maintaining a single reusable _load_alphabet method
    # Basically if its index, we do two things - override case for the return value and load the FULL alphabet if BASIC (index) and EXTENDED (main) match
    def _load_alphabet(self, cursor, lang_code, parse_data, alphabet_type, citation_key, load_case_pair=False, is_index_load=False, notes=None):
        def try_index_load(s_id, lang, script, lcase):
            matching_extended = cursor.execute("""
                SELECT * FROM alphabet_source
                WHERE sequence_id = ? AND lang_code = ? AND alphabet_type_id = ?""",
                    (s_id, lang, AlphabetType.EXTENDED.value))
            if matching_extended.fetchall():  # index (BASIC) and Extended are the same, fill-in the middle FULL
                self._insert_alphabet(cursor, s_id, lang_code, script, lcase, AlphabetType.FULL, SourceInfo('CLDR', 'index exemplar'))

        seq_id = self._check_load_letter_sequence(cursor, parse_data.letters)
        self._insert_alphabet(cursor, seq_id, lang_code, parse_data.script_code, parse_data.letter_case, alphabet_type, SourceInfo(citation_key))

        if is_index_load:
            try_index_load(seq_id, lang_code, parse_data.script_code, parse_data.letter_case)

        # casing
        if not load_case_pair:
            return seq_id
        if parse_data.letter_case == 'Ll':
            alternate_case = 'Lu'
        elif parse_data.letter_case == 'Lu':
            alternate_case = 'Ll'
        else:  # not a cased pair
            return seq_id

        alternate_id = self._check_load_letter_sequence(cursor, parse_data.alternate_letters)
        self._insert_alphabet(cursor, alternate_id, lang_code, parse_data.script_code, alternate_case, alphabet_type, SourceInfo(citation_key))

        if is_index_load:
            try_index_load(alternate_id, lang_code, parse_data.script_code, alternate_case)
            return seq_id

        if alternate_case == 'Ll':
            return seq_id
        return alternate_id


    def _load_manual_alphabet_data(self, cursor, verify):
        added_scripts = set()

        with open(os.path.join(self._resource_path, 'standard_alphabets.csv')) as csvfile:
            for row in csv.DictReader(csvfile):
                parse_data = self._CLDRParseData()
                parse_data.script_code = row['Script']
                parse_data.letter_case = row['Case'][0:2]
                lang_codes = row['Language']
                alphabet_types = row['Alphabet Type'] if row['Alphabet Type'] else str(AlphabetType.BASIC.value)
                alph_notes = row['Notes'] if row['Notes'] else None

                self._parse_cldr_exemplar_set(cursor, row['Alphabet'], parse_data, verify)
                if lang_codes:
                    for lang_code in lang_codes.split('/'):
                        for alphabet_type in alphabet_types.split('/'):
                            exemplar_id = self._load_alphabet(cursor,
                                                              lang_code,
                                                              parse_data,
                                                              AlphabetType(int(alphabet_type)),
                                                              row['Source'],
                                                              load_case_pair = '!' not in row['Case'],
                                                              notes=alph_notes)
                else:  # script-only exemplar
                    exemplar_id = self._check_load_letter_sequence(cursor, parse_data.letters)

                if str(AlphabetType.BASIC.value) in alphabet_types:  # TODO - a bit hacky, will fail if alphabet type ever gets to double digits
                    cursor.execute("UPDATE script SET exemplar_sequence_id = ? WHERE code = ?", (exemplar_id, parse_data.script_code))

                added_scripts.add(parse_data.script_code)

        return added_scripts


    def _load_cldr_alphabet_data(self, cursor, verify):
        def get_script_type_and_needed_alphabets(lang_code, script_code):
            # note this glosses over case: manually specified should always ensure both cases will be handled!
            def has_alphabet_type(lang, script, type): # avoid shadowing headache
                return len(cursor.execute("""
                    SELECT * FROM alphabet a INNER JOIN alphabet_source asrc ON a.sequence_id = asrc.sequence_id AND a.lang_code = asrc.lang_code
                    WHERE a.lang_code = ? AND a.script_code = ? AND asrc.alphabet_type_id = ?""",
                               (lang, script, type.value)).fetchall()) > 0

            script_type = cursor.execute("SELECT type_id FROM script WHERE code = ?", (script_code,)).fetchone()[0]
            return (
                script_type,
                not has_alphabet_type(lang_code, script_code, AlphabetType.EXTENDED),
                script_type in (ScriptType.ALPHABET.value, ScriptType.ABJAD.value) and not has_alphabet_type(lang_code, script_code, AlphabetType.BASIC)
            )

        # languages which use only one case of a cased script.
        # It has since occurred to me this can be per language-script combo, but given I've only found one language (code: oka) so far, I won't code for that yet
        # I was hoping this could be programmatically inferred from the index set, but alas the data file doesn't have an index set for oka
        unicase_languages = []
        with open(os.path.join(self._resource_path, 'unicase_languages.txt'), 'r') as file:
            for line in file:
                unicase_languages.append(line.strip())

        added_scripts = set()

        # yes an xml parser would be more appropriate, but this is a simple task (and lxml seemed to choke and I don't feel like learning another module...)
        # (also there's a potential performance concern in that the exemplars come relatively early in the long files, in case an xml parser might read the whole file)
        exemplar_pattern = re.compile(r'\s*<exemplarCharacters([^>]*)>\[(.+)]</exemplarCharacters>')

        # From CLDR, we pull the main exemplar set as an Extended type alphabet
        # For Alphabet and Abjads the index exemplar set should work for the Basic type alphabet (and full can be inferred if its the same as extended)
        for file_name in os.listdir(os.path.join(self._unicode_path, 'cldr')):
            if file_name == 'license.txt':  # really i should just move this at some point
                continue
            lang_str = file_name.split('.')[0].split('_')
            lang_code = lang_str[0]
            script_code_check = lang_str[1] if len(lang_str) > 1 else cursor.execute("SELECT default_script_code FROM language WHERE code = ?", (lang_code,)).fetchone()[0]
            script_type = None
            need_basic = True
            need_extended = True

            if script_code_check:
                script_type, need_extended, need_basic = get_script_type_and_needed_alphabets(lang_code, script_code_check)

            # No need to read CLDR if we already have manually specified data
            if not need_extended and not need_basic:
                continue

            with (open(os.path.join(self._unicode_path, 'cldr', file_name), 'r') as file):
                line_number = 0  # purely for debug
                exemplar_type = None
                for line in file:
                    if not need_basic and not need_extended:
                        break  # don't need anything in this file (but we need condition in the loop due potentially determining thi sin the loop)
                    line_number += 1
                    match = exemplar_pattern.match(line)

                    if match:
                        attributes = match.group(1)
                        if not attributes or (len(attributes.split()) == 1 and ('draft' in attributes or 'reference' in attributes)):
                            exemplar_type = 'main'
                        elif 'index' in attributes:
                            exemplar_type = 'index'
                        else:
                            continue  # we're only looking for main and possibly index

                        if not need_basic and exemplar_type == 'index':
                            continue
                        if not need_extended and exemplar_type == 'main':
                            continue

                        if file_name == 'ja.xml':  # special case hack-y handling
                            need_basic = False
                            if exemplar_type == 'main':
                                self._load_japanese_cldr_alphabets(cursor, match.group(2))
                                added_scripts.add('Hira')
                                added_scripts.add('Kana')
                                added_scripts.add('Hani')
                                break
                        else:
                            parse_data = self._CLDRParseData()

                            if lang_code in unicase_languages:
                                parse_data.letter_case = 'Lo'  # hard set languages which use only a single case of a cased alphabet to uncased

                            parse_data.script_code = script_code_check
                            if verify and len(lang_str) == 1:
                                parse_data.script_code = None  # basically if verifying, we don't assume CLDR data matching IANA default script

                            self._parse_cldr_exemplar_set(cursor, match.group(2), parse_data, verify and exemplar_type == 'main')
                            # TODO - We have issues dealing with title case in the index sets

                            if not script_code_check:  # we will now have inferred script
                                script_code_check = parse_data.script_code
                                script_type, need_extended, need_basic = get_script_type_and_needed_alphabets(lang_code, script_code_check)
                                if not need_basic and not need_extended:
                                    break
                                if not need_extended:  # we know we're in main cause it's the first one (so the only one where we might not know script yet)
                                    continue

                            if exemplar_type == 'index' and len(parse_data.letters) < 10:
                                continue  # skip, sometimes the index isn't the basic alphabet, and we assume that for less than 10

                            # Correcting some special cases of casing changes (dotted I dealt with in the parsing)
                            # These are dealt with here as we can use language/script codes rather than checking every character for efficiency
                            # (at loss of a bit of generalisation)
                            # Note: Per Wikipedia, capital eszett is officially preferred in Standard German as of 2024
                            #  No correction needed here because German has been manually specified (but may need to keep an eye out for German variants using eszett)
                            if parse_data.script_code == 'Grek':
                                if parse_data.letter_case == 'Ll':
                                    parse_data.alternate_letters.remove('Σ')  # duplicate caused by two lowercase sigma forms
                                elif exemplar_type != 'index':  # index is basic alphabet
                                    parse_data.alternate_letters.insert(parse_data.alternate_letters.index('σ') + 1, 'ς')  # opposite problem
                            elif lang_code == 'kaa' and parse_data.script_code == 'Latn' and parse_data.letter_case == 'Ll':  # I don't want to talk about this one
                                parse_data.alternate_letters[parse_data.alternate_letters.index('I')] = 'Í'

                            if verify and len(parse_data.letters) != len(set(parse_data.letters)) and lang_code != 'ken':
                                # ken has mixed case (not title) in index set for some reason. Suppressing for now cause not sure what to do about it
                                print(f"Detected duplicate letters in alphabet for {lang_code}, {parse_data.script_code}: {parse_data.letters}")

                            if len(lang_str) == 1:  # this is taken to be the default script for a language
                                if verify:
                                    default_script = cursor.execute("SELECT default_script_code FROM language WHERE code = ?", (lang_code,)).fetchone()[0]
                                    if default_script and default_script != parse_data.script_code:
                                        print(f"CLDR and IANA data conflict on default script of language {lang_code}: {parse_data.script_code} / {default_script}")
                                cursor.execute("UPDATE language SET default_script_code = ? WHERE code = ?", (parse_data.script_code, lang_code))

                            self._load_alphabet(cursor,
                                                  lang_code,
                                                  parse_data,
                                                  AlphabetType.EXTENDED if exemplar_type == 'main' else AlphabetType.BASIC,
                                                  'CLDR',
                                                  load_case_pair=True,
                                                  is_index_load= exemplar_type == 'index')

                            # Technically if a logograph script had case, then we should add those as well... probably doesn't exist
                            if script_type == ScriptType.LOGOGRAPH:
                                if verify and parse_data.letter_case in ('Ll', 'Lu'):
                                    print(f"Unsupported cased logograph language {lang_code}, script {parse_data.script_code}")

                                parse_data.letters = parse_data.letters[0:len(parse_data.letters) // 2]
                                self._load_alphabet(cursor, lang_code, parse_data, AlphabetType.FULL,  'CLDR')

                                parse_data.letters = parse_data.letters[0:len(parse_data.letters) // 4]
                                self._load_alphabet(cursor, lang_code, parse_data, AlphabetType.BASIC, 'CLDR')

                            added_scripts.add(parse_data.script_code)

                            if script_type not in (ScriptType.ALPHABET.value, ScriptType.ABJAD.value):
                                break  # we only pull main for these

                    elif exemplar_type:
                        break  # done exemplar section, stop parsing this file and go to next
                if not exemplar_type and verify and line_number > 15:
                    # line number is a blunt tool to avoid excessive reporting on the "stub" entries
                    print(f'Could not find exemplar characters in {file_name}')

        return added_scripts


    def _load_generated_alphabet_data(self, cursor, existing_scripts, verify):
        with (open(os.path.join(self._resource_path, self._GENERATED_DIR_NAME, 'standard_alphabets.csv')) as csvfile):
            for row in csv.DictReader(csvfile):
                parse_data = self._CLDRParseData()
                parse_data.script_code = row['Script']

                # generated data is a last-resort
                if not parse_data.script_code in existing_scripts:
                    self._parse_cldr_exemplar_set(cursor, row['Alphabet'], parse_data, verify)

                    # For generated stuff try to tag a language for a script if we can
                    lang_code = cursor.execute("SELECT main_lang_code FROM script WHERE code = ?", (parse_data.script_code,)).fetchall()[0][0]

                    if lang_code:
                        id = self._load_alphabet(cursor, lang_code, parse_data, AlphabetType.BASIC, row['Source'])
                        # note for generated we're not bothering with a second addition for case - the indic and semitic alphabets are all uncased
                    else:
                        id = self._check_load_letter_sequence(cursor, parse_data.letters)

                    cursor.execute("UPDATE script SET exemplar_sequence_id = ? WHERE code = ?", (id, parse_data.script_code))

    # TODO: should probably be a bit smarter about transactions for the alphabet stuff
    def _load_alphabet_data(self, cursor, verify):
        added_scripts = self._load_manual_alphabet_data(cursor, verify)
        added_scripts |= self._load_cldr_alphabet_data(cursor, verify)
        self._load_generated_alphabet_data(cursor, added_scripts, verify)


    def get_code_point_script_parents(self, id, scripts_to_skip=None):
        return self._get_code_point_script_parents(self._cxn.cursor(), id, option, 1)


    def _get_code_point_script_parents(self, cursor, id, scripts_to_skip=None, weight=1):
        retval = {}
        temp = cursor.execute("""
            SELECT script_code FROM code_point
            WHERE id = ? AND general_category_code NOT LIKE 'C_' AND general_category_code NOT LIKE 'Z_'""", (id,)).fetchall()
        if not temp:
            raise ValueError("Tried to find parent script of non-graphical character")
        script_code = temp[0][0]

        # TODO favour more certain derivations
        parent_code_points = cursor.execute("""
            SELECT cp.id, cp.script_code  
            FROM code_point cp INNER JOIN code_point_derivation cpd ON cp.id = cpd.parent_id 
            WHERE cpd.child_id = ?""", (id,)).fetchall()
        num_parents = len(parent_code_points)

        if num_parents == 0:  # missing data, use empty string as a missing code
            retval[''] = weight
        else:
            for parent in parent_code_points:
                if scripts_to_skip and parent[1] in scripts_to_skip:
                    grand_parents = self._get_code_point_script_parents(cursor, parent[0], scripts_to_skip, weight / num_parents)
                    for grand_parent in grand_parents:
                        self._add_or_increment_dict_entry(retval, grand_parent, grand_parents[grand_parent])
                else: # different parent script
                    self._add_or_increment_dict_entry(retval, parent[1], weight / num_parents)

        return retval

    # This isn't simple recursion due to weights
    # (base case) A single code point will have its parent scripts equally weighted
    # A letter will have its constituent code points equally weighted
    # A general sequence will have its constituent letters and code points equally weighted
    # A general sequence of general sequences will have a pass-through effect, with letters and code points being equally weighted, not higher-order sequences
    # While a little academic for now, this is designing for an "alphabet of alphabets" eg. having an English alphabet that is two sub-alphabets distinguished by case
    def _get_sequence_script_parents(self, cursor, sequence_id, scripts_to_skip=None):
        seq_type = cursor.execute("SELECT type_id FROM sequence WHERE id = ?", (sequence_id,)).fetchone()[0]
        if seq_type == SequenceType.BASE.value:
            return self._get_code_point_script_parents(cursor, sequence_id, scripts_to_skip, 1)

        retval = {}
        if seq_type == SequenceType.LETTER.value:
            code_points = cursor.execute("""
                SELECT cp.id FROM sequence_item si INNER JOIN code_point cp ON si.item_id = cp.id
                WHERE si.sequence_id = ? AND cp.general_category_code NOT LIKE 'C_' AND cp.general_category_code NOT LIKE 'Z_'""", (sequence_id,)).fetchall()
            for code_point in code_points:
                results = self._get_code_point_script_parents(cursor, code_point[0], scripts_to_skip, 1 / len(code_points))
                for result in results:
                    self._add_or_increment_dict_entry(retval, result, results[result])
        else:
            sub_sequences = cursor.execute("SELECT item_id FROM sequence_item WHERE sequence_id = ?", (sequence_id,)).fetchall()
            for sub_sequence in sub_sequences:
                results = self._get_sequence_script_parents(cursor, sub_sequence[0], scripts_to_skip)
                for result in results:
                    self._add_or_increment_dict_entry(retval, result, results[result])

        return retval


    def _get_exemplar_sequence_id_with_fallback(self, cursor, script_code):
        sequence_id = cursor.execute("SELECT exemplar_sequence_id FROM script WHERE code = ?", (script_code,)).fetchall()[0][0]
        if not sequence_id:
            seq = cursor.execute("""
                SELECT a.sequence_id 
                FROM 
                    script s 
                    INNER JOIN alphabet a ON a.script_code = s.code
                    INNER JOIN alphabet_source asrc ON asrc.sequence_id = a.sequence_id AND a.lang_code = asrc.lang_code
                WHERE s.code = ? AND asrc.alphabet_type_id >= ?
                ORDER BY 
                    asrc.alphabet_type_id,   -- prefer basic over full over extended
                    CASE WHEN s.main_lang_code = a.lang_code THEN 0 ELSE 1 END, -- prefer main language                  
                    a.letter_case DESC       -- prefer upper case
                LIMIT 1""", (script_code, AlphabetType.BASIC.value)).fetchall()
            if seq:
                sequence_id = seq[0][0]
        return sequence_id

    # Script skipping has two main uses: Can avoid self-derivation, and avoid a parent script you think isn't that distinct
    def get_script_parents(self, script_code, scripts_to_skip=None):
        real_skips = set(scripts_to_skip) if scripts_to_skip else set()
        real_skips.add(self.INHERITED_SCRIPT)
        # we want to pass through inherited - in Unicode I assume this means a combining mark inheriting the script of the base character
        # but for graphical purposes we want to get to the combining mark's parent script

        cursor = self._cxn.cursor()
        sequence_id = cursor.execute("SELECT exemplar_sequence_id FROM script WHERE code = ?", (script_code,)).fetchall()
        if not sequence_id:
            raise ValueError("Script does not yet have an identified canonical set of letters")

        results = [('Parent Script', 'Number of Letters')]
        raw_results = self._get_sequence_script_parents(cursor, sequence_id[0][0], real_skips)
        for script, value in sorted(raw_results.items(), key=lambda item: item[1], reverse=True):
            if script == self.COMMON_SCRIPT:
                script_name = '(symbol)' # probably
            elif script == 'Zzzz':  # only the signal U+FFFF character
                script_name = '(original/unknown)'
            elif script == '':
                script_name = '(missing data)'
            else:
                script_name = cursor.execute("SELECT name FROM script WHERE code = ?", (script,)).fetchone()[0]
            results.append((script_name, f"{value:.2f}"))

        return results


    def load_database(self, load_options=None):
        def output_info(message, start_time, lap_time, lap_mb):
            current_time = time.time()
            current_mb = os.path.getsize(os.path.join(self._db_path, self._db_name)) / 1000000
            print(f"{message} Elapsed: {current_time - start_time:.2f} s (+{current_time - lap_time:.2f} s). Size: {current_mb:.1f} MB (+{current_mb - lap_mb:.1f} MB)")
            return current_time, current_mb

        options = load_options if load_options else LoadOptions()
        output = options.output_debug_info

        if options.force_overwrite:
            if os.path.isfile(os.path.join(self._db_path, self._db_name)):
                os.remove(os.path.join(self._db_path, self._db_name))
            if os.path.isfile(os.path.join(self._db_path, self._db_name + '-journal')):
                os.remove(os.path.join(self._db_path, self._db_name + '-journal'))
            self._set_connection()
            self._next_sequence_id = ScriptDatabase.UNICODE_MAX
        if options.resource_path:
            self._set_resource_paths(options.resource_path)
        if options.saved_query_path:
            self._query_path = options.saved_query_path

        path = os.path.join(self._resource_path, 'cr-exclusion')
        if self._try_unzip_sources(os.path.join(self._resource_path, 'cr-exclusion')):
            if output: print(f'Source files unzipped to {self._resource_path}')
        elif output: print(f'At least one zip file not present in {path}, relying on existing files in {self._resource_path}')

        cur = self._cxn.cursor()
        start_time = time.time()
        lap_time = start_time
        lap_mb = 0
        if output: print('Setting up schema (starting timer)...')

        cur.execute("PRAGMA foreign_keys = OFF")
        self._setup_schema(cur)
        if options.verify_data_sources:
            cur.execute("PRAGMA foreign_keys = ON")

        self._load_lookups(cur)
        self._cxn.commit()
        deferred = self._load_scripts(cur)
        self._cxn.commit()
        self._load_languages(cur)
        self._cxn.commit()
        self._load_deferred_script_fields(cur, deferred)
        self._cxn.commit()
        self._load_sources(cur)
        self._cxn.commit()
        if output: lap_time, lap_mb = output_info("Done basics: loading lookups, languages, scripts and sources.", start_time, lap_time, lap_mb)

        # updates generally expected on these table, just clear (and before loading code points so cleared space can be used)
        cur.execute("DELETE FROM manual_derivation_source")
        cur.execute("DELETE FROM code_point_derivation")
        self._load_code_point_data(cur)
        self._cxn.commit()
        if output: lap_time, lap_mb = output_info("Done loading code point data.", start_time, lap_time, lap_mb)

        indic_letter_data = self._get_indic_letter_dict(cur, options.verify_data_sources)
        self._load_private_use_data(cur, indic_letter_data)
        semitic_letter_data = self._get_semitic_letter_dict()
        indic_supp_data = self._get_indic_supplement_dict(cur, indic_letter_data)
        self._generate_std_alphabets(semitic_letter_data, indic_letter_data, indic_supp_data)
        if options.drop_bidi_class_column:  # TODO: is it possible to not even load this column to start?
            cur.execute("ALTER TABLE code_point DROP COLUMN bidi_class_code")
        self._cxn.commit()
        if output: lap_time, lap_mb = output_info("Done generating letter data and loading private use data.", start_time, lap_time, lap_mb)

        cur.execute("PRAGMA foreign_keys = ON") # there's a bit of a tricky query in load_derivations that currently relies on ON DELETE CASCADE
        self._load_derivations(cur, indic_supp_data, indic_letter_data, semitic_letter_data, options)
        if not options.verify_data_sources:
            cur.execute("PRAGMA foreign_keys = OFF")
        self._cxn.commit()
        if output: lap_time, lap_mb = output_info("Done loading derivation data.", start_time, lap_time, lap_mb)

        self._load_alphabet_data(cur, options.verify_data_sources)
        self._cxn.commit()
        if output: lap_time, lap_mb = output_info("Done loading alphabet data.", start_time, lap_time, lap_mb)

        if options.drop_unused_languages:
            self._drop_unused_languages(cur)
            self._cxn.commit()
        if options.vacuum_db:
            cur.execute("VACUUM")

        if output:
            print("=" * 80)
            print(f'Database loaded. Total time: {time.time() - start_time:.2f} s. Total size: {os.path.getsize(os.path.join(self._db_path, self._db_name)) / 1000000:.1f} MB')
            priv_use_counts = cur.execute("""
                SELECT is_alphabetic, COUNT(*) FROM code_point 
                WHERE script_code LIKE 'Q%' OR script_code IN ('Psin', 'Egyd')
                GROUP BY is_alphabetic
                ORDER BY is_alphabetic""").fetchall()
            print(f"Number of private use letters: {priv_use_counts[1][1]} (+{priv_use_counts[0][1]} non-letter characters)")
            self.print_table(self.execute_saved_query('Total derivation statistics'))
        if options.verify_data_sources:
            self._verify_script_coverage(cur)

        cur.execute("PRAGMA foreign_keys = ON")
        return cur


    class _CLDRParseData:
        def __init__(self):
            self.letters = []
            self.alternate_letters = []  # generally uppercase, but also want to leave open the possibility for a uni-cased uppercase language
            # fields can be supplied to speed up parsing, or they will be determined by algorithm
            self.script_code = None
            self.letter_case = None


class Certainty(Enum):
    UNSPECIFIED = -1
    NEAR_CERTAIN = 1
    LIKELY = 2
    UNCERTAIN = 3
    STRONG_ASSUMPTION = 4
    WEAK_ASSUMPTION = 5
    VARIED = 6


# at the moment I'm isolating ranges of things I think could be expanded on.
class SequenceType(Enum):
    BASE = 1
    GENERAL = 2
    LETTER = 3
    SIMPLE_ALPHABET = 4

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

    POSITION_DISTINCTION = 180

    Z_VARIANT = 200
    HIEROGLYPHIC_ALTERNATIVE = 201


class AlphabetType(Enum):
    UNSPECIFIED = 1
    INHERITED = 2
    BASIC = 3
    FULL = 4
    EXTENDED = 5
    AUXILIARY = 6


class ScriptType(Enum):
    UNKNOWN = 1
    NOT_APPLICABLE = 2
    MIXED = 3
    ALPHABET = 4
    ABUGIDA = 5
    ABJAD = 6
    SYLLABARY = 7
    LOGOGRAPH = 8


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
    TRANSLATION = 10


if __name__ == '__main__':
    db = ScriptDatabase()

    cursor = db.load_database(ScriptDatabase.OPTIMIZED_DEBUG_LOAD)  # replace with DEBUG_LOAD for development run

    # do stuff here if you want, for example:
    # results = db.execute_saved_query('Get Character Ancestors', parameters=('a',))
    # db.print_table(results)
    # Get a breakdown of a script's parent scripts:
    # db.print_table(db.get_script_parents('Glag', ['Glag']))
    # or your own custom query: db.execute_query('YOUR QUERY HERE', parameters=None)

    cursor.close()