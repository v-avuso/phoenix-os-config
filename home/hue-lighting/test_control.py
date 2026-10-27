import http.client
import json
import struct
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from http.server import HTTPServer
import control


class Controls(unittest.TestCase):
    def test_start_preserves_remembered_source_and_owns_named_app_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'.config/huenicorn/config.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'boundBackendIP': '127.0.0.1', 'restServerPort': 8215,
                                        'restoreToken': 'old-connector', 'credentials': {'key': 'private'}}))
            c = control.Controller('/fixed/huenicorn')
            with patch.object(control.Path, 'home', return_value=root), \
                    patch.object(control.socket, 'socket') as socket, \
                    patch.object(control.subprocess, 'Popen') as launch:
                socket.return_value.__enter__.return_value.connect_ex.return_value = 1
                c.start()
                self.assertEqual(json.loads(path.read_text())['restoreToken'], 'old-connector')
                # Upstream saves a newly approved source; later starts must retain it.
                c.stop()
                replaced = json.loads(path.read_text())
                replaced['restoreToken'] = 'replacement-source'
                path.write_text(json.dumps(replaced))
                launch.return_value.poll.return_value = 1
                c.start()
            config = json.loads(path.read_text())
            self.assertEqual(config['restoreToken'], 'replacement-source')
            self.assertEqual(config['credentials'], {'key': 'private'})
            argv = launch.call_args.args[0]
            self.assertEqual(argv[:4], ['systemd-run', '--user', '--scope', '--quiet'])
            self.assertTrue(argv[5].startswith('app-org.phoenix.HueSync-'))
            self.assertEqual(argv[-2:], ['--', '/fixed/huenicorn'])

    def test_choose_screen_stops_before_resetting_only_restore_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root/'.config/huenicorn/config.json'
            config_path.parent.mkdir(parents=True)
            config = {'restoreToken': 'private-token', 'credentials': {'key': 'private'},
                      'boundBackendIP': '127.0.0.1', 'restServerPort': 8215}
            config_path.write_text(json.dumps(config))
            c = control.Controller('/unused')
            c.process = Mock()
            c.process.poll.return_value = None
            def stopped():
                self.assertEqual(json.loads(config_path.read_text()), config)
                c.process = None
            with patch.object(control.Path, 'home', return_value=root), \
                    patch.object(c, 'stop', side_effect=stopped) as stop, \
                    patch.object(c, 'start') as start:
                c.choose_screen()
            stop.assert_called_once()
            start.assert_called_once()
            self.assertEqual(json.loads(config_path.read_text()),
                             {k: v for k, v in config.items() if k != 'restoreToken'})
            self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)

    def test_off_cannot_reset_capture_permission(self):
        c = control.Controller('/unused')
        with patch.object(control.Path, 'home') as home:
            with self.assertRaises(ValueError):
                c.choose_screen()
            home.assert_not_called()

    def test_level_updates_all_active_channels_and_saves(self):
        c = control.Controller('/unused')
        c.process = Mock()
        c.process.poll.return_value = None
        channels = [{'channelId': n, 'active': n != 9} for n in (0, 1, 2, 3, 4, 5, 9)]
        calls = []
        def api(path, data=None, method='GET'):
            calls.append((path, data, method))
            return channels if path == '/api/channels' else {'succeeded': True}
        with patch.object(control, 'native', side_effect=api):
            c.set_level(.5)
        updates = [x for x in calls if 'setChannelGammaFactor' in x[0]]
        self.assertEqual(len(updates), 6)
        self.assertTrue(all(x[1] == {'gammaFactor': .5} for x in updates))
        self.assertEqual(calls[-1][0], '/api/saveProfile')

    def test_boost_reaches_full_native_brightness_without_lighting_black(self):
        # Native Huenicorn uses float brightness ** (2 ** (-2 * gamma)).
        for level, gamma in [(-1, -1), (0, 0), (.5, .5), (.75, 1), (1, 16)]:
            self.assertAlmostEqual(control.boost_to_gamma(level), gamma)
            self.assertAlmostEqual(control.gamma_to_boost(gamma), level)
        exponent = 2 ** (-2 * control.boost_to_gamma(1))
        for brightness in (2 ** -149, .0001, .01, .5, 1):
            native_float = struct.unpack('f', struct.pack('f', brightness ** exponent))[0]
            self.assertEqual(native_float, 1.0)
        self.assertEqual(0 ** exponent, 0)
        c = control.Controller('/unused')
        c.process = Mock()
        c.process.poll.return_value = None
        channel = {'channelId': 0, 'active': True, 'gammaFactor': 1}
        def api(path, data=None, method='GET'):
            if path == '/api/channels': return [channel]
            if path == '/api/setChannelGammaFactor/0': channel['gammaFactor'] = data['gammaFactor']
            return {'succeeded': True}
        with patch.object(control, 'native', side_effect=api):
            self.assertEqual(c.state()['level'], .75, 'old maximum keeps its physical brightness')
            channel['gammaFactor'] = 8
            self.assertLess(c.state()['level'], 1, 'reserve 100% for full-brightness endpoint')
            c.set_level(1)
            self.assertEqual(channel['gammaFactor'], 16)
            self.assertEqual(c.state()['level'], 1)

    def test_invalid_levels_never_reach_native_api(self):
        c = control.Controller('/unused')
        with patch.object(control, 'native') as api:
            for v in (True, None, '1', 1.1, -1.1, float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    c.set_level(v)
            api.assert_not_called()

    def test_off_cannot_adjust_an_external_instance(self):
        c = control.Controller('/unused')
        with patch.object(control, 'native') as api:
            c.stop()
            with self.assertRaises(ValueError):
                c.set_level(.5)
            api.assert_not_called()

    def test_stop_owns_only_its_child(self):
        c = control.Controller('/unused')
        c.process = Mock()
        c.process.poll.return_value = None
        c.stop()
        c.process.terminate.assert_called_once()
        c.process.wait.assert_called_once_with(timeout=5)

    def test_unsafe_native_binding_refuses_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'.config/huenicorn').mkdir(parents=True)
            (root/'.config/huenicorn/config.json').write_text(json.dumps({'boundBackendIP':'0.0.0.0','restServerPort':8215}))
            with patch.object(control.Path, 'home', return_value=root), patch.object(control.subprocess, 'Popen') as launch:
                with self.assertRaises(ValueError):
                    control.Controller('/unused').start()
                launch.assert_not_called()

    def test_http_rejects_cross_origin_and_rebinding(self):
        c = Mock()
        c.state.return_value = {'enabled': False, 'ready': False, 'level': .5}
        server = HTTPServer(('127.0.0.1', 0), control.handler_for(c))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def request(origin, host, path='/api/sync', data=None):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port)
            headers = {'Host':host,'Content-Type':'application/json'}
            if origin: headers['Origin'] = origin
            conn.request('POST',path,json.dumps({'enabled':True} if data is None else data),headers)
            reply = conn.getresponse();status = reply.status;reply.read();conn.close();return status
        try:
            self.assertEqual(request(None, control.PANEL), 403)
            self.assertEqual(request('https://example.org', control.PANEL), 403)
            self.assertEqual(request('http://'+control.PANEL, 'example.org'), 403)
            c.start.assert_not_called()
            self.assertEqual(request('http://'+control.PANEL, control.PANEL), 200)
            c.start.assert_called_once()
            self.assertEqual(request('https://example.org', control.PANEL, '/api/screen', {}), 403)
            c.choose_screen.assert_not_called()
            self.assertEqual(request('http://'+control.PANEL, control.PANEL, '/api/screen', {}), 200)
            c.choose_screen.assert_called_once()
            self.assertEqual(request('http://'+control.PANEL, control.PANEL, '/api/screen', {'path': '/tmp/other'}), 400)
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__ == '__main__':
    unittest.main()
