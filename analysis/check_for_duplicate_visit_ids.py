import logging
import sqlite3
import json
import argparse
from pprint import pprint as pp
from contextlib import closing
from pathlib import Path

def duplicates_present(con):
    dupes = con.execute('''
SELECT COUNT(*) FROM (SELECT visit_id, COUNT(DISTINCT browser_id) AS cnt,
top_level_url FROM http_requests GROUP BY visit_id) WHERE cnt > 1
                        ''').fetchall()[0][0]
    return dupes

def find_duplicates(con):
    con.executescript('''
-- Compile together info on all duplicated visit_ids
DROP TABLE IF EXISTS dedupe_duplicates;
CREATE TABLE dedupe_duplicates AS 
SELECT navigations.visit_id, navigations.browser_id, extension_session_uuid, arguments FROM navigations 
INNER JOIN crawl_history USING(visit_id) 
WHERE navigations.visit_id IN 
-- List of all visit_ids that have more than 1 browser_id associated with them 
(SELECT visit_id FROM (SELECT visit_id, COUNT(DISTINCT browser_id) AS cnt, 
top_level_url FROM http_requests GROUP BY visit_id) WHERE cnt > 1) 
AND transition_type = 'link' 
-- crawl_history holds correct details - if in it, the (visit_id,browser_id) pair is correct
AND (navigations.visit_id, navigations.browser_id) NOT IN (SELECT visit_id, browser_id FROM crawl_history) 
AND crawl_history.command = 'GetCommand' 
GROUP BY extension_session_uuid;
DROP TABLE IF EXISTS dedupe_corrected;
CREATE TABLE dedupe_corrected AS 
SELECT crawl_history.visit_id AS correct_vid, dedupe_duplicates.visit_id AS wrong_vid, 
dedupe_duplicates.browser_id, dedupe_duplicates.arguments, dedupe_duplicates.extension_session_uuid 
FROM dedupe_duplicates INNER JOIN crawl_history USING(arguments,browser_id);
-- Require manual correction:
DROP TABLE IF EXISTS dedupe_manually;
CREATE TABLE dedupe_manually AS 
SELECT "" AS correct_vid, visit_id AS wrong_vid, browser_id, arguments, 
extension_session_uuid FROM dedupe_duplicates WHERE extension_session_uuid 
NOT IN (SELECT extension_session_uuid FROM dedupe_corrected);
                ''')
    con.commit()

def fix_duplicates(con):
    tables = ['http_requests', 'http_responses']
    logging.info('Backing up visit_ids to `bad_vid` folder for the following tables:')
    logging.info('\t' + ','.join(tables))
    for table in tables:
        try:
            con.execute(f'ALTER TABLE {table} ADD bad_vid INTEGER')
            con.commit()
            logging.debug(f'bad_vid added to table {table}')
        except sqlite3.Error:
            logging.info(f'bad_vid column already exists in table {table}')
        finally:
            con.execute(f'UPDATE {table} SET bad_vid = visit_id')
            con.commit()
    logging.info(f'Old visit_ids backed up to bad_vid columns for {len(tables)} tables')

    manual_count = con.execute('SELECT COUNT(*) FROM dedupe_manually').fetchall()[0][0]
    manual_corrections = 0
    if manual_count:
        logging.info(
            f'Manual corrections needed for {manual_count} rows.\n'
        )
        manual_corrections = int(input('Enter 1 to begin making corrections, or 0 to ignore: '))
    if manual_corrections:
        prompt_user_for_vid(con)
    else:
        logging.info('Manual corrections rejected. Consult `dedupe_manually` later if you wish to fix the visit_ids')

    corrections_query = 'SELECT correct_vid, extension_session_uuid FROM dedupe_corrected'
    if manual_corrections:
        corrections_query = corrections_query + ' UNION SELECT correct_vid, extension_session_uuid FROM dedupe_manually'
    corrections = con.execute(corrections_query).fetchall()

    logging.info('Updating tables with correct visit_ids...')
    cur = con.cursor()
    for table in tables:
        cur.executemany(f'UPDATE {table} SET (visit_id) = (?) WHERE extension_session_uuid = (?)', corrections)
        con.commit()
        logging.info(f'{cur.rowcount} rows updated in the {table} table.')

    logging.info('All visit_ids corrected. Performing sanity check...')
    if duplicates_present(con):
        logging.error('ERROR: Duplicates are still present in one or more tables!')
    else:
        logging.info('Check passed - no duplicates present!')

def prompt_user_for_vid(con):
    logging.info('Beginning manual corrections...')
    corrections = []
    for row in con.execute('SELECT wrong_vid, browser_id, arguments, extension_session_uuid FROM dedupe_manually'):
        print(f'\n\t[ wrong visit_id: {row[0]} | browser_id: {row[1]} | url: {json.loads(row[2])["url"]} ]\n')
        vid = int(input('Enter correct visit_id: '))
        corrections.append((vid, row[3]))
    cur = con.cursor()
    cur.executemany('UPDATE dedupe_manually SET (correct_vid) = (?) WHERE extension_session_uuid = (?)', corrections)
    con.commit()
    logging.info(f'{cur.rowcount} rows manually set in `dedupe_manually`')

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Checks for and tries to automatically fix duplicate visit_ids')
    parser.add_argument('db', type=Path)
    parser.add_argument('--no-action', dest='dontfix', action='store_true')
    args = parser.parse_args()

    with closing(sqlite3.connect(args.db)) as con:
        dupes = duplicates_present(con)
        if dupes:
            logging.info(f'Detected {dupes} visit_ids which have 2 or more browser_ids associated')
            find_duplicates(con)
            if not args.dontfix:
                fix_duplicates(con)
        else:
            logging.info('No duplicate visit_ids detected')
