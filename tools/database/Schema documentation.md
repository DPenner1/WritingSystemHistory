
# Schema & data documentation

## Tables

The `*_type` tables are lookup tables that should mostly be self-explanatory based on their data (though `certainty_type` is given a much fuller explanation here). They are only described here as necessary for the purposes of understanding the main tables.

Many of the tables have a `name` field. For `code_point`, this is mostly the name as specified by Unicode, but is overriden when an alternate name is available, specifically when it's a correction or it's a control character (which officially has no name per the standard). The `language` and `script` tables simply make a singular choice as to a name.

It should be noted that the code which generates the database is configurable and can drop various columns/tables for leaner deployment tailored to specific use cases.

The tables are as follows, in alphabetical order.

### `*_source`

These are cross-reference tables between the `source` table and the other `*` table (naming may vary). It's many:many but it's conceptually best to view the `source` table as the child table and the non-source table as the parent table.

  - The `section` field is a free-text field intended for referring to a location within the source, not necessarily a literal "section."
  - The `access_date` field is a Julian Day value from sqlite (while there is not currently a "published date" field encoded for sources, they could easily be from before 1970, so a UNIX timestamp is not favoured for the database as a whole). Frequently null, indeed part of the point of some sources is that they are evergreen so that maintenance load is reduced (eg. Unicode data files).
  - The `*` table will have a `notes` field. This allows explanatory comment for the parent record that can reference across multiple sources.

### `alphabet`, `alphabet_source`

