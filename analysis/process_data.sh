#!/bin/bash
#
# Activate virtualenv, then run from project root:
#   ./analysis/process_data.sh `which python` crawl_folder_name
#

# Path to virtualenv python
PYTHON=$1
# Name of crawl directory
CRAWL=$2

# Figure out if we're working with a crawl/precrawl
if [ -f "data/$CRAWL/crawl.sqlite" ]; then
    CTYPE=crawl
else
    CTYPE=precrawl
fi

# If it's a CMP crawl database, treat it differently
if [ -z "$3" ]; then
    CMP=
else
    CMP=--cmp
fi

# Log all python command output
LOG=data/$CRAWL/process.log
exec > >(tee -ia $LOG) 2>&1

DB=data/$CRAWL/$CTYPE.sqlite
REDIRECTS=data/$CRAWL/redirects.json

# Run all processing scripts
$PYTHON analysis/check_for_duplicate_visit_ids.py $DB
$PYTHON analysis/pair_responses_and_requests.py $DB $CMP
$PYTHON analysis/merge_leveldb_data.py $DB data/$CRAWL/$CTYPE-leveldb
$PYTHON analysis/record_visit_redirects.py $DB $REDIRECTS
$PYTHON analysis/record_categories.py $DB crawl/lists/urls.json
$PYTHON analysis/parse_request_urls.py $DB crawl/lists/disconnect.json
$PYTHON analysis/parse_logs.py data/$CRAWL/$CRAWL.log \
    --db data/$CRAWL/parsed_log.sqlite --table $CRAWL 

# Output time taken to process data
duration=$SECONDS
echo "$(($duration / 60)) minutes and $(($duration % 60)) seconds taken to process data."
