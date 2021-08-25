import sys
import sqlite3
from contextlib import closing

with closing(sqlite3.connect(sys.argv[1])) as con:
    with closing(con.cursor()) as cur:
        cur.executescript("""
            DROP TABLE IF EXISTS request_data;
            CREATE TABLE request_data AS
	        SELECT http_requests.id AS request_id,
                http_responses.id AS response_id,
                http_requests.visit_id,
                http_requests.top_level_url AS url,
                http_requests.method,
                http_requests.headers AS request_headers,
                http_responses.response_status,
                http_responses.response_status_text,
                http_responses.headers AS response_headers,
                http_responses.content_hash
                FROM http_requests INNER JOIN http_responses
                ON http_requests.url = http_responses.url
                WHERE http_requests.resource_type = 'main_frame';
        """)
