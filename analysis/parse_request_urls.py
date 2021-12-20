import logging
import sys
import sqlite3
from contextlib import closing
from tldextract import extract
import json

def parseDisconnectList(blocklist):
    '''
    Produces a dictionary of suspicious domains of the form
        {domain: {'parent': parent_company,
                    'categories': ['Advertising', 'FingerprintingGeneral', etc],
                    'parent_url': parent_company_url}}
    '''
    disconnect_domains = {}

    with open(blocklist) as f:
        disconnect = json.load(f)

    for threat_category in disconnect['categories']:
        # threat_category is 'Advertising' or 'Content' etc
        for entry in disconnect['categories'][threat_category]: # list, not dict
            # entry is a dict like {'33Across': {'http://33across.com/': ['33across.com']}}
            for entity in entry: # dict
                # entity would be '33Across' from above
                for url in entry[entity]:
                    # http://33across.com/ from above
                    if 'http' not in url:
                        continue
                    for domain in entry[entity][url]: # list, not dict
                        # domain would be 33across.com from above
                        if domain in disconnect_domains:
                            disconnect_domains[domain]['categories'].append(threat_category)
                        else:
                            disconnect_domains[domain] = {'parent': entity,
                                'categories': [threat_category],
                                'parent_url': url}

    return disconnect_domains

# TODO: Need to handle cases of IPs and localhost references
def trim_url(url):
    return '.'.join(extract(url)[1:])

logging.basicConfig(level=logging.INFO)

logging.info('Parsing Disconnect blocklist...')
disconnect_domains = parseDisconnectList(sys.argv[2])
logging.info(f'Blocklist parsed, {len(disconnect_domains)} entries added')

with closing(sqlite3.connect(sys.argv[1])) as con:
    # con.row_factory = sqlite3.Row
    with closing(con.cursor()) as cur:
        columns = ['tld TEXT','is_third_party INTEGER DEFAULT 0','is_tracker INTEGER DEFAULT 0','tracker_info TEXT']
        for column in columns:
            try:
                logging.info(f'Adding {column} column...')
                cur.execute('ALTER TABLE http_requests ADD ' + column)
            except sqlite3.Error:
                logging.warning(f'{column} column already exists')
        update_data = []
        for row in cur.execute('SELECT id, url, top_level_url FROM http_requests'):
            (rid, url, top_level_url) = row
            url = trim_url(url)
            top_level_url = trim_url(top_level_url)
            # import pdb;pdb.set_trace()
            if top_level_url not in url:
                third_party = 1
                url = '.'.join(extract(url)[1:])
                try:
                    tracker_info = disconnect_domains[url]
                    is_tracker = 1
                    logging.debug(f'Tracker detected: {url}')
                except KeyError:
                    tracker_info = None
                    is_tracker = 0
                    logging.debug(f'Benign 3rd party request: {url}')
                update_data.append((url, third_party, is_tracker, json.dumps(tracker_info), rid))
            else:
                pass
                # logging.info(f'First party request: {url}')
        cur.executemany('''UPDATE http_requests SET 
        tld = ?, is_third_party = ?, is_tracker = ?, tracker_info = ?
        WHERE id = ?''', update_data)
        con.commit()
        logging.info(f'Finished. {con.total_changes} rows updated.')
