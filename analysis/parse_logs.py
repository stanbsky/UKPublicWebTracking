from tldextract import extract
from contextlib import closing
from pathlib import Path
import argparse
import sqlite3
import re
import json
import logging

class LogParser:

    browsers = {}
    commit_data = {}

    def __init__(self, log, db, table_name, redirect_list):
        logging.basicConfig(level=logging.INFO)
        self.log = log
        self.redirects = None
        if redirect_list:
            with open(redirect_list, 'r') as f:
                self.redirects = json.load(f)
        self.db = db
        self.table_name = table_name
        url_pattern = r'(https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*))'
        self.matchers = {
            self._get_cmd:
            'BROWSER (\d{7,}).*GetCommand\(' + url_pattern,
            self._new_visit:
            'Starting to work on CommandSequence with visit_id (\d{10,}) on browser with id (\d{7,})',
            self._accept_found:
            'accept_button_found, website=' + url_pattern + ", id=(.*), call_to_action=b?'(.*)'",
            self._accept_not_found:
            'accept_button_not_found, website=(' + url_pattern + ')',
            self._cmp_found:
            'BROWSER (\d{7,}): driver: console.log: "CMP Detected: " "(.*)"',
            self._timeout:
            'BROWSER (\d{7,}): (Timeout while executing command, AcceptCookiesCommand)'
        }

    def _get_cmd(self, match):
        browser_id, url = match.groups()[:2]
        try:
            browser = self.browsers[browser_id]
        except KeyError:
            browser = {'url': None, 'visit_id': None}
            self.browsers[browser_id] = browser
        browser['url'] = url

    def _new_visit(self, match):
        visit_id, browser_id = match.groups()
        try:
            browser = self.browsers[browser_id]
        except KeyError:
            browser = {'url': None, 'visit_id': None}
            self.browsers[browser_id] = browser
        browser['visit_id'] = visit_id

    def _accept_found(self, match):
        url = match.groups()[0]
        css_id, cta = match.groups()[-2:]
        visit_data = self._get_visit_data_by_url(url)
        self._add_to_commit(visit_data, accept_found=1, css_id=css_id, accept_cta=cta)
    
    def _accept_not_found(self, match):
        url = match.groups()[0]
        visit_data = self._get_visit_data_by_url(url)
        self._add_to_commit(visit_data, accept_found=0)

    def _cmp_found(self, match):
        browser_id, cmp = match.groups()
        visit_data = (browser_id, *self.browsers[browser_id].values())
        self._add_to_commit(visit_data, cmp=cmp)

    def _timeout(self, match):
        browser_id, error = match.groups()
        visit_data = (browser_id, *self.browsers[browser_id].values())
        self._add_to_commit(visit_data, error=error)

    # def _get_visit_data_by_browser_id(self, browser_id):

    def _get_visit_data_by_url(self, url):
        for browser_id, browser_entry in self.browsers.items():
            if extract(browser_entry['url'])[1:] == extract(url)[1:]:
                return (browser_id, browser_entry['url'], browser_entry['visit_id'])
        # Couldn't find browser in self.browsers, check redirects
        for entry in self.redirects:
            visit_id, original_url, redirected_url = entry
            for browser_id, browser_entry in self.browsers.items():
                if browser_entry['visit_id'] == visit_id:
                    # We found a redirected url, but let's be paranoid...
                    if redirected_url not in url:
                        logging.warning(f'Redirected url {redirected_url} not the same as accept_cookies {url}')
                    if original_url != browser_entry['url']:
                        logging.warning(f'Original GetCommand url {browser_entry["url"]} not the same as redirect url {redirected_url}')
                    return (browser_id, browser_entry['url'], browser_entry['visit_id'])
        logging.error(f"Couldn't find a browser visiting the url {url}!")
        return (None, url, None)

    def _add_to_commit(self, visit_data, **kwargs):
        browser_id, url, visit_id = visit_data
        try:
            row = self.commit_data[visit_id]
        except KeyError:
            row = {}
            self.commit_data[visit_id] = row
        row['visit_id'] = visit_id
        row['browser_id'] = browser_id
        row['url'] = url
        # if 'error' in kwargs.keys():
        #     import pdb;pdb.set_trace()
        default_values = {
            'visit_id': None,
            'browser_id': None,
            'url': None,
            'accept_found': 0,
            'css_id': None,
            'accept_cta': None,
            'banner_selector': None,
            'cmp': None,
            'error': None
        }
        default_values.update(row)
        default_values.update(kwargs)
        self.commit_data[visit_id] = default_values

    def parse(self):
        with open(self.log, 'r') as f:
            for line in f:
                matches = {}
                for action, pattern in self.matchers.items():
                    match = re.search(pattern, line, re.I)
                    if match:
                        logging.info(f'Calling {action.__name__} with match {match}')
                        action(match)
                        break

    def _freeze_commit_data(self):
        data = []
        for _, values in self.commit_data.items():
            row = tuple(values.values())
            data.append(row)
        self.commit_data = data

    def commit(self):
        self._freeze_commit_data()
        with closing(sqlite3.connect(self.db)) as con:
            # TODO: Ask for permission / check args before overwriting
            con.executescript(
                f'DROP TABLE IF EXISTS {self.table_name};'
                f'CREATE TABLE {self.table_name} ('
                f'visit_id INT, browser_id INT, url TEXT, accept_found INT,'
                f'css_id TEXT, accept_cta TEXT, banner_selector TEXT, cmp TEXT, error TEXT)'
            )
            con.executemany(
                f'INSERT INTO {self.table_name}'
                f'(visit_id, browser_id, url, accept_found, css_id, accept_cta,'
                f'banner_selector, cmp, error) VALUES (?,?,?,?,?,?,?,?,?)', self.commit_data
            )
            con.commit()
            logging.info(f'Finished. {con.total_changes} rows updated.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse crawl log and record interactions with cookie banners and CMPs to a database.')
    parser.add_argument('log', type=Path)
    parser.add_argument('--db', type=Path, default=Path('../data/parsed_logs.sqlite'))
    parser.add_argument('--table', type=ascii)
    parser.add_argument('--redirects', type=Path)
    args = parser.parse_args()

    if not args.table:
        args.table = args.log.stem

    logs = LogParser(args.log, args.db, args.table, args.redirects)
    logs.parse()
    logs.commit()
