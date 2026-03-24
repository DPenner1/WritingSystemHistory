*Disclaimer: Software is provided as-is. The author takes no responsibility for ill-effects from use of said software.*

***Note:*** *This database is in beta. Expect breaking changes. After a few weeks of development, I finally have an idea for a front-end to this thing and am starting to develop in support of that.*

## Overview

This is a `sqlite3` database with script and character information, whose main purpose is to document historical development of writing on the individual character level. This started out as an exploration on updating the All Scripts chart with script samples that could show character development over time (objective not yet complete or even known to be feasible).

There are three queries that I wanted to answer with the database:

  - What are a given character's ancestors? *(done!)*
  - What are a given character's descendants? *(done!)*
  - Given a script, what are its immediate parent scripts, and in what proportions? This is to help with the chart derivations. *(query done, but the data is a bit rough - see alphabet in the schema documentation below)*
  - A fourth query could be a script's immediate children, but I'm not sure how much this adds on top of the other queries.

Though there are no current plans, the functionality of the database could be extended beyond historical character relationships in the future (if you have any interesting ideas, ideally either not done elsewhere and/or fits neatly with current DB schema, ping me either here on GitHub or [on Reddit](https://www.reddit.com/user/DPenner1/)).

## Statistics

*As of 2026-03-15*

  - *(Just over 100,000 letters in the Unicode Standard are Chinese characters. These stats are notated "All / non-Chinese")*. There are ⁨130,804 / 29,866 distinct<sup>1</sup> letters<sup>2</sup> in the database. Of those, 29,282 / 22,786 have a historical ancestor specified (22.2% / 76.3%, including no known ancestor), of which 1871 / 1832 are manually reviewed (1.4% / 6.1%).
  - The database is about 20 MB with minimalistic settings (configurable to keep more data/indexes).

  1. Distinct being defined for this project has having no other equivalent representation in Unicode. See schema documentation on `code_point.equivalent_sequence_id`.
  2. Letters for this project being defined as Unicode "Alphabetic" property plus the Private Use characters which currently stands at 410 (+79 non-letter characters).

## Getting Started

The database must be generated. For all purposes, the `./tools/database` folder is the working directory (while I am Linux-based, this should also work on Windows, but I have not tested this).

  1. The database is generated using Python 3, with only standard modules plus `sqlite3` (which is an optional module possibly already included in a given installation).
  4. Generate the database by running the `./scriptdb.py` script. There was some logic for the script to try and work with an existing database, but at present this is unlikely to work. This may be revisted.
  5. The database `./scripts.db` appears (or is updated)! You can now run queries as you like from `sqlite3`. Alternatively, include some code at the end of `./scriptdb.py` or `import scriptdb` into your own Python code. But I guess that should've been done before step 2. Oops.

The [`./queries`](https://github.com/DPenner1/WritingSystemHistory/tree/main/tools/database/queries) folder contains some queries, including finding a character's ancestors and descendants. Queries suffixed with `p` are parameterized, either replace the `?`(s) or call from code with parameters. Queries suffixed with `s` or `d` are called internally by the database setup code, the latter only with certain debug flags.

## Schema/data documentation

  - `alphabet`: *(schema relatively stable, but data/codegen is not)* Data on alphabets used by various languages, with the specific letters being stored in the referenced `sequence` table. While it might seem like overkill (and probably still is), this table is to help determine the "canonical" letters for a script.
     - Languages with a case distinction have entries for both lower case and upper case.
     - The design was based on considering an alphabet to be "a meaningful collection of characters associated to a language" to not be too restrictive.
     - Alphabets are represented as a sequence of letters and code points, with letters themselves being sequences of code points. Currently, single code point letters are not boxed into a single-item letter sequence (this feels like too much unnecessary data bloat as this is the majority case), but this may change if the structure ends up being too difficult to work with.
     - Use the `source` field to determine where the alphabet comes from. The code loads alphabets from three sources: Manually specified, [CLDR data](https://cldr.unicode.org/) and automatically generated (from the same process that does Brahmi and Semitic letters).
         - Note that CLDR data only covers modern languages. Also note that the CLDR data isn't necessarily a "canonical" alphabet: (1) It generally includes the typical accented characters in a language even if the language typically considers them non-distinct letters. (2) It does generally tend to follow the language's alphabet order except that the accented characters are grouped together (which may or may not be how a language typically orders letters).
         - Manually specified and CLDR data can co-exist, but the code will not load a generated alphabet if one of these two exist.
     - The `is_language_exemplar` field is to determine which alphabet is the main one for a given language. For CLDR, this is mechanically determined based on CLDR leaving off a script in the filename and is the upper case one for cased scripts.
        - For Japanese I've set it to Kanji (Han characters) as it felt weird favouring a kana alphabet.
        - I have yet to decide what precisely to do with the Chinese language(s). CLDR has separately specified Traditional and Simplified characters, but in the Unicode character database they are under a single script code.
        - The equivalent script exemplar field is on the `script` table. There is no language table, otherwise the language exemplar would be there. A slight distinction is made that the script exemplar is associated to a sequence rather than the alphabet. This allows it to be associated language-independently in the future (eg. could be useful for Cyrillic where there isn't a universally agreed set of canonical letters).
        - Canadian Aboriginal syllabics was the main judgment call: It could have been Ojibwe, Cree, or Inuktitut. Ojibwe syllabics was not in the CLDR data leaving Cree and Inuktitut. In CLDR, only Swampy Cree specifically was in the files, which would be much fewer speakers than Inuktitut. However, between considering Cree more widely and that Inuktitut discarded the Pitman Shorthand derived letters (and this project is for finding interesting graphical developments) I've associated it to Swampy Cree.
     - At present there's no functionality for sub-languages. Eg. It could be useful to have a search for code `cr` (Cree) return results for `csw` (Swampy Cree) since `cr` isn't in the data files, but this feels like too much effort for too little gain on this project's goals.
  - `code_point`: Mostly what you would expect from Unicode.
     - Non-character U+FFFF is used as a signal value for when a character has been evaluated to have no known ancestor (to distinguish it from the case where data is simply missing).
     - Private use characters are used for historical scripts not yet in Unicode proper. For the Brahmi-based scripts, they've been automatically generated and assumed to exist if 50%+1 of their descendents have the corresponding letter. It should not be assumed the particular code points used are stable.
     - Field `equivalent_sequence_id` combines various Unicode sources for "equivalent" code points. May have to change later, but as it stands these sources do not overlap. These are decomposition (including Hangul Syllable/Jamo), z-variants (the lowest code point in a set has been taken to be the original) and Hieroglyph alternate sequences (kEH_AltSeq). One further custom equivalency is added for this project: positional equivalence, for when a Unicode characters is the same graphical character but has technical or positional distinction (so far two categories: combining marks existing as stand-alone/modifiers and Hangul initial/final consonants).
  - `code_point_derivation`: This is the main table for this project, mapping out the historical derivations of characters. In an ideal world, all characters would be manually reviewed. Last I checked, that was not the case. So, a sizable proportion are automatically generated from various data sources. For certainty, manually specified data will always override automatic data source. This table is also liable to renaming to `code_point_relation` if project scope expands. The automatic derivations are:
     - An assumption that lowercase characters derive from their uppercase counterparts.
     - For the Brahmi-derived and Semitic scripts, it is assumed that cognate letters derive from their known ancestor script.
     - Independently originated scripts have all their letters set to have no historical ancestor (this isn't necessarily always true as there can be script-internal derivation!).
     - Simplified Chinese characters deriving from their Traditional counterpart.
     - Unicode decompositions (eg. accented characters, duplicate/legacy code points, etc.).
     - Hangul syllables deriving from their constituent jamo.
     - *(to investigate data sources and history)* Han ideograph and radical relations.
  - `script`: ISO 15924. A bit of a mish-mash, but works so far. Table based on list found [here](https://www.unicode.org/iso15924/iso15924-codes.html). To my understanding, rows without a Unicode Alias yet having a Unicode version date are scripts which Unicode considers a font variant of another. This was marked with the `canonical_script_code` field.
     - The `exemplar_sequence_id` field references a canonical set of letters.
     - The table is then augmented with private use scripts with a `u_name` specified. These are:
        - Proto-Sinaitic
        - Pallava
        - Kadamba
        - Landa
        - Nagari
        - Gaudi
        - Gupta
        - Demotic (subset)
        - *(future possible subset of)* Pitman Shorthand
  - `sequence`: A sequence of sequences (recursive tree). Each code point also has an "dummy" base entry sequence in the table, with a matching ID. Use the `type_id` field to determine what kind of sequence you are looking at.
  - `sequence_item`: An item in a sequence. The code points sequences do *not* have an entry in this table, they are the leaf items in the tree.
  - The `*_type` tables are lookup tables that should be self-explanatory based on their data.

## Random Notes

  - Character is a fuzzy term and does not necessarily equate to a code point. For simplicity, this project has started out as code points. In principle, a character could be multiple codepoints. In that case, historical derivations are still quite supported as you would just combine the derivations of the constituent code points. It's a bit imprecise, but so far I'm not bothered by it. In the future, derivations could be associated to sequences if deemed necessary.
  - There are a decent number of defaults and fallbacks in the source to avoid repetitively specifying stuff in source files.
  - I have in usually been lazy with csv quoting and avoided commas in the data. I'm using python csv reader, so this is pure laziness as quotes would be no issue.

## Licence info

This project contains resources from some openly licensed sources.

  - The database is generated from some files the [Unicode Consortium](https://home.unicode.org/). Unicode licence is at [`./resource/unicode-data/license.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/unicode-data/license.txt)

  - The database is generated using some text sourced from Wikipedia, which is under CC BY-SA 4.0. For compliance, and further info on that see in this project [`./resource/wikipedia-sourced/licence-info.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/wikipedia-sourced/licence-info.txt).

I intend to more formally put the database and the Python generation code under an open licence. The planned front-end I'm less sure about.
