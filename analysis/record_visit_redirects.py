from tldextract import extract
from pathlib import Path
from contextlib import closing
import argparse
import sqlite3
import json
import logging

def tld(url):
    return list(map(str.lower,extract(url)[1:]))

parser = argparse.ArgumentParser(description='Record redirects: we visited one domain, but ended up recording visits to another.')
parser.add_argument('db', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()

logging.basicConfig(level=logging.INFO)
with closing(sqlite3.connect(args.db)) as con:
    cur = con.cursor()
    redirects = []
    visits = cur.execute('SELECT visit_id, site_url FROM site_visits').fetchall()
    for visit in visits:
        (vid, surl) = visit
        url = cur.execute('SELECT url FROM request_data WHERE visit_id = ' + str(vid)).fetchone()
        if url:
            (url,) = url
        else:
            # No data for visit recorded in request_data
            continue
        if tld(url) != tld(surl):
            logging.info(f'Detected redirect from {surl} to {url}')
            redirects.append([vid, surl, url])

with open(args.output, 'w') as f:
    json.dump(redirects, f)
logging.info(f'Recorded {len(redirects)} redirects to {args.output}')
