#!/bin/bash

inkscape -D -d 96 "All Script History.svg" -o "All Script History.png"
inkscape -D -d 192 "All Script History.svg" -o "All Script History 2X.png"
inkscape -d 96 "All Script History.svg" -o "All Script History.pdf"

convert "All Script History.png" -crop 950x950+2+3142 "All Scripts preview.png"

drawio -x -f pdf -o "Modern Script History.pdf" "Modern Script History.drawio"
drawio -x -f png -o "Modern Script History.png" "Modern Script History.drawio"
