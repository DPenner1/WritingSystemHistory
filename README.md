# Writing System History

![Writing System History](https://github.com/DPenner1/WritingSystemHistory/blob/main/Script%20History.png)

This projects's objective is to provide a visual reference as to how modern writing scripts are related. This is not a coding project, but it can serve as a quick reference for internationalization testing (but is by no means sufficient). 

**The PDF version is clickable**: all of the scripts and most of the legend are linked to an appropriate Wikipedia page.

The diagram is designed to fit on both A4 and US-Letter sized paper. `Script History.xml` is the source file for draw.io.

## General Notes

  - All **current** writing scripts are intended to be included, but for space and sanity the least used ones have to be left out.
    - The script must not be moribund or have revival efforts whose success is uncertain.
    - Scripts with a specialized use case (not for general communication) are excluded if they do not exist in Unicode.
  - Scripts are additionally included if they are an ancestor to a modern script. However, chains of historical scripts are skipped, there must be meaninful splits to include them.
    - "Extra" added letters don't count as a new script.
  - The specific symbols used to identify writing system type were mostly chosen by taking the largest system of that type and simply finding something that worked with the font I was using. Though with Latin, I wanted a non-Latin looking symbol.
  - There are probably mistakes.

## Language specific notes

  - **Bopomofo**: Maybe over 10m users? Wikipedia says its a method of computer input in Taiwan and Taiwan is around 23m people.
  - **Brahmi**: Seems the Northern/Southern Brahmi distinction is mostly grouping convenience?
  - **Chinese script styles**: The way I read it, the Wikipedia articles seem to imply these are style variations rather than full-fledged different scripts, so I've chosen to group them together, spitting out the earliest Oracle Bone script.
  - **Georgian**: I opted to group this with the Greek family due to greater similarity.
  - **Hentaigana**: Maybe over 10m users? Wikipedia says its rare, but Japan is 100m+ people.
  - **Pahawh Hmong**, Mainly derived from Lao but Wikipedia mentions it derives a few letters from Pollard and Fraser. Since it's just a few letters, and the diagram would be a mess trying to incoporate that, I didn't. Also, unlike the other abugidas, it seems this one's vowel-based.
  - **Pitman Shorthand**: I went for Alphabet based on my read of Wikipedia, but not sure.
  - **Thaana**: The Brahmic half is because it partially derives from the numeral systems! It's unclear exactly where in the Brahmic branch various numeral systems split off from though.
  - **Tifinagh**: Wasn't sure Tifinagh or Neo-Tifinagh met the inclusion criteria, but erred on the side of leaving them in. Notably, Tifinagh was the only script I found written from bottom to top.
