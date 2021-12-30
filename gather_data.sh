#!/bin/bash

# Figure out if we're working with a crawl/precrawl
if [ -f "data/$1/crawl.sqlite" ]; then
    CTYPE=crawl
else
    CTYPE=precrawl
fi

source analysis/utilities.sh
echo "Deleting intermediate screenshots..."
rm -rf data/$1/screenshots/parts
echo "Moving screenshot folder..."
mv data/$1/screenshots data/$1-screenshots
echo "Moving profiles folder..."
mv data/$1/profiles data/$1-profiles
echo "Moving logs..."
mv logs/$CTYPE.log data/$1/$1.log
mv logs/$CTYPE-openwpm.log data/$1/$1-openwpm.log
cd data
echo "Uploading crawl data..."
upload_to_gdrive $1 15
