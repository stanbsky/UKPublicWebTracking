import sqlite3
import argparse
from contextlib import closing
from pathlib import Path


def create_request_data(db, cmp):
    with closing(sqlite3.connect(db)) as con:
        cur = con.cursor()
        if cmp:
            # Separate out the vanilla crawl for building request_data
            cur.executescript('''
                CREATE TEMPORARY TABLE site_visits AS 
                SELECT * FROM site_visits WHERE browser_id IN 
                (SELECT browser_id FROM crawl WHERE browser_params NOT LIKE '%.tar%')
                              ''')
            pref = 'temp.'
        else:
            pref = ''
        con.commit()

        cur.executescript(
            f"CREATE TEMPORARY TABLE chash AS "
            f"SELECT content_hash, visit_id FROM http_responses GROUP BY visit_id;"
            f"DROP TABLE IF EXISTS request_data;"
            f"CREATE TABLE request_data AS "
                f"SELECT {pref}site_visits.visit_id, site_url AS url, chash.content_hash "
                f"FROM site_visits JOIN chash ON chash.visit_id = {pref}site_visits.visit_id"
        )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Creates a request_data table pairing requests and responses for the main GET request used to navigate to a website.')
    parser.add_argument('db', type=Path)
    parser.add_argument('--cmp', action='store_true')
    args = parser.parse_args()
    create_request_data(args.db, args.cmp)
