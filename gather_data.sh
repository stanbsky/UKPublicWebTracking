#!/bin/bash

source analysis/utilities.sh
echo "Renaming and moving directories..."
rm -rf data/$1/screenshots/parts
mv data/$1/screenshots data/$1-screenshots
mv logs/precrawl.log data/$1/$1.log
cd data
echo "Uploading logs..."
pushd $1
upload_to_gdrive $1.log 2
rm $1.tar.xz
popd
echo "Uploading crawl data..."
upload_to_gdrive $1 10
