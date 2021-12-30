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
def query_vt(action, url, client):
    try:
        return action(url=url, client=client)
    except APIError as error:
        logger.error(error)
        return None

def _scan(url, client):
    return client.scan_url(url, wait_for_completion=True)

def _get_info(url, client):
    url_id = vt.url_id(url)
    return client.get_object('/urls/{}', url_id)

def parse_categories(data):
    categories = []
    for val in data.values():
        categories.append(val)
    return ';'.join(categories)

def commit_data(output):
    cur.executemany('UPDATE tp_requests SET categories = ?, data = ? WHERE url = ?', output)
    con.commit()
    logger.info(f'{con.total_changes} rows updated.')

with closing(sqlite3.connect(sys.argv[1])) as con:
    # con.row_factory = sqlite3.Row
    with closing(con.cursor()) as cur:
        try:
            logger.info(f'Creating tp_requests table...')
            cur.executescript('''
                CREATE TABLE tp_requests AS
                SELECT url, COUNT(*) AS cnt, resource_type, is_tracker
                FROM http_requests WHERE is_third_party = 1 AND
                resource_type IN ('image','script','sub_frame','websocket','xmlhttprequest')
                GROUP BY url ORDER BY cnt DESC;
                ALTER TABLE tp_requests ADD COLUMN categories TEXT;
                ALTER TABLE tp_requests ADD COLUMN data TEXT;
            ''')
        except sqlite3.Error:
            logger.warning(f'Table already exists')

        # Limit querying to requests seen multiple times: cnt > 2 ~= 3K rows
        urls = set(cur.execute('SELECT url FROM tp_requests WHERE cnt > 2 AND data IS NULL').fetchall())
        logger.info(f'List of {len(urls)} distinct third-party domains loaded')

        output = []
        count = 0
        total = 0
        for url, in urls:
            logger.info(f'Querying VT for {url}...')
            analysis = query_vt(_scan, url, client)
            data = query_vt(_get_info, url, client)
            if not data:
                logger.warning(f'Query for {url} failed!')
                continue
            data = data.to_dict()['attributes']
            categories = parse_categories(data['categories'])
            if not categories:
                logger.warning(f'No categories data for {url}!')
            output.append((
                json.dumps(categories), json.dumps(data), url
            ))
            logger.info(f'Data for {url} successfully retrieved.')
            count += 1
            if count == 10:
                commit_data(output)
                output = []
                total += count
                count = 0

        commit_data(output)
        total += count
        client.close()
        logger.info(f'Finished. {total} rows updated.')
