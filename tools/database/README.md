*Disclaimer: Software is provided as-is. The author takes no responsibility for ill-effects from use of said software.*

***Note:*** *This database is in beta. Expect breaking changes. After a few weeks of development, I finally have an idea for a front-end to this thing and am starting to develop in support of that.*

## Overview

This is a `sqlite3` database with script and character information, whose main purpose is to document historical development of writing on the individual character level. This started out as an exploration on updating the All Scripts chart with script samples that could show character development over time (objective not yet complete or even known to be feasible).

There are three queries that I wanted to answer with the database:

  - What are a given character's ancestors? *(done!)*
  - What are a given character's descendants? *(done!)*
  - Given a script, what are its immediate parent scripts, and in what proportions? This is to help with the chart derivations. *(query done, but the data is a bit rough)*
  - A fourth query could be a script's immediate children, but I'm not sure how much this adds on top of the other queries.

Though there are no current plans, the functionality of the database could be extended beyond historical character relationships in the future (if you have any interesting ideas, ideally either not done elsewhere and/or fits neatly with current DB schema, ping me either here on GitHub or [on Reddit](https://www.reddit.com/user/DPenner1/)).

## Statistics

*As of 2026-03-15*

  - *(Just over 100,000 letters in the Unicode Standard are Chinese characters. These stats are notated "All / non-Chinese")*. There are ⁨130,811 / 29,873 distinct<sup>1</sup> letters<sup>2</sup> in the database. Of those, 29,282 / 22,799 have a historical ancestor specified (22.2% / 76.3%, including no known ancestor), of which 1879 / 1840 are manually reviewed (1.4% / 6.2%).
  - The database is about 21 MB with minimalistic settings (configurable to keep more data/indexes).

  1. Distinct being defined for this project has having no other equivalent representation in Unicode. See schema documentation on `code_point.equivalent_sequence_id`.
  2. Letters for this project being defined as Unicode "Alphabetic" property plus the Private Use letters which currently stands at 417 (+79 non-letter characters).

## Getting Started

The database must be generated. For all purposes, the `./tools/database` folder is the working directory (while I am Linux-based, this should also work on Windows, but I have not tested this).

  1. The database is generated using Python 3, with only standard modules plus `sqlite3` (which is an optional module possibly already included in a given installation).
  4. Generate the database by running the `./scriptdb.py` script. There was some logic for the script to try and work with an existing database, but at present this is unlikely to work. This may be revisted.
  5. The database `./scripts.db` appears (or is updated)! You can now run queries as you like from `sqlite3`. Alternatively, include some code at the end of `./scriptdb.py` or `import scriptdb` into your own Python code. But I guess that should've been done before step 2. Oops.

The [`./queries`](https://github.com/DPenner1/WritingSystemHistory/tree/main/tools/database/queries) folder contains some queries, including finding a character's ancestors and descendants. Queries suffixed with `p` are parameterized, either replace the `?`(s) or call from code with parameters. Queries suffixed with `s` or `d` are called internally by the database setup code, the latter only with certain debug flags.

For details, see the Schema documentation file.

## Random Notes

  - Character is a fuzzy term and does not necessarily equate to a code point. For simplicity, this project has started out as code points. In principle, a character could be multiple codepoints. In that case, historical derivations are still quite supported as you would just combine the derivations of the constituent code points. It's a bit imprecise, but so far I'm not bothered by it. In the future, derivations could be associated to sequences if deemed necessary.
  - There are a decent number of defaults and fallbacks in the source to avoid repetitively specifying stuff in source files.
  - I have in usually been lazy with csv quoting and avoided commas in the data. I'm using python csv reader, so this is pure laziness as quotes would be no issue.

## Licence info

This project contains resources from some openly licensed sources.

  - The database is generated from some files the [Unicode Consortium](https://home.unicode.org/). Unicode licence is at [`./resource/unicode-data/license.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/unicode-data/license.txt)
  - The database is generated using some text sourced from Wikipedia, which is under CC BY-SA 4.0. For compliance, and further info on that see in this project [`./resource/wikipedia-sourced/licence-info.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/wikipedia-sourced/licence-info.txt).
  - The database makes use of the [IANA/IETF Subtag Language Registry](https://www.iana.org/assignments/language-subtags-tags-extensions/language-subtags-tags-extensions.xhtml#language-subtags), which is [essentially public domain](https://www.iana.org/help/licensing-terms):

I intend to more formally put the database and the Python generation code under an open licence. The planned front-end will also likely be assuming I stick with current plans to use open source.
