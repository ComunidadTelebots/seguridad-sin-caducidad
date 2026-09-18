import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from test_server import CommunityTests
from server import connect

source = Path(os.environ.get('MOONBOT_REPO', Path(__file__).parent / 'integrations/moonbot'))
plugin_path = source / 'plugins/right_to_updates.py' if (source / 'plugins').exists() else source / 'right_to_updates.py'
spec = importlib.util.spec_from_file_location('right_to_updates', plugin_path)
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


class FakeBot:
    bot_username = 'cintiabot'

    def __init__(self):
        self.messages = []

    def api_call(self, method, payload):
        self.messages.append((method, payload))
        return {'ok': True}

    def send_msg(self, chat_id, text):
        self.messages.append(('sendMessage', {'chat_id': chat_id, 'text': text}))


class MoonbotTests(CommunityTests):
    def setUp(self):
        super().setUp()
        self.config = {'secret': 'test-only-' * 6, 'bot_username': 'cintiabot', 'api_url': self.base}
        self.config_patch = patch('server.moonbot_configuration', return_value=self.config)
        self.handler_patch = patch('moonbot_bridge.configuration', return_value=self.config)
        self.plugin_patch = patch.object(plugin, 'config', return_value=self.config)
        for item in (self.config_patch, self.handler_patch, self.plugin_patch):
            item.start()
            self.addCleanup(item.stop)

    def challenge(self):
        status, data = self.request('/api/telegram/challenge', {'country': 'ES', 'technology': 'windows-10'})
        self.assertEqual(status, 201)
        self.assertTrue(data['url'].startswith('https://t.me/cintiabot?start=rtu_'))
        return data['token']

    def test_plugin_end_to_end_and_duplicate(self):
        token = self.challenge()
        bot = FakeBot()
        self.assertTrue(plugin.handle_command(bot, 1234, 1234, '/start rtu_' + token, 'User'))
        self.assertEqual(self.request()[1]['total'], 0)
        markup = json.loads(bot.messages[-1][1]['reply_markup'])
        callback = markup['inline_keyboard'][0][0]['callback_data']
        self.assertLessEqual(len(callback.encode()), 64)
        self.assertTrue(plugin.handle_callback(bot, 1234, 1234, 'test', callback, 'callback1'))
        self.assertEqual(self.request()[1]['total'], 1)
        self.assertEqual(self.request()[1]['technologies']['windows-10'], 1)
        self.assertEqual(self.request('/api/telegram/status', {'token':token})[1]['state'], 'confirmed')
        plugin.handle_callback(bot, 1234, 1234, 'test', callback, 'callback2')
        self.assertEqual(self.request()[1]['total'], 1)
        other = self.challenge()
        plugin.handle_command(bot, 1234, 1234, '/start rtu_' + other, 'User')
        plugin.handle_callback(bot, 1234, 1234, 'test', 'rtu_ok_' + other, 'callback3')
        self.assertEqual(self.request('/api/telegram/status', {'token':other})[1]['state'], 'duplicate')
        self.assertEqual(self.request()[1]['total'], 1)

    def test_auth_owner_expiry_and_no_early_count(self):
        token = self.challenge()
        body = {'token':token, 'user_id':1234, 'bot_username':'cintiabot'}
        self.assertEqual(self.request('/api/moonbot/confirm', body)[0], 403)
        self.assertIn('error', plugin.bridge(FakeBot(), 'confirm', token, 1234))
        self.assertEqual(plugin.bridge(FakeBot(), 'prepare', token, 1234)['state'], 'pending')
        self.assertIn('error', plugin.bridge(FakeBot(), 'confirm', token, 9999))
        with connect(self.database) as db:
            db.execute('UPDATE telegram_challenges SET expires=0')
        self.assertEqual(plugin.bridge(FakeBot(), 'confirm', token, 1234)['error'], 'expired')
        self.assertEqual(self.request()[1]['total'], 0)

    def test_existing_commands_and_private_chat(self):
        bot = FakeBot()
        for command in ['/start', '/help', '/proxy', '/start another_flow']:
            self.assertFalse(plugin.handle_command(bot, 1234, 1234, command, 'User'))
        self.assertFalse(plugin.handle_callback(bot,1234,1234,'test','req_proxy','cb'))
        self.assertEqual(bot.messages, [])
        token = self.challenge()
        plugin.handle_command(bot, -100,1234,'/start rtu_'+token,'User')
        self.assertNotIn('reply_markup',bot.messages[-1][1])
        self.assertEqual(self.request()[1]['total'],0)

    def test_config_does_not_expose_secret(self):
        status, data = self.request('/api/telegram/config')
        self.assertEqual(status,200)
        self.assertEqual(data, {'enabled':True,'username':'cintiabot'})
