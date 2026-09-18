"""One-use voting challenges. Telegram credentials remain exclusively in Moonbot."""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path

CONFIG = Path(__file__).resolve().parent / '.local/moonbot.json'


def configuration():
    path = Path(os.environ.get('RTU_BRIDGE_CONFIG', str(CONFIG)))
    try:
        config = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    username = config.get('bot_username', '').lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9_]{5,32}', username) or len(config.get('secret', '')) < 32:
        return {}
    return {**config, 'bot_username': username}


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS telegram_challenges (
        digest TEXT PRIMARY KEY, country TEXT NOT NULL, technology TEXT,
        expires INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'pending', user_hash TEXT)''')


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def handle(path, body, authorization, db, countries, technologies, config=None):
    config = configuration() if config is None else config
    if not config:
        return 503, {'error': 'telegram_unavailable'}
    schema(db)
    now = int(time.time())
    if path.startswith('/api/moonbot/'):
        if not hmac.compare_digest(authorization, 'Bearer ' + config['secret']):
            return 403, {'error': 'unauthorized'}
        if body.get('bot_username', '').lstrip('@').lower() != config['bot_username'].lower():
            return 403, {'error': 'wrong_bot'}
        uid = body.get('user_id')
        if not isinstance(uid, int) or isinstance(uid, bool) or uid <= 0:
            return 400, {'error': 'invalid_user'}
        user_hash = 'telegram:' + digest(str(uid))
    if path == '/api/telegram/challenge':
        country, technology = body.get('country'), body.get('technology') or None
        if country not in countries or (technology and technology not in technologies):
            return 400, {'error': 'validation'}
        db.execute('DELETE FROM telegram_challenges WHERE expires < ?', (now - 86400,))
        if db.execute('SELECT count(*) FROM telegram_challenges WHERE expires > ?', (now,)).fetchone()[0] >= 1000:
            return 429, {'error': 'busy'}
        token = secrets.token_urlsafe(24)
        db.execute('INSERT INTO telegram_challenges(digest,country,technology,expires) VALUES(?,?,?,?)',
                   (digest(token), country, technology, now + 900))
        return 201, {'token': token, 'url': f'https://t.me/{config["bot_username"]}?start=rtu_{token}', 'expiresIn': 900}
    token = body.get('token', '')
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32}', token):
        return 400, {'error': 'invalid_token'}
    row = db.execute('SELECT country,technology,expires,state,user_hash FROM telegram_challenges WHERE digest=?', (digest(token),)).fetchone()
    if not row:
        return 404, {'error': 'not_found'}
    country, technology, expires, state, owner = row
    if expires < now:
        return 410, {'error': 'expired'}
    if path == '/api/telegram/status':
        return 200, {'state': state}
    if owner and owner != user_hash:
        return 403, {'error': 'different_user'}
    if path == '/api/moonbot/prepare':
        if state != 'pending':
            return 200, {'state': state}
        db.execute('UPDATE telegram_challenges SET user_hash=? WHERE digest=?', (user_hash, digest(token)))
        return 200, {'state': state, 'country': country, 'technology': technology}
    if path == '/api/moonbot/confirm':
        if owner != user_hash:
            return 403, {'error': 'not_prepared'}
        if state != 'pending':
            return 200, {'state': state}
        exists = db.execute('SELECT 1 FROM supports WHERE email_hash=?', (user_hash,)).fetchone()
        state = 'duplicate' if exists else 'confirmed'
        if not exists:
            db.execute('INSERT INTO supports(email_hash,country,technology) VALUES(?,?,?)', (user_hash, country, technology))
        db.execute('UPDATE telegram_challenges SET state=? WHERE digest=?', (state, digest(token)))
        return 200, {'state': state}
    return 404, {'error': 'not_found'}
