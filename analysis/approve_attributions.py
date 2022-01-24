import os
import sys
import sqlite3
from contextlib import closing
from json import loads
from pprint import pprint as pp
from tldextract import extract

def check_for_more(con, attrib):
    others = con.execute(f"SELECT rowid FROM attrib WHERE attrib_data LIKE '%\"href\": \"{attrib}\"%' AND attrib_url IS NULL").fetchall()
    sites_updated = len(others)
    if others:
        for row in others:
            commit(con, (attrib, row[0]))
    return sites_updated

def commit(con, commit_data):
    con.execute('UPDATE attrib SET attrib_url = ? WHERE rowid = ?', commit_data)
    con.commit()

def hr():
    print(80*'-')

def approve_attributions(db):
    with closing(sqlite3.connect(db)) as con:
        with closing(con.cursor()) as cur:
            con.row_factory = sqlite3.Row
            bad_candidates = ['twitter.com','t.co','youtube.com','vimeo.com','google.com','google.co.uk','facebook.com']
            rows = con.execute("SELECT rowid, url, attrib_data FROM attrib WHERE attrib_url IS NULL AND attrib_data IS NOT NULL").fetchall()
            rows_left = len(rows)
            last_update = 0
            for row in rows:
                os.system('clear')
                if last_update:
                    print(f'{last_update} site attributions written.\n')
                print(f'{rows_left} websites are awaiting labelling.\n\n')
                print(f"Site: {row['url']}\n")
                data = loads(row['attrib_data'])
                candidates = []
                for candidate in data:
                    url = candidate['href']
                    if url in bad_candidates:
                        # The usual third-party links that are not attributions...
                        continue
                    if url in row['url']:
                        # If we're here, find_attributions messed up...
                        continue
                    parts = extract(url)
                    if not parts.domain or not parts.suffix:
                        # This is not a proper url
                        continue
                    candidates.append(candidate)
                    hr()
                    print(f"Candidate {len(candidates)}:\n")
                    pp(candidate)
                if candidates:
                    vote = int(input('\nEnter candidate number to accept, or 0 if none are applicable: '))
                else:
                    vote = 0
                if vote:
                    good_attrib = data[vote-1]['href']
                    # No need to commit, check_for_more will mark this one and others
                    last_update = check_for_more(con, good_attrib)
                    rows_left -= last_update
                else:
                    commit_data = ('--', row['rowid'])
                    commit(con, commit_data)
                    rows_left -= 1

if __name__ == "__main__":
    approve_attributions(sys.argv[1])
