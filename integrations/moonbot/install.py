"""Install the additive Moonbot plugin and its narrow /start route."""
import argparse
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('moonbot', type=Path)
args = parser.parse_args()
target = args.moonbot.resolve()
core = target / 'moon_multibot.py'
original = core.read_bytes()
newline = b'\r\n' if b'\r\n' in original else b'\n'
marker = b'        # Right to Updates: handle only voting deep links; preserve all other commands.'
anchor = b'        if raw_cmd in ["/start", "/inicio", "/panel", "/menu"] and (self.bot_username or "").lower() == "cintiabot":'
if marker not in original:
    if original.count(anchor) != 1:
        raise SystemExit('Moonbot command layout changed; no files modified.')
    addition = '\n'.join([
        marker.decode(),
        '        if raw_cmd == "/start" and args and args[0].startswith("rtu_"):',
        '            if not self._run_plugin_command(cid, uid, text, rk):',
        '                self.send_msg(cid, "La verificación de votos no está disponible en este bot.")',
        '            return True', '', '',
    ]).encode('utf-8').replace(b'\n', newline)
    core.write_bytes(original.replace(anchor, addition + anchor))
plugin = target / 'plugins/right_to_updates.py'
plugin.write_bytes((ROOT / 'integrations/moonbot/right_to_updates.py').read_bytes())
(target / 'plugins/right_to_updates_catalog.json').write_bytes((ROOT / 'web/technologies.json').read_bytes())
ignore = target / '.gitignore'
rule = b'!plugins/right_to_updates_catalog.json'
if rule not in ignore.read_bytes():
    with ignore.open('ab') as stream:
        stream.write(newline + rule + newline)
config_path = ROOT / '.local/moonbot.json'
config_path.parent.mkdir(exist_ok=True)
if not config_path.exists():
    config_path.write_text(json.dumps({'bot_username':'cintiabot', 'api_url':'http://127.0.0.1:8080', 'secret':secrets.token_urlsafe(48)}, indent=2), encoding='utf-8')
(target / 'data').mkdir(exist_ok=True)
dest_config = target / 'data/right_to_updates_bridge.json'
if dest_config.exists() and dest_config.read_bytes() != config_path.read_bytes():
    raise SystemExit('Existing Moonbot bridge configuration differs; left unchanged.')
dest_config.write_bytes(config_path.read_bytes())
print('Installed additive voting route, plugin, catalog and private local bridge configuration. No bot tokens accessed.')
