# Writing System History

This project consists of two diagrams:

  1. A minimalistic diagram designed to show the history of **currently used** scripts while fitting on both A4 & US Letter sized paper with 1/4" margins for easy printing.
  2. A comprehensive diagram showing the history of **all scripts** in Unicode, including a timeline and location of origin.

Note that the PDF & HTML versions are **clickable**: all of the scripts and most of the legend are linked to an appropriate Wikipedia page *(however, I wasn't careful with fonts - I'm not sure whether they are embedded or not, so PDFs/HTML/SVG files may not look as intended - I'll try to take a look at this early/mid June)* .

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
  - Some scripts have multiple possible writing directions or are difficult to categorize. There are multiple symbols for these, I attempted to list the most dominant first.
  - Sometimes scripts incorporate letters from other scripts. In order to count as a derivation, the amount of borrowed letters should be at least 20%. This percentage was derived from the Coptic borrowing of Demotic letters and hence ultimately Egyptian Hieroglyphic characters. I wanted this on the diagram as it appears to constitute the only *current* use of Egyptian Hieroglyph derived characters outside of the Proto-Sinaitic branch. For partial independent creation, the same percentage provisionally applies, but I find that less interesting so I might change that in the future.
  - There was effort to place independent scripts near related scripts. For the Modern diagram, this is linguistic similarity, for the All Scripts diagram this is more geographic.
  - In the All Scripts diagram, I did not show disputed derivations. I simply picked the majority opinion, or where there was no obvious one I could determine, I first favoured non-independent derivation, then whichever one made the diagram work better (generally when sibling branches originate around the same time)
  - The script groups in the legend are ordered by a rough estimate of total population using them.
  - For the All Scripts timeline, dates before 1800 in particular are frequently not known with absolute precision and might commonly have an acceptable range of a century, sometimes two. Part of this is lack of historical/archaeological record, and part of this is that scripts tend to gradually evolve so an absolute date is a bit nebulous. Unless I could find more specific text, when Wikipedia said something like "5th century," I by default put it in the middle of the century, so 450. I did the same for info-box dates like "c. 800" as I found this tended to be said as 9th century in the article text, so I moved it up to 850 in the diagram.
  - The structure of the All Scripts diagram allowed me to use the same box to show evolutions of a script (see esp. early Chinese). This does not imply older versions aren't still used for specialized cases (eg. Clerical is still used for calligraphy, old Georgian scripts are still used for religious purposes), but it does mean that there is no significant exteneded simultaneous use of the script versions in question.
  - Modern Scripts diagram was made in Draw.IO and All Scripts in Inkscape (.svg).

## Script Inclusion Criteria

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

In the All Scripts diagram, this turned out to be much less of an issue. It starts by including all Unicode scripts (up to anticipated v17) and then including all non-Unicode historical ancestors (as per Wikipedia) by default. A few non-branching historical ancestors then get excluded for space reasons. I did specially include non-Unicode Maya and Indus scripts for historical significance, though admittedly the latter is not yet determined to be a full-fledged writing script. There's also some "extra" scripts where Unicode considers it to be part of another one, but I felt it should be split out based on my reading of Wikipedia. Eg. Hentaigana is encoded as a part of Kana in Unicode, Hieratic is considered a font variation of Egyptian Hieroglyphics, etc.

A bigger issue in the All Scripts diagram was the consideration of what counts as separate scripts, especially as they frequently evolve gradually. This was purely a judgement call, mostly following along with Wikipedia. For the most part removing non-branching historical ancestors resulted in being able to sidestep this question in the Modern Scripts diagram, but it was still somewhat challenging for the [Chinese script(s)](https://en.wikipedia.org/wiki/Chinese_script_styles) and [Georgian script(s)](https://en.wikipedia.org/wiki/Georgian_scripts). Note that having a few "extra" letters won't count as a separate script in this diagram.


## Script specific notes

*My sources were mainly [Wikipedia](https://en.wikipedia.org), [Omniglot](https://www.omniglot.com/), [Endangered Alphabets](https://www.endangeredalphabets.net/alphabets/) and sometimes Unicode inclusion proposals.*

  - **Asomtavruli (Old Georgian)**: Disputed origin. It seems the majority opinion is that it's derived from Greek, though some argue a Semitic or independent origin.
  - **Baybayin**: Quite a few theories on origin, one of them is Gujarati which I am not including without stronger evidence as that would be hard to link with the current Modern Scripts diagram layout.
  - **Bopomofo**: Based on it being used for computer input in Taiwan and Taiwan being around 23m people, I've bolded it for being used by over 10m people.
  - **Brahmi**: The majority academic opinion seems to favour Aramaic origin, but some advocate independent derivision or derivision from the Indus Script. Also, seems the Northern/Southern Brahmi distinction is mostly geographic grouping convenience? I can't find a lot of sources making the distinction, and Wikipedia doesn't really cite precise criteria on the grouping, but it's useful for this diagram.
  - **Hentaigana**: Maybe over 10m users? Wikipedia says its rare, but Japan is 100m+ people.
  - **Kayah Li**: Appears to have come up with many unique letter glyphs, but with likely influence from Burmese, so I've made it Brahmic & Independent.
  - **Nushu** *(All Scripts only)*: Just about the least certain for origin date. There's broad agreement peak usage was late Qing (c. 1900), but origin is totally unknown, with one source even having suggested Song dynasty (960-1279).
  - **Nyiakeng Puachue Hmong**: Several letters similar to Hebrew while appearing Thai or Lao in style. Seems reasonable for a script devised by a Hmong Christian group. Far from definitive, so I put disputed arrows.
  - **Pahawh Hmong**, Appears mainly an independent invention, though significantly influenced by Lao. There appears to be some influence from Pollard and Fraser as well, but since that is lesser and it would be a mess trying to incoporate that, I didn't. Also, unlike the other abugidas, it seems this one's vowel-based.
  - **Thaana**: Uniquely, the letters are derived from Arabic and Indic numeral systems. Numbers aren't generally considered a language so their representation aren't considered a writing system to be included in this diagram. Thus, Thaana gets the independent group in this diagram.
  - **Tifinagh**: Marginal inclusion for both Tifinagh or Neo-Tifinagh. Frequently sources would just use Tifinagh for the modern version, but sources that distinguished did tend to say Tifinagh had some limited use. Notably, Tifinagh was one of two scripts I found written from bottom to top (with the other being Hanuno'o).
  - **Ulu / Rejang**: Rejang is part of the highly related Ulu group of scripts. I couldn't tell whether Unicode has Rejang as a stand-alone script or intended it to represent all Ulu scripts (with variants being dealt with in font).
  - **Yi**: Just so much contradiction in the sources, I did my best.


## Script samples

I'm not an expert in all these languages of course. To try to show the samples neutrally, I generally used the first 7 letters of the alphabet (or Unicode Block where I couldn't quite figure out for sure the alphabetic order). The first three are uppercase and the next are lowercase when the script has casing (ABCdefg). For the Brahmic family which usually separates consonants and vowels, I tried to stick to the traditional ordering of consonants (*k*, *kh*, *g*, *gh*, *n*, etc.). Where the script was too ordered by appearance I did break this pattern to showcase a variety of distinct characters.

For space reasons, some only got 5 letters and others none at all. Otherwise when there is no script, this is because I did not have a font that supported it and did not want to go hunting for it (in particular if it's not in Unicode yet!).

Some scripts may appear larger or smaller. To keep things neutral, I simply used the default sans serif font on my machine and used a consistent software font point size. Size differences would be due to the font itself (it's been a while since I've done any graphical work on Windows so I'm not sure if it's the same, but my Linux Mint text programs generally just let me specify Sans and presumably selects an appropriate font that has the characters in question).



