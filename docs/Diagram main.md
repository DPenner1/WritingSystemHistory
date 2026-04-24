# Script Inclusion Criteria

Generally, in order to be included, the script must be able to fully or almost fully represent a spoken language. Having this limit is really the only feasible way to semi-objectively have a manageable diagram.

There is also the question of what counts as separate scripts. Basically, the written version of "[A language is a dialect with an army and navy.](https://en.wikipedia.org/wiki/A_language_is_a_dialect_with_an_army_and_navy)" There's not a great answer to this, but for these diagrams, it is an extremely strong indicator that if Unicode considers one script to be a font variant of another, then they will be considered as a singular script.

There also exists a bit of a middle ground: Unicode may consider some grouping as a singular script, but the characters may be in distinct "sets" which are culturally treated as distinct scripts. A good example of this is the [Georgian scripts](https://en.wikipedia.org/wiki/Georgian_scripts) which are under a singular script code in Unicode, but each cultural script is given their own separate distinct letters (and so are *not* font variants). That said, a few extra letters added on to a script (common for adapting an alphabet to a new language) will not constitute an entirely new script.

The All Scripts diagram partially gets around this by having timeline boxes so that distinct stages of a script can be shown together. This arguably punts the question down as to what constitutes separate stages, but so far this has been rather intuitive (perhaps there's some unconscious bias, but I've generally not felt there to be any difficult decisions here).

## Modern Scripts Inclusion Criteria

For space and sanity, some scripts have to be left out. In order to have semi-objective criteria for this, here's what I've landed on for the Modern Scripts diagram:

  1. **Currently used** writing scripts are included if they are:
     1. In Unicode, _and_
     2. In some natural non-moribund use. By "natural," this is meant to exclude new creations or revival attempts which are too recent to judge successful.
  2. **Historical scripts** are included if they are:
     1. An earliest known ancestor of a currently used script, _or_
     2. An intermediate ancestor that has more than one distinctly named descendent included on the diagram. Examples for this are:
         1. The script lineage of Sukhothai > Fakkham > Tai Noi > Lao. Fakkham and Tai Noi are excluded as they don't branch off anywhere else on the diagram, but Sukhothai remains as it branches to Thai and Tai Viet.
         2. The Telugu-Kannada script only branches into Telugu and Kannada, so is excluded.

Naturally, there's a judgment call here, made worse by the fact scripts on the boundary of inclusion/exclusion are also lesser known and hard to research. Most marginal inclusions/exclusions were due to this boundary.

## All Scripts Inclusion Criteria

In the All Scripts diagram, inclusion criteria turned out to be much less of an issue. It starts by including all Unicode scripts and then including all non-Unicode historical ancestors (as per Wikipedia) by default. A few non-branching historical ancestors then get excluded for space reasons (I only recall excluding Tai Noi, an intermediate between Fakkham and Lao).

A few detail notes:

  - Non-Unicode Maya and Indus scripts are exceptionally included for historical significance, though admittedly the latter is not yet determined to be a full-fledged writing script. Honestly if I started from scratch again, I would not include Indus to avoid the exception, but Maya can fairly be included as one of three fully accepted inventions of the *idea* of writing (modern scholarship usually accepts four). It just seems overly aggressive to remove it now. It can be retconned as "the earliest scripts in each region also get included."
  - At discretion, scripts planned for the next version of Unicode may also be included, along with the relevant historical ancestors (generally when batching major changes together).
  - Non-Unicode descendents should be included for historical Unicode scripts for the sole purpose of not misleadingly showing a script going extinct early. This currently does not occur on the diagram.

# Qualifying Derivations

Sometimes scripts incorporate letters from multiple other scripts. In order to count as a derivation, the amount of borrowed letters should be at least 20%. This percentage was derived from the Coptic borrowing of Demotic letters and hence ultimately Egyptian Hieroglyphic characters. I wanted this on the diagram as it appears to constitute the only *current* use of Egyptian Hieroglyph derived characters outside of the Proto-Sinaitic branch. In the future, this rule could be modified a bit taking into account that earlier Coptic retained more Hieroglyph derived characters.

For partial independent creation, a higher percentage was needed to keep the distinction useful (20% just results in way too many scripts qualifying). All new scripts add something novel (otherwise they wouldn't be a different script), so it's already implied there's some independent innovation (whether gradual or deliberate). At present there's no fixed minimum percentage of independently created letters for this to count. However, based on current analysis from the beta database project, there seems to be a gulf between 30%-70% that very few scripts fall into (and none in current data, though data is still being loaded and must be interpreted).

While the database project is still beta state, the process for computing this percentage is:

  1. Take a set of letters regarded as "standard" for a script.
  2. Filter out the letters that are missing data.
  3. For each letter, get the script(s) of the letter's immediate ancestor.
  4. Recursively apply the previous step if it resulted in script-internal derivation (eg. Latin G derives from Latin C, so we reach back further to Old Italic C (one step further back would be Greek gamma)).
  5. For the candidate ancestor script, divide its total number of letters by the total number of letters from step 2. Note: each letter is weighted equally (which results in letters with multiple parents, eg. ligatures, having each parent count as a fraction). Some interpretation is currently required for this step as the DB doesn't distinguish well between having multiple real parent letters or multiple potential parent letters due to historical uncertainty.

# Disputed Derivations

On Modern Scripts, any qualifying derivation is shown with dotted lines if reasonably disputed in academic sources. If this dispute would affect the designated group (colour) of the script, then that colour is determined in the same way as in the All Scripts chart with one exception.

On All Scripts, showing all disputed derivations would be far too messy, so a singular choice is made. The choice is made generally taking into account the following:

  1. Favour clear majority academic opinion.
  2. Favour proper derivation over independent creation.
      - Exceptionally, the script may be shown as both. This is generally done when the data is incredibly unclear and/or a significant amount of independent creation occurred anyways (even if it doesn't meet the normal qualifying threshold). This currently applies to Hangul and Yezidi, with Georgian being potentially added pending further research.
  3. If the dispute is of the form (A->C) vs (A->B->C) this is a judgment call based on competing factors:
      - Parent A would be preferred as its not incorrect, just less specific.
      - If B is generally considered a minor or intermediary script, then one would expect sources to not always mention it, so the more specific B would be preferred.
  4. If all else fails, just pick the one that visually works best (generally when sibling branches originate around the same time).

The exception for Modern Scripts is when under point 1, independent creation is chosen. Unlike All Scripts, because Modern Scripts shows disputed arrows it looks like an awkward mistake to show pure independent creation. So the group colour must additionally be added.

# Minor notes

  - The specific symbols used to identify writing system type were mostly chosen by taking the largest system of that type and simply finding something that worked with the font I was using.
       - Naturally with Latin, I needed a non-Latin looking symbol due to the chart being in Latin script itself. Greek Omega was chosen due to recognizability, distinctness, and being the originator of that group of scripts.
       - The Arabic character chosen is actually a regional one. I was not aware of this at the time and this will probably change in the future to be more representative.
  - Some scripts have multiple possible writing directions or are difficult to categorize. There are multiple symbols for these, I attempted to list the most dominant first. For a few scripts written and read in separate directions (eg. Tagbanwa, Hanuno'o), the reading direction is listed first.
  - There was effort to place independent scripts near related scripts. For the Modern diagram, this is linguistic similarity, for the All Scripts diagram this is more geographic.
  - The script groups in the legend are ordered by a rough estimate of total population using them.
  - I generally went with Wikipedia's article title for the name of the scripts, though there were some exceptions, particularly where Unicode had a distinct name for it (space permitting). Preferring Wikipedia over Unicode here is due to Unicode script names being permanent, so may not reflect current terminology.
  - While researching, there were two big gotcha's to be aware of: Many scripts have the same name as the corresponding language, so had to be careful it was specifically the script that was being mentioned in the source. Second, for related scripts, sources would mention an Old or Proto script, eg. proto-Bengali, proto-Odia, etc., based on whichever script they were talking about. However it's important to note that sometimes these different names are actually referring to essentially the exact same script before the child scripts became distinct scripts.
  - The italics for designating scripts not in Unicode might be a bit misleading. Per top section, Unicode may consider culturally distinct scripts to be font variants of the overall same script. So in this case the diagrams do not italicize. In many cases though, this is ambiguous.

## All Scripts minor notes

  - Dates before 1800 in particular are frequently not known with absolute precision and might commonly have an acceptable range of a century, sometimes two. Part of this is lack of historical/archaeological record, and part of this is that scripts tend to gradually evolve so an absolute date is a bit nebulous. Unless I could find more specific text, when Wikipedia said something like "5th century," I by default put it in the middle of the century, so 450. I did the same for info-box dates like "c. 800" as I found this tended to be said as 9th century in the article text, so I moved it up to 850 in the diagram. End dates are particularly nebulous. If only one person is using the script, surely we won't consider it in active use, but how many does it take?
  - For determining dates, physical evidence is persuasive, but not final. In particular it is possible that scholarly consensus has script B deriving from script A, yet earlier physical samples from B are lacking. This would cause problems for the diagram if we purely went by physical evidence as we would apparently be making a derivation backwards in time. While there's not a direct example of this on the graph, this partially impacted Psalter Pahlavi (as letters were borrowed into Avestan) and certain derivation schemes of the Kawi group possibly would have resulted in that.
  - Lowercase development is shown in Greek & Latin due to these being significant graphical developments of the script (as is the purpose of this diagram). This isn't special treatment. Best I can tell, all other scripts with a case distinction either have mostly non-graphically distinct letter cases (lowercase is just small uppercase) or the cases appeared at the same time (within the timescale resolution), so is not a distinct evolution of the script.
  - Geography: The scripts are placed in regions (as defined by the Wikipedia articles) according to their place of origin, with reference to modern borders to keep things consistent. Based on script evolution, it was far easier to group Anatolian & Caucasian scripts with Europe (and under some definitions, part of the Caucasus is in Europe anyways). Central Asia is grouped with East Asia for two main reasons: it didn't have many distinct scripts & Xinjiang is surprisingly frequent. While part of modern-day China, for many historical scripts, the sources almost always say "Central Asia" when the area was under control of Turkic or sometimes Mongolian cultures.
  - The structure allowed me to use the same box to show evolutions of a script (see esp. early Chinese). This does not imply older versions aren't still used for specialized cases (eg. Clerical is still used for calligraphy, old Georgian scripts are still used for religious purposes).

# Script samples (All Scripts)

I'm not an expert in all these languages of course. To try to show the samples neutrally, I generally used the first 7 letters of the alphabet (or Unicode Block where I couldn't quite figure out for sure the alphabetic order). The first three are uppercase and the next are lowercase when the script has casing (ABCdefg). For the Brahmic family which usually separates consonants and vowels, I tried to stick to the traditional ordering of consonants (*k*, *kh*, *g*, *gh*, *n*, etc.). Where the script was too ordered by appearance I did break this pattern to showcase a variety of distinct characters.

For scripts with a primarily vertical writing direction, the diagram is intended to rotated 90 degrees clockwise to read the script sample.

For space reasons, some only got 5 letters and others none at all. Otherwise when there is no script, this is because either the script is not yet in Unicode and/or there was no Noto font for the script. Most of scripts had a Noto Sans font available, but the following required a Noto Serif font: Ahom, Dogri, Khitan Small, Makasar, Old Uyghur, Nyiakeng Puachue Hmong, Tangut, Tibetan, Todhri, Toto, Yezidi. Note that to keep things neutral, all script samples are set to the same font size, differences in size are due to the font itself.

This is an area that may change in the future, as it would be nice to show the same characters evolving.

# Future improvements (All Scripts)

  - I would like to add writing direction changes. At present they show the modern writing direction, but given the timeline format it would probably be better to show when that changed.
  - I'm not sure if there's an intuitive way to show the case where there's a highly related group of scripts in which one or two members distinguish themselves from the group as a whole. This is notably the case with Latin & Old Italic. While Latin derived from one of the Old Italic alphabets (Etruscan specifically), it is arguably a member of said group as well. If I recall correctly, other cases of "distinguished group member" on the chart are Libyco-Berber->Tifinagh, Takri->Dogri and Kaithi->Sylheti Nagri. The Takri->Dogri one is illustrative of a solution we can't take: simply putting the distinguished member chronologically after the group. Not only does this falsely imply a late start for the distinguished member, but it's impossible in this particular case where the member doesn't survive past the group.