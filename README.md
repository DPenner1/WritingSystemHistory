# Writing System History

![Writing System History](https://github.com/DPenner1/WritingSystemHistory/blob/main/Script%20History.png)

This projects's objective is to provide a visual reference as to how modern writing scripts are related. This is not a coding project, but it can serve as a quick reference for internationalization testing (but is by no means sufficient). 

**The PDF version is clickable**: all of the scripts and most of the legend are linked to an appropriate Wikipedia page.

The diagram is designed to fit on both A4 and US-Letter sized paper. `Script History.xml` is the source file for draw.io.

## General Diagram Notes

  - Reminder that writing scripts and spoken language can have very different histories.
  - "Specialized use" means use in specific use cases, but not for general default written communication of a language (or the language itself is specialized). About half of these were for religious purposes.
  - The specific symbols used to identify writing system type were mostly chosen by taking the largest system of that type and simply finding something that worked with the font I was using. Though with Latin, I wanted a non-Latin looking symbol.
  - Some scripts have multiple possible writing directions or are difficult to categorize. There are multiple symbols for these, I attempted to list the most dominant first.
  - "Extra" added letters don't count as a new script.
  - There is a line on how many letters "imported" from a secondary script counts as an arrow in the diagram. No hard line currently, there's a gulf between the "few" Fraser and Pollard derived letters in Pahawh Hmong and the seven Demotic derived letters in Coptic.
  - I generally went with Wikipedia's article title for the name of the scripts
  - There are probably mistakes.

## Script Inclusion Criteria

For space and sanity, some scripts have to be left out. In order to have semi-objective criteria for this, here's what I've landed on:

  1. All **currently used** writing scripts are included if they are in Unicode and are in some natural active non-moribund use (or were moribund but revival attempts have yet to prove successful)
  2. Include all ancestor scripts of the currently used scripts, but remove the following, unless they are the earliest known ancestor:
     1. Scripts with no splits/branches. Eg. There's the script lineage of Sukhothai > Fakkham > Tai Noi > Lao. Fakkham and Tai Noi are excluded as they don't branch off anywhere else on the diagram, but Sukhothai remains as it branches to Thai and Tai Viet.
     2. Scripts whose only splits/branches are similarly named. Eg. The Telugu-Kannada script only branches into Telugu and Kannada, and is removed.

Naturally, there's a judgment call here, made worse by the fact scripts on the boundary of inclusion/exclusion are also lesser known and hard to research. Most marginal inclusions/exclusions were due to this boundary, but here's some notes on a few peculiar exclusions:

  - Runic: Everyday use long dead, but various new use cases pop up throughout history, though no sufficent current use that I can see. A single letter as a symbol for Bluetooth doesn't count.
  - Nyiakeng Puachue Hmong: Probably should be included, but researching this one is proving difficult in terms of what the current use is and where it derives from, though I can visually see that it's probably somewhere in Khmer family of scripts. And the long name will be fun to try to fit on the diagram.

## Script specific notes

*All based on reading Wikipedia, and sometimes Omniglot.*

  - **Baybayin**: Quite a few theories on origin, one of them is Gujarati which I am not including without stronger evidence as that would be hard to with the current diagram layout.
  - **Bopomofo**: Maybe over 10m users? It's used for computer input in Taiwan and Taiwan is around 23m people.
  - **Brahmi**: Seems the Northern/Southern Brahmi distinction is mostly grouping convenience?
  - **Chinese script styles**: The way I read it, the Wikipedia articles seem to imply these are closer to variations rather than full-fledged different scripts, so I've chosen to group them together, splitting out the earliest Oracle Bone script. But extremely uncertain about this one.
  - **Georgian**: I opted to group this with the Greek family due to greater similarity.
  - **Hentaigana**: Maybe over 10m users? Wikipedia says its rare, but Japan is 100m+ people.
  - **Kayah Li**: Appears to have come up with many unique letter glyphs, but with likely influence from Thai and Burmese, so I've shaded it Brahmic & Independent.
  - **Pahawh Hmong**, Mainly derived from Lao but derives a few letters from Pollard and Fraser. Since it's just a few letters, and the diagram would be a mess trying to incoporate that, I didn't. Also, unlike the other abugidas, it seems this one's vowel-based.
  - **Pitman Shorthand**: I went for Abugida based on vowels appearing to be diacritical to consonants.
  - **Thaana**: The Brahmic half is because it partially derives from various numeral systems! It's unclear exactly where in the Brahmic branch various numeral systems split off from though.
  - **Tifinagh**: Marginal inclusion for both Tifinagh or Neo-Tifinagh. Notably, Tifinagh was the only script I found written from bottom to top.



