import logging
import sqlite3
import argparse
from contextlib import closing
from pathlib import Path


def create_request_data(db, cmp):
    with closing(sqlite3.connect(db)) as con:
        cur = con.cursor()

        # Speed up this query and future analyses by building visit_id indices
        tables = ['requests','responses']
        for table in tables:
            try:
                logging.info(f'Adding index on visit_id in http_{table}...')
                cur.execute(f'CREATE INDEX {table}_vid ON http_{table}(visit_id)')
            except sqlite3.Error:
                logging.warning(f'Index already exists')

            query = '''
        CREATE TABLE request_data AS
        SELECT content_hash, http_responses.visit_id, http_responses.url FROM http_responses 
        -- Attempt to make sure we are grabbing the content hash for the main page
        INNER JOIN http_requests USING (visit_id, request_id) WHERE http_requests.resource_type = 'main_frame' 
        '''

        if cmp:
            # Separate out the vanilla crawl for building request_data
            query = query + "AND http_responses.browser_id IN (SELECT browser_id FROM crawl WHERE browser_params NOT LIKE '%accept%' AND browser_params NOT LIKE '%reject%')"
        query = query + 'GROUP BY http_responses.visit_id'

        logging.info('Finding main page content hashes...')
        cur.execute(query)
        con.commit()
        entries_written = cur.execute('SELECT COUNT(*) FROM request_data').fetchall()[0][0]
        logging.info(f'Done. {entries_written} entries written to request_data')

        # Sanity check
        null_hash_rows = cur.execute('SELECT COUNT(*) FROM request_data WHERE content_hash IS NULL').fetchall()[0][0]
        if null_hash_rows:
            logging.warning(f'No content_hash recorded for {null_hash_rows} rows!')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Creates a request_data table pairing requests and responses for the main GET request used to navigate to a website.')
    parser.add_argument('db', type=Path)
    parser.add_argument('--cmp', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    create_request_data(args.db, args.cmp)
