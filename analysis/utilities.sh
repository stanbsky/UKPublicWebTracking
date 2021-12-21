#!/bin/bash

# To use the below, at command prompt, do: source utilities.sh

# First arg: path to directory
# Second arg: number of cores to use
upload_to_gdrive() {
    tar -cvS -I "xz -T$2" -f $1.tar.xz $1; rclone copy -P $1.tar.xz gdrive:/WebTracking2021/data
}

mem_use() {
    ps -U `whoami` --no-headers -o rss | awk '{ sum+=$1} END {print int(sum/1024) "MB"}'
}

mem_use_all() {
    ps hax -o rss,user | awk '{a[$2]+=$1;}END{for(i in a)print i" "int(a[i]/1024+0.5);}' | sort -rnk2
}

# Log parsing functions

cmps_found() {
    count=$(grep "CMP Detected" $1 | wc -l)
    echo "$count/2" | bc -l
}

site_visits_attemped() {
    count=$(grep -P \
        "GetCommand\(https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)" \
        $1 | wc -l)
    # Uncomment below if running a triple-browser CMP crawl
    # echo "$count/3" | bc -l
    echo $count
}

site_visits_attemped() {
    count=$(grep -P \
       "EXECUTING COMMAND: GetCommand\(https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)" \
        $1 | wc -l)
    echo $count
}

browser_commands() {
    grep -i "executing command" $1 | awk '{ print $1, $2, $(NF-4), $(NF-3), $NF }'
}

browser_commandsl() {
    $(_browser_commands) | less
}

browser_visits() {
    grep -i "GetCommand" $1 | awk '{ print $1, $2, $(NF-4), $(NF-3), $NF }' 
}

browser_visitsl() {
    $(_browser_visits) | less
}

# First arg: file with regex patterns, one per line
# Second arg: log to be searched
parse() {
    grep -f $1 -iE $2
}
