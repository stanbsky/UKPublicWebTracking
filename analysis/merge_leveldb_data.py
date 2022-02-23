import re
import logging
import sys
import sqlite3
import plyvel
from contextlib import closing

logging.basicConfig(level=logging.INFO)

with closing(sqlite3.connect(sys.argv[1])) as con:
    cur = con.cursor()
    hashes = cur.execute(
        'SELECT content_hash FROM request_data WHERE content_hash IS NOT NULL'
    ).fetchall()
    try:
        logging.info('Adding \'content_blob\' column')
        cur.execute('ALTER TABLE request_data ADD content_blob BLOB')
    except sqlite3.Error:
        logging.warning('\'content_blob\' column already exists')

    with closing(plyvel.DB(sys.argv[2])) as ldb:
        rows = 0
        for h in hashes:
            h = h[0]
            content = ldb.get(bytes(h, encoding='utf8'))
            if content:
                cur.execute(
                    'UPDATE request_data SET content_blob = ? WHERE content_hash = ?',
                    (content, h)
                )
                rows += 1
                logging.debug(f'Content inserted for {h}')
            else:
                logging.debug(f'No content found for {h}')
        con.commit()
        logging.info(f'Done. {rows} rows updated.')

    try:
        logging.info('Adding \'is_short\' column')
        cur.execute('ALTER TABLE request_data ADD is_short INTEGER')
    except sqlite3.Error:
        logging.warning('\'content_blob\' column already exists')
    cur.execute('UPDATE request_data SET is_short = 1 WHERE length(content_blob) < 3000')
    con.commit()
    logging.info(f'Detected {cur.rowcount} abnormally short responses.')

    # Sanity check: does content_blob contain a <title> tag?
    def regexp(x,y, search=re.search):
        try:
            return 1 if search(x, y) else 0
        except Exception as e:
            logging.exception(e)
    con.create_function('regexp', 2, regexp)
    bad_content = cur.execute("SELECT visit_id FROM request_data WHERE NOT content_blob REGEXP ?", [rb'<title.*?>|<TITLE.*?>']).fetchall()
    bad_records_count = len(bad_content)
    if bad_records_count > 0:
        logging.warning(
            f'{bad_records_count} entries do not contain a <title> tag and are likely not main page content!'
        )
        try:
            logging.info('Adding a bad_content column...')
            cur.execute('ALTER TABLE request_data ADD bad_content INTEGER')
        except sqlite3.Error:
            logging.warning('\'bad_content\' column already exists')
        cur.executemany('UPDATE request_data SET bad_content = 1 WHERE visit_id = ?', bad_content)
        con.commit()
        logging.info(f'Done. {cur.rowcount} bad content rows labelled.')
