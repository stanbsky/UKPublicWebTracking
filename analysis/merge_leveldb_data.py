import logging
import sys
import sqlite3
import plyvel
from contextlib import closing

logging.basicConfig(level=logging.INFO)

with closing(sqlite3.connect(sys.argv[1])) as con:
    with closing(con.cursor()) as cur:
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
            cur.execute('DELETE FROM request_data WHERE length(content_blob) < 3000')
            con.commit()
            logging.info(f'Deleted {cur.rowcount} abnormally short responses.')
