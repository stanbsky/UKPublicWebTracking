import logging
from pathlib import Path
import sys
import sqlite3
from contextlib import closing
import json
import vt
from vt.error import APIError
from ratelimit import limits, RateLimitException
from backoff import on_exception, expo

name = Path(__file__).stem
logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s | {name} | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).resolve().parent.parent.joinpath(f'logs/{name}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

client = vt.Client(sys.argv[2])

@on_exception(expo, RateLimitException)
@limits(calls=1000, period=60)
def query_vt(query, client):
    try:
        return client.get_object(query)
    except APIError as error:
        logger.error(error)
        return None

def parse_categories(data):
    categories = []
    for val in data.values():
        categories.append(val)
    return ';'.join(categories)

with closing(sqlite3.connect(sys.argv[1])) as con:
    # con.row_factory = sqlite3.Row
    with closing(con.cursor()) as cur:
        try:
            logger.info(f'Creating tlds table...')
            cur.execute('''
                CREATE TABLE tlds (
                    id INTEGER PRIMARY KEY ASC,
                    tld TEXT,
                    categories TEXT,
                    data TEXT
                    )''')
        except sqlite3.Error:
            logger.warning(f'Table already exists')

        # tlds = [('176.32.230.252',),('localhost.',)]
        tlds = set(cur.execute('SELECT DISTINCT tld FROM http_requests WHERE is_third_party = 1').fetchall())
        tlds = tlds.difference(set(cur.execute('SELECT tld FROM tlds WHERE data IS NOT NULL').fetchall()))
        logger.info(f'List of {len(tlds)} distinct third-party domains loaded')

        output = []
        for tld, in tlds:
            logger.info(f'Querying VT for {tld}...')
            data = query_vt(f'/domains/{tld}', client)
            if not data:
                logger.warning(f'Query for {tld} failed!')
                continue
            data = data.to_dict()['attributes']
            categories = parse_categories(data['categories'])
            if not categories:
                logger.warning(f'No categories data for {tld}!')
            output.append((
                tld, json.dumps(categories), json.dumps(data)
            ))
            logger.info(f'Data for {tld} successfully retrieved.')

        client.close()
        cur.executemany('INSERT INTO tlds(tld, categories, data) VALUES (?,?,?)', output)
        con.commit()
        logger.info(f'Finished. {con.total_changes} rows updated.')
