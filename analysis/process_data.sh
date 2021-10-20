#!/bin/bash
#
# Activate virtualenv, then run from project root:
#   ./analysis/process_data.sh `which python` crawl_folder_name
#

# Path to virtualenv python
PYTHON=$1
# Name of crawl directory
CRAWL=$2

# Log all python command output
LOG=data/$CRAWL/process.log
exec > >(tee -ia $LOG) 2>&1

DB=data/$CRAWL/precrawl.sqlite
REDIRECTS=data/$CRAWL/redirects.json

# Run all processing scripts
$PYTHON analysis/pair_responses_and_requests.py $DB
$PYTHON analysis/merge_leveldb_data.py $DB data/$CRAWL/precrawl-leveldb
$PYTHON analysis/record_visit_redirects.py $DB $REDIRECTS
$PYTHON analysis/record_categories.py $DB crawl/lists/urls.json
$PYTHON analysis/parse_request_urls.py $DB crawl/lists/disconnect.json
$PYTHON analysis/parse_logs.py data/$CRAWL/$CRAWL.log \
    --db data/$CRAWL/parsed_log.sqlite --table $CRAWL --redirects $REDIRECTS

# Output time taken to process data
duration=$SECONDS
echo "$(($duration / 60)) minutes and $(($duration % 60)) seconds taken to process data."
