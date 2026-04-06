
# Schema & data documentation

## Tables

The `*_type` tables are lookup tables that should mostly be self-explanatory based on their data (though `certainty_type` is given a much fuller explanation here). They are only described here as necessary for the purposes of understanding the main tables.

Many of the tables have a name field. For `code_point`, this is mostly the name as specified by Unicode, but is overriden when an alternate name is available, specifically when it's a correction or it's a control character (which officially has no name per the standard). The `language` and `script` tables simply make a singular choice as to a name.

The tables are as follows, in alphabetical order.

### `alphabet`

Data on alphabets used by various languages, with the specific letters being stored in the referenced `sequence` table. While it might seem like overkill (and probably still is), this table is to help determine the "canonical" letters for a language and is probably a more user-friendly concept than script. An "alphabet" in this schema is intended to be a bit broader than a dictionary definition, in order to account for fuzzy boundaries. The conceptual understanding should be "a meaningful collection of characters associated to a language."

 - Languages can have multiple alphabet entries, distinguishing on case, script and type.
 - The `type_id` is the current attempt at a rough categorization. The author frankly does not currently understand enough about different languages and cultures for this to be broadly applicable and this is susceptible to change in the future. The main types are "basic", "full" and "extended." The current distinction being made is that "basic" is the canonical set of letters, "full" includes accepted letter variants or secondary letters (eg. German äöüß) while "extended" includes all letter glyphs required to write a language (eg. such an extended letter glyph in Greek is ΐ - iota with diaeresis and tonos accent - my understanding is the diacritics are viewed as separate from the letter itself). These are language-specific determinations, eg. ä generally being viewed as a variant of "a" in German, but a fully independent letter in Swedish (to my understanding).
    - Logographic scripts already challenge this categorization. At present, these different types will simply return a smaller/larger set of characters.
 - Alphabets are represented as a sequence of letters and code points, with letters themselves being sequences of code points. Single code point letters are not boxed into a single-item letter sequence (this feels like too much unnecessary data bloat as this is the majority case). The data structure supports alphabets of alphabets (eg. could combine cases, or separate out Indic consonants and dependent/independent vowels), but current codegen does not do this.
 - Use the `source_id` field to determine where the alphabet comes from. The code loads alphabets from three sources: Manually specified, [CLDR data](https://cldr.unicode.org/) and automatically generated (from the same process that does Brahmi and Semitic letters).
    - Note that CLDR data only covers modern languages. The data are loaded as "extended" alphabet types from CLDR's main exemplar set. Abjad and Alphabet type scripts further have "basic" types loaded from the index set (these tend to be underspecified for logographs, syllabaries and probably abugidas too - dependent vowels usually being missing). Note that CLDR does tend to follow the language's alphabet order, but sometimes the accented characters are grouped together (which may or may not be how a language typically orders letters).
    - I have yet to decide what precisely to do with the Chinese language(s). CLDR has separately specified Traditional and Simplified characters, but in the Unicode character database they are under a single script code.
 - At present, the data is largely unverified.
 - **Design considerations.** This table was simultaneously the most subjective and least important for this project. The codegen loads only "letters", but symbols could in principle be supported by the data structure.
    - The definition leads to the PK `(lang_code, sequence_id)`. However, to keep things simple, this table has been de-normalized (again this is not an important part of the DB and is subjective and can change so avoiding possibly over-engineering in the wrong direction). The PK is extended with `type_id` which in a normalized context should be specified in a separate many:1 table against the proper PK (I figure the `source` field would also go in that table, leaving remaining fields with the original table).
    - The `script_code` and `letter_case` may at first glance seem inferable from the referenced sequence id, but consider potential alphabets with mixed case or mixed script. It needs to be possible to make a manual determination for the overall case/script even if the sequence contains exceptions.
    - There is no current support for designating historical versions of alphabets. For historical languages/scripts, any included alphabet is interpreted as the most recent possible.
    - The design intends for `(lang_code, type_id, script_code, letter_case)` to be able to specify a singular sequence assuming such a sequence exists (the real world is messier with uncertainty, but the design calls for making a choice). In many cases this will be overspecifying (uncased languages, languages only ever written in a singular script, etc.), but a unique key has been added to represent this.

### `certainty_type`

Certainty is a measure of the strength of evidence for a derivation used on the `code_point_derivation` table. As a visualization (and as planned for the front end), a derivation can be envisioned as an arrow from parent to child and that arrow can be a solid, dashed or dotted line in order of decreasing evidence strength. The IDs are:

 - ID -1 *Unspecified (dotted)*: This is considered a missing data error.
 - IDs 1-3 are the straightforward *Near Certain*/*Likely*/*Uncertain* with corresponding arrows.
 - IDs 4-5 are the "assumed" types where there is no specific source, but has been derived by the database author for one reason or another (it is considered a data error for all the other IDs to not have an entry in `derivation_source`). If a source is provided anyways for these derivations, it is informative or tangential, but not direct.
    - ID 4 *Strong Assumption (dashed)*: There are two "default" reasons for a strong assumption (and are permitted to have a null `notes` field). To a large extent, the purpose of this ID existing is to compensate for the fact it's hard to find sources for such obvious derivations.
        - A child script with strongly matching glyph and sound (or function for unpronounced characters like punctuation).
        - A glyph that is a transparent combination of one or more same-script glyphs (eg. letter + minor modification such as addition of diacritic, lowercase being small uppercase, ligatures, etc.). In specifying this kind of derivation, care should be taken to ensure that the same transparent combination did not first occur in a parent script (and so the child script inherited this derivation rather than creating it itself).
        - If there is another reason (eg. a documented sound shift occurred, or follows a general pattern of glyph changes), this must be explained in the `notes` field.
    - ID 5 *Weak Assumption (dotted)*: It is considered a data error to not have a justification in the `notes` field.
 - IDs 6+ represent an automated derivation from a data source. Technically this is a bit de-normalized as it applies to an entire source (set of code points) rather than the specific code points on the record.
    - ID 6 *From Technical Source (solid)* represents a technical derivation source, the prime example being Unicode decomposition. These aren't really separate characters from an epigraphic standpoint, just different ways of encoding characters in Unicode, and so are derived by definition.
    - ID 7 *From Non-Graphical Source (dashed)* is a derivation from a non-graphical source, but is highly correlated with graphical derivation. Examples are upper/lowercase forms, cognate letters in the Indic & Semitic scripts and various patterns inferred from code point names.
    - There are currently no other IDs. Notably absent is any automated source that details specifically graphical derivation. The database author has simply not yet found any that was worth automatic parsing (part of the reason for this database; naturally many individual sources exist and are categorized under IDs 1-3). IDs may later be added for this purpose, but ideally such a source could instead be mapped onto IDs 1-3.

### `code_point`

Mostly what you would expect from Unicode.

 - Non-character U+FFFF is used as a signal value for when a character has been evaluated to have no known ancestor (to distinguish it from the case where data is simply missing).
 - Private use characters are used for historical scripts not yet in Unicode proper. For the Brahmi-based scripts, adding these characters is a partially automated process which may not be 100% accurate.
 - Field `equivalent_sequence_id` combines various Unicode sources for "equivalent" code points and some custom equivalency. May have to change later, but as it stands these sources do not overlap. These are decomposition (including Hangul Syllable/Jamo), z-variants (the lowest code point in a set has been taken to be the original) and Hieroglyph alternate sequences (kEH_AltSeq). The custom equivalency is positional equivalence, for when a Unicode characters is the same graphical character but has technical or positional distinction (so far two sub-categories: combining marks existing as stand-alone/modifiers and Hangul initial/final consonants).

### `code_point_derivation`

This is the main table for this project, mapping out the historical derivations of characters. In an ideal world, all characters would be manually reviewed. Last I checked, that was not the case. So, a sizable proportion are automatically generated from various data sources. For certainty, manually specified data will always override automatic data source. This table is also liable to rename to `code_point_relation` if project scope expands.

  - The `derivation_type_id` borders on legacy. However, there's not really any reason to drop it formally, most new data is simply taking the default value without breaking anything.
  - `certainty_type_id`: see `certainty_type` table. (trivia - the derivation and certainty types essentially swapped places in terms of usefulness and the database author's initial anticipation of their usefulness).
  - The automatic derivations are:
     - An assumption that lowercase characters derive from their uppercase counterparts.
     - For the Brahmi-derived and Semitic scripts, it is assumed that cognate letters derive from their known ancestor script.
     - Independently originated scripts have all their letters set to have no historical ancestor (this isn't necessarily always true as there can be script-internal derivation!).
     - Simplified Chinese characters deriving from their Traditional counterpart.
     - Unicode decompositions (eg. accented characters, duplicate/legacy code points, etc.).
     - Hangul syllables deriving from their constituent jamo.
     - *(to investigate data sources and history)* Han ideograph and radical relations.

### `derivation_source`

Cross-reference table between `code_point_derivation` and `source`. The `section` field is a free-text field intended for referring to a location within the source, not necessarily a literal "section." This table is also liable to rename to `relation_source` if project scope expands.

### `language`

Loaded mainly from the IANA language subtag registry (see licence info in README). This source was preferred over ISO 639 due to friendlier licensing and closer alignment with CLDR (I'm sure the codes mostly match anyways). The `default_script_code` field is supplemented by CLDR data if missing from IANA.

### `script`

A manually maintained table. Started out based on the list found [here](https://www.unicode.org/iso15924/iso15924-codes.html).

  - To my understanding, the original source table having rows without a Unicode Alias yet having a Unicode version date are scripts which Unicode considers a font variant of another. This was marked with the `canonical_script_code` field, but the usefulness is questionable.
  - The `exemplar_sequence_id` field references a canonical set of letters. Associating to a sequence and not an alphabet allows for language-independence (eg. could be useful for Cyrillic where there isn't a universally agreed set of canonical letters). A sequence has been manually specified for a few scripts. However, most are specified with a "automated" process of specifying the main language for a script, which then pulls in the sequence generated from that language's alphabet (see `alphabet` table).
     - For the most part, determining the main language was not difficult. Canadian Aboriginal syllabics was the main judgment call: It could have been Ojibwe, Cree, or Inuktitut. Ojibwe syllabics was not in the CLDR data leaving Cree and Inuktitut. In CLDR, only Swampy Cree specifically was in the files, which would be much fewer speakers than Inuktitut. However, between considering Cree more widely and that Inuktitut discarded the distinct final consonants (and this project is for finding interesting graphical developments), I've associated it to Swampy Cree.
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

A sequence of sequences (recursive tree). Each code point also has an "dummy" base entry sequence in the table, with a matching ID. Use the `type_id` field to determine what kind of sequence you are looking at.

### `sequence_item`

An item in a sequence. The base code point sequences do *not* have an entry in this table, they are the leaf items in the tree.

### `source`

Provides reference sources. Note this is far from the highest academic rigour, it is mainly to provide at least a minimum level of traceability.
