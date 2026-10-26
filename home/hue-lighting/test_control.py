import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from http.server import HTTPServer
import control


class Controls(unittest.TestCase):
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
        def request(origin, host):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port)
            headers = {'Host':host,'Content-Type':'application/json'}
            if origin: headers['Origin'] = origin
            conn.request('POST','/api/sync',json.dumps({'enabled':True}),headers)
            reply = conn.getresponse();status = reply.status;reply.read();conn.close();return status
        try:
            self.assertEqual(request(None, control.PANEL), 403)
            self.assertEqual(request('https://example.org', control.PANEL), 403)
            self.assertEqual(request('http://'+control.PANEL, 'example.org'), 403)
            c.start.assert_not_called()
            self.assertEqual(request('http://'+control.PANEL, control.PANEL), 200)
            c.start.assert_called_once()
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__ == '__main__':
    unittest.main()