Data on alphabets used by various languages, with the specific letters being stored in the referenced `sequence` table. While it might seem like overkill (and probably still is), this table is to help determine the "canonical" letters for a language and is probably a more user-friendly concept than script. An "alphabet" in this schema is intended to be a bit broader than a dictionary definition, in order to account for fuzzy boundaries. The conceptual understanding should be "a meaningful collection of characters associated to a language."

 - Languages can have multiple alphabet entries, distinguishing on case, script and type.
 - The `letter_case` field hijacks the general category code, using `Lu`, `Ll` for upper/lower and `Lo` for uncased. Potential future codes are `LC` and/or `Lx` for unspecified and/or mixed cased (I believe I saw the former used somewhere in Unicode documentation).
 - Alphabets are represented as a sequence of letters and code points, with letters themselves being sequences of code points. Single code point letters are not boxed into a single-item letter sequence (this feels like too much unnecessary data bloat as this is the majority case). The data structure supports alphabets of alphabets (eg. could combine cases, or separate out Indic consonants and dependent/independent vowels), but current codegen does not do this.
 - The `alphabet_source` table follows a slightly different design to the other source tables. Each alphabet can be associated to multiple types, so a 1:many with a `alphabet_type_id` field was already required. Then it seemed rather unlikely multiple sources would be needed for a given alphabet × type. So the schema is such that only a singular source can be specified for it, removing the need for separate type and source tables.
     - The `alphabet_type_id` is the current attempt at a rough categorization. The author frankly does not currently understand enough about different languages and cultures for this to be broadly applicable and this is susceptible to change in the future. The main types are "basic", "full" and "extended." The current distinction being made is that "basic" is the canonical set of letters, "full" includes accepted letter variants or secondary letters (eg. German äöüß) while "extended" includes all letter glyphs required to write a language (eg. such an extended letter glyph in Greek is ΐ - iota with diaeresis and tonos accent - my understanding is the diacritics are viewed as separate from the letter itself). These are language-specific determinations, eg. ä generally being viewed as a variant of "a" in German, but a fully independent letter in Swedish (to my understanding). Frequently the same set of letters may stand-in for multiple types, eg. in English the A-Z sequence is all three of these types.
        - Logographic scripts already challenge this categorization. At present, these different types will simply return a smaller/larger set of characters.
     - Use the `source_id` field to determine where the alphabet comes from. The code loads alphabets from three sources: Manually specified, [CLDR data](https://cldr.unicode.org/) and automatically generated (from the same process that does Brahmi and Semitic letters).
        - Note that CLDR data only covers modern languages. The data are loaded as "extended" alphabet types from CLDR's main exemplar set. Abjad and Alphabet type scripts further have "basic" types loaded from the index set (these tend to be underspecified for logographs, syllabaries and probably abugidas too - dependent vowels usually being missing). Note that CLDR does tend to follow the language's alphabet order, but sometimes the accented characters are grouped together (which may or may not be how a language typically orders letters).
        - I have yet to decide what precisely to do with the Chinese language(s). CLDR has separately specified Traditional and Simplified characters, but in the Unicode character database they are under a single script code.
        - Perhaps in the future, sourcing may be bifurcated in the same manner as `code_point_derivation`, but with only two automated processes this is likely overengineering (but tempting; having an FK to reference the exact same process as the Indic/Semitic letter derivations feels so tidy).
     - At present, the data is largely unverified.
 - **Design considerations.** This table was simultaneously the most subjective and least important for this project. The codegen loads only "letters", but symbols could in principle be supported by the data structure.
    - The loose definition leads to the PK `(lang_code, sequence_id)`.
    - The `script_code` and `letter_case` may at first glance seem inferable from the referenced sequence id, but consider potential alphabets with mixed case or mixed script. It needs to be possible to make a manual determination for the overall case/script even if the sequence contains exceptions.
    - There is no current support for designating historical versions of alphabets. For historical languages/scripts, any included alphabet is interpreted as the most recent possible.
    - The design intends for `(lang_code, alphabet_type_id, script_code, letter_case)` to always specify at most one sequence (the real world is messier with uncertainty, but the design calls for making a choice). In many cases this will be overspecifying (uncased languages, languages only ever written in a singular script, etc.).

### `certainty_type`

Certainty is a rough measure of the strength of evidence for a derivation used on the `code_point_derivation` table. As a visualization (and as planned for the front end), a derivation can be envisioned as an arrow from parent to child and that arrow can have a solid, dashed or dotted line in order of decreasing evidence strength. The IDs are:

 - ID -1 *Unspecified (dotted)*: This is considered a missing data error.
 - IDs 1-3 are the straightforward *Near Certain*/*Likely*/*Uncertain* with corresponding arrows.
 - IDs 4-5 are the "assumed" types where there is no specific source, but has been derived by the database author for one reason or another (it is considered a data error for all the other IDs to not have an associated entry in either `manual_derivation_source` or `process_source`). If a source is provided anyways for these derivations, it is informative or tangential, but not direct.
     - ID 4 *Strong Assumption (dashed)*: To a large extent, the purpose of this ID existing is to compensate for the fact it's hard to find sources for such obvious derivations. 
        - There are a few "default" reasons for a strong assumption (and are permitted to have a null `notes` field):
           1. A child script with strongly matching glyph and sound (or function for unpronounced characters like punctuation).
           2. A glyph that is a transparent combination of same-script glyphs (eg. letter plus diacritic, ligatures, etc.)
           3. A glyph that is a minor modification of a same-script glyph (eg. addition of a small mark, lowercase being small uppercase, etc.).
           4. Simple transparent combination of rules 2 & 3.
        - Note: in specifying a derivation under rules 2-4, care should be taken to ensure that the same transparent change did not first occur in a parent script (and so the child script inherited this derivation rather than creating it itself).
        - If there is another reason for a strong assumption (eg. a documented sound shift occurred, or follows a general pattern of glyph changes), this must be explained in the appropriate `notes` field.
     - ID 5 *Weak Assumption (dotted)*: It is considered a data error to not have a justification in the approriate `notes` field.
 - ID 6 *Variable (dashed)* is a special code used by automated derivation processes where an individualized certainty cannot reasonably be assigned. A prime example of this is the process which automatically derives Indic cognate letters. Derivations are made based on known script parentage, but occasionally a script does something special for a letter (eg. borrows it from somewhere, internally modifies a letter, etc.). On top of that, sometimes the parent-child relationship is not fully certain, so certainty runs the full gamut here from obviously correct to obviously incorrect.

### `code_point`

Mostly what you would expect from Unicode.

 - Non-character U+FFFF is used as a signal value for when a character has been evaluated to have no known ancestor (to distinguish it from the case where data is simply missing).
 - Private use characters are used for historical scripts not yet in Unicode proper. For the Brahmi-based scripts, adding these characters is a partially automated process which may not be 100% accurate.
 - Field `equivalent_sequence_id` combines various Unicode sources for "equivalent" code points and some custom equivalency. May have to change later, but as it stands these sources do not overlap. These are decomposition (including Hangul Syllable/Jamo), z-variants (the lowest code point in a set has been taken to be the original) and Hieroglyph alternate sequences (kEH_AltSeq). The custom equivalency is positional equivalence, for when a Unicode characters is the same graphical character but has technical or positional distinction (so far two sub-categories: combining marks existing as stand-alone/modifiers and Hangul initial/final consonants).
 - Field `is_independently_graphical` is a custom property similar in function to other Unicode derived properties. It is meant to indicate the character has a graphical representation independent of its surrounding context. I was not able to find an existing Unicode property to match this intuition. By default Unicode general categories `C_` and `Z_` are considered non-graphical while the rest are, with a manually maintained exception list. There are no current `Z_`, `S_` and `L_` exceptions. `C_` exceptions are varied, the trickiest call was whether a soft hyphen was an exception, current decision is no. So far, known `M_` exceptions are the variation selectors and Pollard Miao script tone position characters.

### `code_point_derivation`

This is the main table for this project, mapping out the historical derivations of characters. In an ideal world, all characters would be manually reviewed. Last I checked, that was not the case. So, a sizable proportion are automatically generated from various data sources. For certainty, manually specified data will always override automatic data source. This table is also liable to rename to `code_point_relation` if project scope expands.

  - The `derivation_type_id` borders on legacy. However, there's not really any reason to drop it formally, most new data is simply taking the default value without breaking anything.
  - `certainty_type_id`: see `certainty_type` table. (trivia - the derivation and certainty types essentially swapped places in terms of usefulness and the database author's initial anticipation of their usefulness).
  - `process_type_id`: Indicates the process by which the derivation was made. It may be sufficient to some users to simply distinguish between manual and automatic derivations. Manual is ID 1, Automatic is all others. It should be noted that besides IDs 1 & 2, specific IDs should not be considered stable across release versions.
  - The intent is that an automatic process is permissible if it's expected that at least 75% of derivations made by the process would also be made if the derivations were done manually (minutia: this does not mean that the derivation itself has &ge;75% likelihood of being correct, as it could be a low-certainty derivation). The certainty assigned to an automatic derivation should roughly match the certainty that would be assigned were the derivation to be done manually. This is done ignoring the case where the derivation is incorrect for automation reasons, but not ignoring reasons of incorrect underlying data.
  - Sourcing for this table is bifurcated: `manual_derivation_source` for manual derivations and `process_source` for automatic ones. As is the pattern for `*_source` tables, both parent tables have a `notes` field. However, it is conceivable that an automatic process could additionally write to the `code_point_derivation.notes` field for explanatory comments that apply to a subset of derivations that the process makes (current processes do not yet do this).

### `language`

Loaded mainly from the IANA language subtag registry (see licence info in README). This source was preferred over ISO 639 due to friendlier licensing and closer alignment with CLDR (I'm sure the codes mostly match anyways). The `default_script_code` field is supplemented by CLDR data if missing from IANA.

### `script`

A manually maintained table. Started out based on the list found [here](https://www.unicode.org/iso15924/iso15924-codes.html).

  - To my understanding, the original source table having rows without a Unicode Alias yet having a Unicode version date are scripts which Unicode considers a font variant of another. This was marked with the `canonical_script_code` field, but the usefulness is questionable.
  - The `exemplar_sequence_id` field references a canonical set of letters. Associating to a sequence and not an alphabet allows for language-independence (eg. could be useful for Cyrillic where there isn't a universally agreed set of canonical letters). A sequence has been manually specified for a few scripts. The process which does Brahmic and Semitic letters will fill this in if as a "last resort" if none is specified either directly or in the `alphabet` table. If there is no exemplar sequence, one can be selected from the `alphabet` table as required.
  - The `main_lang_code` field designates the main language for a script. For the most part determining this was not difficult. Canadian Aboriginal syllabics was the main judgment call: It could have been Ojibwe, Cree, or Inuktitut. Ojibwe syllabics was not in the CLDR data leaving Cree and Inuktitut. In CLDR, only Swampy Cree specifically was in the files, which would be much fewer speakers than Inuktitut. However, between considering Cree more widely and that Inuktitut discarded the distinct final consonants (and this project is for finding interesting graphical developments), I've associated it to Swampy Cree (in the future it may be feasible to associate to more general Cree as the data exists, but the codegen doesn't yet do anything with macrolanguages).
  - The table includes data for private use scripts. These are:
    - Proto-Sinaitic (exists in ISO but not Unicode proper)
    - Pallava
    - Kadamba
    - Landa
    - Nagari
    - Gaudi
    - Gupta
    - Demotic (subset, exists in ISO but not Unicode proper)
    - Pitman Shorthand (non-Logographic characters only)

### `sequence`

A sequence of sequences (recursive tree). Each code point also has a "dummy" base entry sequence in the table, with a matching ID. Use the `type_id` field to determine what kind of sequence you are looking at.

### `sequence_item`

An item in a sequence. The base code point sequences do *not* have an entry in this table, they are the leaf items in the tree.

### `source`

Provides reference sources. Note this is far from the highest academic rigour, it is mainly to provide at least a minimum level of traceability. Field `parent_id` refers to the parent source where the given source can be found. The motivation here is to be able to designate separate authors for a book/journal and individual chapters/articles (generally the parent authors would be referred to as editors - again the citation rigour isn't the strongest in this project, just enough for traceability). Additionally there was not always a URL to provide at the lower level, so linking the parent helps with this. There is an `authors` field which for now is "list" field (there's no real reason yet in this project to 1:many this field, it is not actively used and is included only for proper credit and traceability).
