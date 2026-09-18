"""Moonbot plugin: use the existing bot.api_call; never access or copy bot tokens."""
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def config():
    try:
        return json.loads(Path(os.getenv('RTU_BRIDGE_CONFIG', 'data/right_to_updates_bridge.json')).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def bridge(bot, action, token, uid):
    settings = config()
    base = settings.get('api_url', '').rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')):
        return {'error': 'configuration'}
    if len(settings.get('secret', '')) < 32:
        return {'error': 'configuration'}
    data = json.dumps({'token':token, 'user_id':int(uid), 'bot_username':getattr(bot,'bot_username','')}).encode()
    req = Request(base + '/api/moonbot/' + action, data=data,
                  headers={'Content-Type':'application/json', 'Authorization':'Bearer '+settings['secret']})
    try:
        with urlopen(req, timeout=8) as response:
            return json.load(response)
    except HTTPError as error:
        # Do not log URLs, request headers or response bodies containing secrets.
        return {'error':'expired' if error.code == 410 else 'unavailable'}
    except (URLError, TimeoutError, ValueError, OSError):
        return {'error':'unavailable'}


def handle_command(bot, cid, uid, text, rank):
    match = re.fullmatch(r'/start(?:@[A-Za-z0-9_]+)? rtu_([A-Za-z0-9_-]{32})', text.strip())
    if not match:
        return False
    if str(cid) != str(uid) or int(uid) <= 0:
        bot.send_msg(cid, 'Abre el enlace de votación en un chat privado con el bot.')
        return True
    result = bridge(bot, 'prepare', match[1], uid)
    if result.get('state') == 'pending':
        technology = result.get('technology') or 'Solo apoyar la iniciativa'
        catalog_path = Path(__file__).with_name('right_to_updates_catalog.json')
        try:
            catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
            technology = next((item['name'] for item in catalog if item['id'] == technology), technology)
        except (OSError, ValueError):
            pass
        bot.api_call('sendMessage', {
            'chat_id':cid,
            'text':f'Confirma tu apoyo a Right to Updates\n\nPaís: {result["country"]}\nTecnología: {technology}\n\nSolo se contará al pulsar Confirmar. Un apoyo por cuenta de Telegram. No es una firma oficial. Si no has solicitado este voto, ignora el mensaje. El enlace caduca en 15 minutos.',
            'reply_markup':json.dumps({'inline_keyboard':[[{'text':'Confirmar mi voto','callback_data':'rtu_ok_'+match[1]}]]}),
        })
    else:
        bot.send_msg(cid, 'Este enlace ya se ha utilizado o no está disponible. Vuelve a la web para comprobar tu voto o solicitar un enlace nuevo.')
    return True


def handle_callback(bot, cid, uid, uname, data, cbq_id):
    match = re.fullmatch(r'rtu_ok_([A-Za-z0-9_-]{32})', data or '')
    if not match:
        return False
    if str(cid) != str(uid) or int(uid) <= 0:
        return True
    result = bridge(bot, 'confirm', match[1], uid)
    state = result.get('state')
    text = ('Tu voto está confirmado. Ya cuenta en el mapa y en la tecnología elegida.' if state == 'confirmed'
            else 'Esta cuenta de Telegram ya tiene un voto. No se ha sumado otro.' if state == 'duplicate'
            else 'No se ha podido confirmar. Vuelve a la web y solicita un enlace nuevo si ha caducado.')
    bot.send_msg(cid, text)
    # Moonbot acknowledges the callback after dispatching its plugins.
    return True
