*Disclaimer: Software is provided as-is. The author takes no responsibility for ill-effects from use of said software.*

***Note:*** *This database is in beta. Expect breaking changes.*

## Overview

This is a `sqlite3` database with script and character information, whose main purpose is to document historical development of writing on the individual character level. This started out as an exploration on updating the All Scripts chart with script samples that could show character development over time (objective not yet complete or even known to be feasible).

In principle, there are a few neat queries that could be answered with the database (functionality yet to be written):

  - Given a script, what are its ancestor scripts, and in what proportions?
  - Given a character, what are its descendents and ancestors?

Though there are no current plans, the functionality of the database could be extended beyond historical character relationships in the future (if you have any interesting ideas, ideally either not done elsewhere and/or fits neatly with current DB schema, ping me either here on GitHub or [on Reddit](https://www.reddit.com/user/DPenner1/).

## Getting Started

The database must be generated. For all purposes, the `./tools/database` folder is the working directory (while I am Linux-based, this should also work on Windows, but I have not tested this).

  1. The database is generated using Python 3, with only standard modules plus `sqlite3` (which is an optional module possibly already included in a given installation).
  4. Generate the database by running the `./main.py` script. There is some logic for the script to try and work with an existing database, but there is no guarantee and you may have to delete the existing first. If the schema does not change though, it should just run a data update without issue.
  5. The database `./scripts.db` appears (or is updated)! You can now run queries as you like from `sqlite3`. Alternatively, include some code at the end of `./main.py`. But I guess that should've been done before step 2. Oops.

## Schema/data documentation

  - `code_point`: Generally what you would expect from Unicode. Non-character U+FFFF is used as a signal value for when a character has been evaluated to have no known ancestor (to distinguish it from the case where data is simply missing). *(planned)* Private use characters are used for historical scripts not yet in Unicode proper.
  - `code_point_derivation`: This is the main table for this project, mapping out the historical derivations of characters. In an ideal world, all characters would be manually reviewed. Last I checked, that was not the case. So, a sizable proportion are automatically generated from various data sources. For certainty, manually specified data will always override automatic data source. These automatic derivations are:
     - An assumption that lowercase characters derive from their uppercase counterparts.
     - The Brahmi-derived scripts have a decently documented history, it is assumed that cognate letters derive from their known ancestor script.
     - Independently originated scripts have all their letters set to have no historical ancestor (this isn't necessarily always true as there can be script-internal derivation!)
     - Simplified Chinese characters deriving from their Traditional counterpart.
     - Unicode decompositions (eg. accented characters, duplicate/legacy code points, etc.).
     - *(planned)* Hangul syllables deriving from their constituent jamo.
     - *(to investigate data sources)* Han ideograph and radical relations.
  - `decomposition_mapping`: Unicode decompositions, in this project this was just an interim table from which to create automatic derivations.
  - `script`: Based on ISO 15924, but I'm likely to re-organize it later to deal with differences between what ISO supports, what Unicode supports, and the historical scripts neither has yet.

## Statistics

  - (2026-02-24) There are 141,295 distinct letters in the database (defined as Unicode general category L* and having no Unicode decomposition). Of those, 27,064 have a historical ancestor specified (19.2%, including no known ancestor), of which 556 are manually reviewed (0.4%).

## Random Notes

  - There are some significant gaps in the data at the moment.
  - Character is a fuzzy term and does not necessarily equate to a code point. For simplicity, this project has started out as code points. In principle, a character could be multiple codepoints. In that case, historical derivations are still quite supported as you would just combine the derivations of the constituent code points. Less well supported would be the case when such a sequence of code points constituting a character is an ancestor character to another. This is anticipated to be rare (maybe non-existant?).
  - While the database as a whole is in beta, the implementation of standard alphabets is especially questionable. At present, it is mostly there for feedback purposes: running the script in dev mode lets me check for important data gaps with it. I'll be looking at integrating CLDR data for this at some point
  - There are a decent number of defaults and fallbacks in the source to avoid repetitively specifying stuff in source files.
  - I have in general been lazy with csv quoting and avoided commas in the data. I'm using python csv reader, so this is pure laziness as quotes would be no issue.

## Licence info

This project contains resources from some openly licensed sources.

  - The database is generated from some files the [Unicode Consortium](https://home.unicode.org/). Unicode licence is at [`./resource/unicode-data/license.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/unicode-data/license.txt)

  - The database is generated using some text sourced from Wikipedia, which is under CC BY-SA 4.0. For compliance, and further info on that see in this project [`./resource/wikipedia-sourced/licence-info.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/wikipedia-sourced/licence-info.txt).
