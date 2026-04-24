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


## Diagram Notes

  - There are probably mistakes.
  - The diagrams show **graphical** derivision of scripts which can be very different from spoken language derivation.
  - "Specialized use" means use in specific use cases, but not for general default written communication of a language (or the language itself is specialized). Most frequently, this is religious or ceremonial uses.

## Bias avoidance

The general design philosophy is to create interesting/informative charts that are self-consistent. To that end, the diagram "rules" are engineered to result in a good end result. However, as much as reasonable, exceptions are avoided to keep the diagram self-consistent to avoid any bias. Additionally, authoritative sources, such as academic papers and [Unicode data](https://home.unicode.org/) are followed.

There will of course have to be judgment calls to make, as is normal for trying to categorize things that fundamentally do not have hard boundaries. These rules and judgment calls are [documented](https://github.com/DPenner1/WritingSystemHistory/tree/main/docs) for transparency.

## FAQ

 - **Why isn't script X included?** Usually this will be because it's considered a variant and not a full script in its own right. For Modern Scripts, this may additionally be because it's close to unused. See Script Inclusion Criteria at the top of the [main doc](https://github.com/DPenner1/WritingSystemHistory/blob/main/docs/Diagram%20main.md) for further details.
 - **Shouldn't script X derive from Y?** Maybe. But, a [decent amount of research](https://github.com/DPenner1/WritingSystemHistory/blob/main/docs/Script%20Specific%20Notes.md) has been done for these diagrams. Feel free to open an issue. Speaking of which...

## Reporting an issue

Feel free to open issues as you like, but do be warned that issues already answered in documentation will be closed with minimal comment. If raising a factual error (eg. script derivation, dates), as opposed to graphical, please ensure you include good sources, explaining why they counter current cited sources (and note that a singular source is not law - sources can disagree).

Apologies for curtness, but there are around 200 scripts on the All Scripts diagram. I can't be spending too much time going over the details on each one especially if there's already documentation on it. This will only get worse when the beta database exits beta and starts accepting issues, where each *letter/character* could be disputed.

## Source Files

The Modern Scripts diagram was made in Draw.IO and All Scripts in Inkscape SVG. For consistency, the fonts are mostly standardized, by using only Google's [Noto fonts](https://fonts.google.com/noto), with a preference for the Sans serif where possible. This means if you download all the Noto fonts, the source diagrams should look as intended without font fallback issues.

The Modern Scripts diagram though still has old references to Helvetica I'm still working on fixing, but I believe these are whitespace/formatting characters which hopefully don't impact the intended appearance.

The `./tools` folder contains a Linux bash shell script to automatically export the diagrams into the various image/pdf formats. It requires the Inkscape & draw.IO command line interfaces, as well as Imagemagick for the All Scripts preview file. Run it from the project home folder with `./tools/export.sh`. The Inkscape SVG to PDF export throws a lot of "Invalid glyph found" errors, I've not yet figured out why that's the case, but it seems to work just fine. Draw.io does not yet support the HTML export via CLI, so this one still has to be manual.

The source files are sometimes ahead of the PDF/PNG/HTML exports, this will only occur with minor updates.

## Project Origins

I created the Modern Scripts diagram in 2015. I was an independent contractor doing software internationalization testing and wanted a quick visual reference (I did it in personal time to avoid any potential rights issue, in addition to not being an employee). This is also why fitting it on US Letter/A4 was a design consideration, so I could print it out wherever easily. The diagram helped in that I could immediately see which scripts were widely used, and which scripts were more closely related. This latter bit was a good rule of thumb: when I wanted to test a new script, I'd try to pick one furthest away from already tested scripts to maximize my chances of finding new bugs.

The All Scripts diagram came in 2025. I do have a natural interest in language and was sad about two things in the Modern Scripts diagram: Not enough space to include script samples, and I wanted to include many more scripts. It took awhile for me to act on this though because it just seemed infeasible to come up with a way to have a "reasonably" sized diagram while simultaneously having semi-objective script inclusion criteria. Fast-forward 10 years and I've learned more about language and Unicode to help with the script inclusion criteria side of things and became much less hesitant about the potential size of the diagram after having seen many more large charts and diagrams (especially the UsefulCharts YouTube channel).

The database came in 2026. This was partially to help with determining derivations, partially to analyze script sample selection and partially because database development is just something I enjoy doing.

## Licence Info

All rights reserved, for now. In general I'm fine with personal use, I just mostly haven't given much thought about what I want to licence this as (if any), but know open licensing it would be hard to take back.

The database though isn't really protectable anyways, so have at that (I'm non-EU, so don't get that sui generis database protection).

The database project (`./tools/database`) comes with resources from some openly licensed sources:

  - The database is generated from some files the [Unicode Consortium](https://home.unicode.org/). Unicode licence is at [`./resource/unicode-data/license.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/unicode-data/license.txt)

  - The database is generated using some text sourced from Wikipedia, which is under CC BY-SA 4.0. For compliance, and further info on that see in this project [`./resource/wikipedia-sourced/licence-info.txt`](https://github.com/DPenner1/WritingSystemHistory/blob/main/tools/database/resource/wikipedia-sourced/licence-info.txt).
