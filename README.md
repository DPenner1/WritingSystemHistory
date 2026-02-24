# Writing System History

This project consists of two diagrams and a beta-state database:

  1. A minimalistic diagram designed to show the history of **currently used** scripts while fitting on both A4 & US Letter sized paper with 1/4" margins for easy printing.
  2. A comprehensive diagram showing the history of **all scripts** in Unicode, including a timeline and location of origin.
  3. A database mapping out history on a character-by-character basis. See [`./tools/database/README.md`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/README.md) for more infomation on that. This README will focus on the diagrams.

Note that the PDF & HTML versions are **clickable**: all of the scripts and most of the legend are linked to an appropriate Wikipedia page.

Here is the minimalistic diagram:

![Writing System History](https://github.com/DPenner1/WritingSystemHistory/blob/main/Modern%20Script%20History.png)

And a section of the comprehensive diagram (as the full thing is excessive for a README):

![Writing System History](https://github.com/DPenner1/WritingSystemHistory/blob/main/All%20Scripts%20preview.png)

## General Diagram Notes

  - There are probably mistakes.
  - The diagrams show **graphical** derivision of scripts which can be very different from spoken language derivation.
  - "Specialized use" means use in specific use cases, but not for general default written communication of a language (or the language itself is specialized). Most frequently, this is religious or ceremonial uses.
  - I generally went with Wikipedia's article title for the name of the scripts, though there were some exceptions, particularly where Unicode had a distinct name for it.
  - The specific symbols used to identify writing system type were mostly chosen by taking the largest system of that type and simply finding something that worked with the font I was using. Though with Latin, I wanted a non-Latin looking symbol.
  - Some scripts have multiple possible writing directions or are difficult to categorize. There are multiple symbols for these, I attempted to list the most dominant first. For a few scripts written and read in separate directions (eg. Tagbanwa, Hanuno'o), the reading direction is listed first.
  - Sometimes scripts incorporate letters from other scripts. In order to count as a derivation, the amount of borrowed letters should be at least 20%. This percentage was derived from the Coptic borrowing of Demotic letters and hence ultimately Egyptian Hieroglyphic characters. I wanted this on the diagram as it appears to constitute the only *current* use of Egyptian Hieroglyph derived characters outside of the Proto-Sinaitic branch. For partial independent creation, the same percentage provisionally applies, but I find that less interesting so I might change that in the future.
  - There was effort to place independent scripts near related scripts. For the Modern diagram, this is linguistic similarity, for the All Scripts diagram this is more geographic.
  - The script groups in the legend are ordered by a rough estimate of total population using them.

## All Scripts Diagram Notes

  - I did not show disputed derivations. I simply picked the majority opinion, or where there was no obvious one I could determine, I first favoured non-independent derivation, then whichever one made the diagram work better (generally when sibling branches originate around the same time).
  - Dates before 1800 in particular are frequently not known with absolute precision and might commonly have an acceptable range of a century, sometimes two. Part of this is lack of historical/archaeological record, and part of this is that scripts tend to gradually evolve so an absolute date is a bit nebulous. Unless I could find more specific text, when Wikipedia said something like "5th century," I by default put it in the middle of the century, so 450. I did the same for info-box dates like "c. 800" as I found this tended to be said as 9th century in the article text, so I moved it up to 850 in the diagram.
  - The structure allowed me to use the same box to show evolutions of a script (see esp. early Chinese). This does not imply older versions aren't still used for specialized cases (eg. Clerical is still used for calligraphy, old Georgian scripts are still used for religious purposes).
  - Lowercase development is shown in Greek & Latin due to these being significant graphical developments of the script (as is the purpose of this diagram). This isn't special treatment. Best I can tell, all other scripts with a case distinction either have mostly non-graphically distinct letter cases (lowercase is just small uppercase) or the cases appeared at the same time (within the timescale resolution), so is not a distinct evolution of the script.
  - Geography: The scripts are placed in regions (as defined by the Wikipedia articles) according to their place of origin, with reference to modern borders to keep things consistent. Based on script evolution, it was far easier to group Anatolian & Caucasian scripts with Europe (and under some definitions, part of the Caucasus is in Europe anyways). Central Asia is grouped with East Asia for two main reasons: it didn't have many distinct scripts & Xinjiang is surprisingly frequent. While part of modern-day China, for many historical scripts, the sources almost always say "Central Asia" when the area was under control of Turkic or sometimes Mongolian cultures.

## Source Files

The Modern Scripts diagram was made in Draw.IO and All Scripts in Inkscape SVG. For consistency, the fonts are mostly standardized, by using only Google's [Noto fonts](https://fonts.google.com/noto), with a preference for the Sans serif where possible. This means if you download all the Noto fonts, the source diagrams should look as intended without font fallback issues.

The Modern Scripts diagram though still has old references to Helvetica I'm still working on fixing, but I believe these are whitespace/formatting characters which hopefully don't impact the intended appearance.

The `./tools` folder contains a bash shell script to automatically export the diagrams into the various image/pdf formats. It requires the Inkscape & draw.IO command line interfaces, as well as Imagemagick for the All Scripts preview file. Run it from the project home folder with `./tools/export.sh`. The Inkscape SVG to PDF export throws a lot of "Invalid glyph found" errors, I've not yet figured out why that's the case, but it seems to work just fine. Draw.io does not yet support the HTML export via CLI, so this one still has to be manual.

## Script samples (All Scripts)

I'm not an expert in all these languages of course. To try to show the samples neutrally, I generally used the first 7 letters of the alphabet (or Unicode Block where I couldn't quite figure out for sure the alphabetic order). The first three are uppercase and the next are lowercase when the script has casing (ABCdefg). For the Brahmic family which usually separates consonants and vowels, I tried to stick to the traditional ordering of consonants (*k*, *kh*, *g*, *gh*, *n*, etc.). Where the script was too ordered by appearance I did break this pattern to showcase a variety of distinct characters.

For scripts with a primarily vertical writing direction, the diagram is intended to rotated 90 degrees clockwise to read the script sample.

For space reasons, some only got 5 letters and others none at all. Otherwise when there is no script, this is because either the script is not yet in Unicode and/or there was no Noto font for the script. Most of scripts had a Noto Sans font available, but the following required a Noto Serif font: Ahom, Dogri, Khitan Small, Makasar, Old Uyghur, Nyiakeng Puachue Hmong, Tangut, Tibetan, Todhri, Toto, Yezidi. Note that to keep things neutral, all script samples are set to the same font size, differences in size are due to the font itself.

## Why isn't script **X** included? Why does script **X** do **Y**? ##

See [here](https://github.com/DPenner1/WritingSystemHistory/blob/main/docs/Script%20Inclusion%20Criteria.md) for general inclusion criteria, and [here](https://github.com/DPenner1/WritingSystemHistory/blob/main/docs/Script%20Specific%20Notes.md) for script-specific decisions and research notes.

## Next steps

More documentation: Mostly along the lines of the decision making for the diagrams - there's naturally a lot of judgment calls, but as much as possible I tried to do so as consistently as possible. Clearly document all these rules.

Script samples: It would be great to review script samples and specifically try to show evolutions of a character regardless of alphabetic order. Investigating this is what triggered the creation of the database mapping out character history.

## Project Origins

I created the Modern Scripts diagram in 2015. I was an independent contractor doing software internationalization testing and wanted a quick visual reference (I did it in personal time to avoid any potential rights issue, in addition to not being an employee). This is also why fitting it on US Letter/A4 was a design consideration, so I could print it out wherever easily. The diagram helped in that I could immediately see which scripts were widely used, and which scripts were more closely related. This latter bit was a good rule of thumb: when I wanted to test a new script, I'd try to pick one furthest away from already tested scripts to maximize my chances of finding new bugs.

The All Scripts diagram came in 2025. I do have a natural interest in language and was sad about two things in the Modern Scripts diagram: Not enough space to include script samples, and I wanted to include many more scripts. It took awhile for me to act on this though because it just seemed infeasible to come up with a way to have a "reasonably" sized diagram while simultaneously having semi-objective script inclusion criteria. Fast-forward 10 years and I've learned more about language and Unicode to help with the script inclusion criteria side of things and became much less hesitant about the potential size of the diagram after having seen many more large charts and diagrams (especially the UsefulCharts YouTube channel).

## Licence Info

All rights reserved, for now. In general I'm fine with personal use, I just mostly haven't given much thought about what I want to licence this as (if any), but know open licensing it would be hard to take back.

The database though isn't really protectable anyways, so have at that (I'm non-EU, so don't get that sui generis database protection).

The database project (`./tools/database`) comes with resources from some openly licensed sources:

  - The database is generated from some files the [Unicode Consortium](https://home.unicode.org/). Unicode licence is at [`./resource/unicode-data/license.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/unicode-data/license.txt)

  - The database is generated using some text sourced from Wikipedia, which is under CC BY-SA 4.0. For compliance, and further info on that see in this project [`./resource/wikipedia-sourced/licence-info.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/wikipedia-sourced/licence-info.txt).
