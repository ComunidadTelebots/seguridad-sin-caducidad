import json
import tempfile
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import Handler, connect


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / 'test.sqlite3'
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, database=self.database))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path='/api/community/stats', data=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        req = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            response = urlopen(req)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def support(self, **values):
        body = {'email': 'example@example.test', 'country': 'ES', 'technology': 'windows-10'}
        body.update(values)
        return self.request('/api/collections/supports/records', body)

    def test_totals_duplicates_and_persistence(self):
        self.assertEqual(self.request()[1]['total'], 0)
        self.assertEqual(self.support()[0], 201)
        self.assertEqual(self.support(email='EXAMPLE@example.test')[0], 400)
        self.assertEqual(self.support(email='second@example.test', country='FR', technology='')[0], 201)
        data = self.request()[1]
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['countries']['ES'], 1)
        self.assertEqual(data['countries']['FR'], 1)
        self.assertEqual(data['technologies']['windows-10'], 1)
        self.assertEqual(sum(data['countries'].values()), data['total'])
        self.assertNotIn('email', json.dumps(data))
        with connect(self.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM supports').fetchone()[0], 2)
            self.assertNotIn('@', db.execute('SELECT email_hash FROM supports LIMIT 1').fetchone()[0])

    def test_validation_and_origin(self):
        for values in [{'country': ''}, {'country': 'ZZ'}, {'email': 'bad'}, {'technology': 'fake'}, {'email': None}]:
            self.assertEqual(self.support(**values)[0], 400)
        status, _ = self.request('/api/collections/supports/records', {'email':'a@b.test','country':'ES'}, 'https://other.example')
        self.assertEqual(status, 403)
        self.assertEqual(self.request()[1]['total'], 0)


if __name__ == '__main__':
    unittest.main()
