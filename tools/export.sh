#!/bin/bash

opt_a=false
opt_m=false

while getopts "ham" opt; do
    case $opt in
        h) 
            echo "Script should be run from folder containing charts. Export using -m for Modern Scripts only and -a for All Scripts only"
            exit 0
            ;;
        a)  
            opt_a=true
            ;;
        m)  
            opt_m=true
            ;;
        \?)
            echo "Unrecognized option."
            exit 1
            ;;
    esac
done

if [ $opt_m != "true" ]; then
    inkscape -D -d 96 "All Script History.svg" -o "All Script History.png"
    inkscape -D -d 192 "All Script History.svg" -o "All Script History 2X.png"
    inkscape -d 96 "All Script History.svg" -o "All Script History.pdf"

    convert "All Script History.png" -crop 950x950+2+3105 "All Scripts preview.png"
fi

if [ $opt_a != "true" ]; then
    drawio -x -f pdf -o "Modern Script History.pdf" "Modern Script History.drawio"
    drawio -x -f png -o "Modern Script History.png" "Modern Script History.drawio"
fi
