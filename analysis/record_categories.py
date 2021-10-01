import logging
import json
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('db', type=Path)
parser.add_argument('url_list', type=Path)
args = parser.parse_args()

logger = logging.getLogger()
logger.setLevel(logging.WARNING)

with open(args.url_list) as f:
    sites = []
    for category, urls in json.load(f).items():
        sites.extend([(category, url) for url in urls])

with closing(sqlite3.connect(args.db)) as con:
    try:
        con.execute('ALTER TABLE site_visits ADD COLUMN category TEXT')
    except:
        logger.warning('Table site_visits already contains a category column!')

    con.executemany('UPDATE site_visits SET category = ? WHERE site_url = ?', sites)
    con.commit()
    logging.info('Finished. {con.total_changes} rows updated.')
