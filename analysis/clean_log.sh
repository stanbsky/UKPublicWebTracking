#!/bin/bash

# Cleans up log files for better readability and smaller filesize
# by deleting long printouts, such as settings JSONs
#
# Usage: ./clean_log.sh input_log

# Erase JSONs with browser config settings
sed -i '.filterbak' 's/Browser Config:" .*/Browser Config:" \.\.\./g' $1

# Erase Cookie-O-Matic's rules.json printouts
sed -i '.filterbak' 's/FetchedRules:" .*/FetchedRules:" \.\.\./g' $1

# Cleanup backup file
rm $1.filterbak
