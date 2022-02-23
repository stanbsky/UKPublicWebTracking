from functools import partial
from pathlib import Path
from bs4 import BeautifulSoup as bs
from contextlib import closing
from tldextract import extract
import argparse
import sqlite3
import json
import re
import logging
import time

def setup_logger(log_dir):
    name = Path(__file__).stem
    logging.basicConfig(
        level=logging.INFO,
        format=f"%(asctime)s | {name} | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_dir.joinpath(f'{name}.log')),
            logging.StreamHandler()
        ]
    )
    global logger
    logger = logging.getLogger(__name__)

def _is_third_party(href, tld):
    domain = extract(href)
    if domain.domain and domain != tld and domain.suffix != 'gov.uk' and domain.suffix != 'nhs.uk':
        return True
    else:
        return False

def _third_party_href(tag, is_third_party):
    return tag.name == 'a' and tag.has_attr('href') and is_third_party(tag['href'])

def has_matching_text(tag, r):
    for e in [tag.string, tag.previous_sibling, tag.next_sibling]:
        if r.search(str(e)):
            return tag
    return None

def find_attributions_in_source(content, tld):
    # Add spaces before+after the keyword?
    # Test for presence in the lower part of the viewport?
    # Negative test for "website accessibility"?
    # Lots of accessibility statements getting caught
    r = re.compile('.*(built|website|design|designed|developed|development|powered|web technology)+.*', re.IGNORECASE)
    bs_data = bs(content, 'lxml')
    is_third_party = partial(_is_third_party, tld=tld)
    third_party_href = partial(_third_party_href, is_third_party=is_third_party)
    attributions = []
    tags = bs_data.find_all(third_party_href)
    if tags:
        for tag in tags:
            if has_matching_text(tag, r):
                attributions.append({'href': '.'.join(extract(tag['href'])[1:]), 'parent': str(tag.parent)})
        return attributions if attributions else None
    else:
        return None

def find_attributions(db):
    commit_data = []
    with closing(sqlite3.connect(db)) as con:
        con.row_factory = sqlite3.Row
        for row in con.execute('SELECT rowid, url, content_blob FROM request_data WHERE content_blob IS NOT NULL'):
            tld = '.'.join(extract(row['url'])[1:])
            logger.info(f'Parsing {tld} ...')
            attributions = find_attributions_in_source(row['content_blob'], tld)
            if attributions:
                commit_data.append((len(attributions), json.dumps(attributions), row['rowid']))
                logger.info(f'Found {len(attributions)} attributions')
            else:
                commit_data.append((None, None, row['rowid']))
                logger.info('No attributions found')
        try:
            con.execute('ALTER TABLE request_data ADD COLUMN attrib_num INTEGER')
            con.execute('ALTER TABLE request_data ADD COLUMN attrib_data TEXT')
        except:
            logger.warning('Table request_data already contains attributions columns!')
        con.executemany('UPDATE request_data SET attrib_num = ?, attrib_data = ? WHERE rowid = ?', commit_data)
        con.commit()
        logger.info(f'Saved attributions for {con.total_changes} websites')

# def find_attributions_json(row):
#     return json.dumps(find_attributions(row))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find possible website attributions.')
    parser.add_argument('db', type=Path)
    parser.add_argument('--logdir', type=Path, default=Path('./logs/'))
    args = parser.parse_args()

    setup_logger(args.logdir)
    tic = time.perf_counter()
    find_attributions(args.db)
    toc = time.perf_counter()
    logger.info(f'Completed in {toc - tic:0.1f} seconds')
