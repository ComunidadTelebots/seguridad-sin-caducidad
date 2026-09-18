"""Local preview with persistent, separate community supports (no production writes)."""
import argparse
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from moonbot_bridge import configuration as moonbot_configuration, handle as moonbot_handle

ROOT = Path(__file__).resolve().parent
COUNTRIES = set('AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE'.split())
TECHNOLOGIES = {t['id'] for t in json.loads((ROOT / 'web/technologies.json').read_text(encoding='utf-8'))}


@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=10)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS supports (email_hash TEXT PRIMARY KEY, country TEXT NOT NULL, technology TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            yield db
    finally:
        db.close()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, database, **kwargs):
        self.database = database
        super().__init__(*args, directory=str(ROOT / 'web'), **kwargs)

    def json_response(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/api/telegram/config':
            config = moonbot_configuration()
            self.json_response(200, {'enabled': bool(config), 'username': config.get('bot_username', '')})
            return
        if self.path.split('?')[0] == '/api/community/stats':
            with connect(self.database) as db:
                countries = dict(db.execute('SELECT country, count(*) FROM supports GROUP BY country'))
                technologies = dict(db.execute('SELECT technology, count(*) FROM supports WHERE technology IS NOT NULL GROUP BY technology'))
            self.json_response(200, {
                'mode': 'local', 'total': sum(countries.values()),
                'countries': {c: countries.get(c, 0) for c in sorted(COUNTRIES)},
                'technologies': {t: technologies.get(t, 0) for t in sorted(TECHNOLOGIES)},
                'technologyVoting': True,
            })
        elif self.path.startswith('/api/'):
            self.json_response(404, {'error': 'not_found'})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path in {'/api/telegram/challenge', '/api/telegram/status', '/api/moonbot/prepare', '/api/moonbot/confirm'}:
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                self.json_response(403, {'error': 'origin'})
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 4096 or self.headers.get_content_type() != 'application/json':
                    raise ValueError()
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError()
                with connect(self.database) as db:
                    db.execute('BEGIN IMMEDIATE')
                    status, result = moonbot_handle(self.path, body, self.headers.get('Authorization', ''), db, COUNTRIES, TECHNOLOGIES)
                self.json_response(status, result)
            except (ValueError, TypeError, AttributeError):
                self.json_response(400, {'error': 'validation'})
            return
        if self.path != '/api/collections/supports/records':
            self.json_response(404, {'error': 'not_found'})
            return
        # Local endpoint: JSON only, same origin, bounded body. No CORS access.
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            self.json_response(403, {'error': 'origin'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096 or self.headers.get_content_type() != 'application/json':
                raise ValueError()
            body = json.loads(self.rfile.read(size))
            email = body.get('email', '').strip().casefold()
            country = body.get('country')
            technology = body.get('technology') or None
            if (len(email) > 254 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email)
                    or country not in COUNTRIES or (technology and technology not in TECHNOLOGIES)):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            self.json_response(400, {'error': 'validation'})
            return
        try:
            with connect(self.database) as db:
                db.execute('INSERT INTO supports(email_hash,country,technology) VALUES(?,?,?)',
                           (hashlib.sha256(email.encode()).hexdigest(), country, technology))
        except sqlite3.IntegrityError:
            self.json_response(400, {'data': {'email': {'code': 'validation_not_unique'}}})
            return
        self.json_response(201, {'mode': 'local'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--database', type=Path, default=ROOT / '.local/supports.sqlite3')
    args = parser.parse_args()
    args.database.parent.mkdir(parents=True, exist_ok=True)
    with connect(args.database):
        pass
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, database=args.database))
    print(f'Local preview: http://127.0.0.1:{args.port} (local supports only)', flush=True)
    server.serve_forever()
