*Disclaimer: Software is provided as-is. The author takes no responsibility for ill-effects from use of said software.*

***Note:*** *This database is in beta. Expect breaking changes.*

## Overview

This is a `sqlite3` database with script and character information, whose main purpose is to document historical development of writing on the individual character level. This started out as an exploration on updating the All Scripts chart with script samples that could show character development over time (objective not yet complete or even known to be feasible).

In principle, there are a few neat queries that could be answered with the database (functionality yet to be written):

  - Given a script, what are its ancestor scripts, and in what proportions?
  - Given a character, what are it's descendents and ancestors?

For technical reasons, it is essentially limited to characters present in Unicode. Though there are no current plans, the functionality of the database could be extended beyond historical character relationships in the future.

## Getting Started

The database must be generated (~12MB). For all purposes, the `./tools/database` folder is the working directory (while I am Linux-based, this should also work on Windows, but I have not tested this).

  1. The database uses some Unicode Character Database files in its generation. Per [Unicode copyright licence](https://www.unicode.org/copyright.html), they are not included in this project. You must copy them into `./cr-exclusion`. From the (https://www.unicode.org/Public/UCD/latest/ucd/) copy the following:

     - `UnicodeData.txt`
     - `Scripts.txt`
     - The `Unihan_Variants.txt` file from the `Unihan.zip`

  3. The database is generated using Python 3, with only standard modules plus `sqlite3` (which is an optional module possibly already included in a given installation).
  4. Generate the database by running the `./main.py` script. There is some logic for the script to try and work with an existing database, but there is no guarantee and you may have to delete the existing first. If the schema does not change though, it should just run a data update without issue.
  5. The database `./scripts.db` appears (or is updated)! You can now run queries as you like from `sqlite3`. Alternatively, include some code at the end of `./main.py`. But I guess that should've been done before step 3. Oops.

## Random Notes

  - I do intend on documenting this better.
  - There are some significant gaps in the data at the moment.
  - A large proportion of the derivations are algorithmically generated from sources. These aren't perfect. Ideally they would eventually be manually reviewed (but who has time for that?).
  - While the database as a whole is in beta, the implementation of standard alphabets is especially questionable. At present, it is mostly there for feedback purposes: running the script in dev mode lets me check for important data gaps with it.
  - There are a decent number of defaults and fallbacks in the source to avoid repetitively specifying stuff in source files.
  - I have in general been lazy with csv quoting and avoided commas in the data. I'm using python csv reader, so this is pure laziness as quotes would be no issue.

## Licence info

The database is generated using some text sourced from Wikipedia, which is under CC BY-SA 4.0. For compliance, and further info on that see in this project [`./resource/wikipedia-sourced/licence-info.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/wikipedia-sourced/licence-info.txt).
