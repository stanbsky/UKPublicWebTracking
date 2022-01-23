import os
import sys
import sqlite3
from contextlib import closing
from json import loads
from pprint import pprint as pp

def commit(con, commit_data):
    con.executemany('UPDATE attrib SET attrib_url = ? WHERE rowid = ?', commit_data)
    con.commit()

if __name__ == "__main__":
    with closing(sqlite3.connect(sys.argv[1])) as con:
        with closing(con.cursor()) as cur:
            con.row_factory = sqlite3.Row
            commit_data = []
            bad_hrefs = []
            good_hrefs = []
            rows = con.execute("SELECT rowid, url, attrib_data FROM attrib WHERE attrib_url IS NULL AND attrib_data IS NOT NULL").fetchall()
            for row in rows:
                os.system('clear')
                print('Accepted candidates:\n')
                print(commit_data, '\n', '-'*16, '\n')

                print(f"Site: {row['url']}\n")
                data = loads(row['attrib_data'])
                for idx, val in enumerate(data):
                    if val['href'] in bad_hrefs:
                        continue
                    if val['href'] in good_hrefs:
                        commit_data.append((data[vote-1]['href'], row['rowid']))
                        continue
                    print(f"Candidate {idx+1}:\n")
                    pp(val)
                vote = int(input('\nEnter candidate number to accept, or 0 if none are applicable: '))
                if vote:
                    commit_data.append((data[vote-1]['href'], row['rowid']))
                    good_hrefs.append(data[vote-1]['href'])
                else:
                    commit_data.append(('--', row['rowid']))
                if len(commit_data) >= 100:
                    # Process in batches of 100, just in case of issues
                    commit(con, commit_data)
                    commit_data = []
            
            commit(con, commit_data)
            print(f'Updated attributions for {con.total_changes} websites')
