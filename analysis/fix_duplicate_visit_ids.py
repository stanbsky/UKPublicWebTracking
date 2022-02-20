import logging
import sqlite3
import json
import argparse
import re
from contextlib import closing
from pathlib import Path
from tldextract import extract

def clean_url(url):
    # Match full url
    # return re.match('https?:\/\/([^\/:]+)', url).group(1)
    # Match without www
    return re.match('https?:\/\/(?:www\.)?([^\/:]+)', url).group(1)
    # Maximum permissivity: we grab just the domain
    # This should be ok since we'll just end up correcting already correct visit_ids
    # return extract(url).domain # no - this matches things like "gov"
    # return re.match('https?:\/\/(?:www\.)?([^\.]+)', url). group(1) # still really bad, matches like "nhs"

def fix_duplicate_vids(db):
    with closing(sqlite3.connect(db)) as con:
        # Backup old visit_id values to bad_vid
        # tables = ['http_requests', 'http_responses']
        # for table in tables:
        #     try:
        #         con.execute(f'ALTER TABLE {table} ADD bad_vid INTEGER')
        #         con.commit()
        #         logging.debug(f'bad_vid added to table {table}')
        #     except sqlite3.Error:
        #         logging.info(f'bad_vid column already exists in table {table}')
        #     finally:
        #         con.execute(f'UPDATE {table} SET bad_vid = visit_id')
        #         con.commit()

        # logging.info(f'Old visit_ids backed up to bad_vid columns for {len(tables)} tables')

        # Get a list of visit_ids which have multiple associated browser_id instances 
        bad_urls = con.execute('''
        SELECT url FROM (
            SELECT COUNT(DISTINCT browser_id) AS cnt, visit_id, url FROM navigations GROUP BY visit_id
        ) WHERE cnt > 1
                               ''').fetchall()
        bad_urls = {clean_url(e[0]) for e in bad_urls}

        logging.info(f'Found {len(bad_urls)} cases of non-unique visit_ids')

        # Retrieve good visit_ids as (vid, uuid) tuples
        good_data = []
        while bad_urls:
            good_data.extend(
                find_good_vids(con, bad_urls.pop())
            )
        import pdb;pdb.set_trace()
        from pprint import pprint as pp
        pp(good_data)

def find_good_vids(con, bad_url):
    logging.debug(f'Searching for "{bad_url}"')
    bid_to_vid = con.execute(
        "SELECT browser_id, visit_id FROM crawl_history WHERE command = 'GetCommand'"
        f" AND arguments LIKE '%{ bad_url }%'"
    ).fetchall()

    if len(bid_to_vid) == 0:
        logging.error(f"ERROR: Couldn't find any results for bad url {bad_url} in crawl_history!")
        return []
    else:
        logging.debug(f"Found browser_ids, visit_ids {bid_to_vid} associated with bad url {bad_url}")
        bid_to_vid = {bid: vid for (bid, vid) in bid_to_vid}

    bid_bad_vid_to_uuid = con.execute(
        'SELECT browser_id, visit_id, extension_session_uuid FROM navigations WHERE '
        f"url LIKE '%{bad_url}%' GROUP BY extension_session_uuid"
    ).fetchall()

    if len(bid_bad_vid_to_uuid) == 0:
        logging.error(f"Couldn't find any results for url {bad_url} in navigations!")
        return []
    else:
        logging.debug(f"Found browser_ids, uuids {bid_bad_vid_to_uuid} associated with bad visit_id {bad_url}")
        bid_bad_vid_to_uuid = {(bid, vid): uuid for (bid, vid, uuid) in bid_bad_vid_to_uuid}

    return bid_bad_vid_to_uuid 

    # bid_to_uuid = con.execute(
    #     'SELECT browser_id, extension_session_uuid FROM navigations WHERE visit_id = '
    #     f'{bad_vid} GROUP BY browser_id'
    # ).fetchall()

#     if len(bid_to_uuid) == 0:
#         logging.error(f"Couldn't find any results for bad visit_id {bad_vid} in navigations!")
#         return []
#     elif len(bid_to_uuid) != len(bid_to_vid):
#         logging.error("browser_id and uuid results size mismatch!")
#         return []
#     else:
#         logging.debug(f"Found browser_ids, uuids {bid_to_uuid} associated with bad visit_id {bad_vid}")
#         bid_to_uuid = {bid: uuid for (bid, uuid) in bid_to_uuid}

#     return [(bid_to_vid[bid], bid_to_uuid[bid]) for bid in bid_to_vid.keys()]


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Fixes duplicated visit_ids from the unaffected site_visits table')
    parser.add_argument('db', type=Path)
    args = parser.parse_args()

    fix_duplicate_vids(args.db)
