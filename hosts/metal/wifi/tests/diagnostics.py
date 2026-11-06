import importlib.util
import io
import pathlib
import tempfile
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'diagnostics.py'
spec = importlib.util.spec_from_file_location('wifi_diagnostics', SOURCE)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class DiagnosticsTests(unittest.TestCase):
    def test_trace_limit_accounts_for_each_cpu_and_page_rounding(self):
        for cpus in (1, 32, 192, 8192):
            size = d.buffer_kib(cpus)
            self.assertGreaterEqual(size, 4)
            self.assertEqual(size % 4, 0)
            self.assertLessEqual(size * cpus, 32768)

    def test_loss_ignores_other_interfaces_and_triggers_once(self):
        state = d.Incident()
        state.arm()
        self.assertFalse(state.observe('wlan9: CTRL-EVENT-DISCONNECTED', 10))
        self.assertTrue(state.observe('wlp12s0: CTRL-EVENT-DISCONNECTED reason=4', 11))
        self.assertFalse(state.observe('wlp12s0: Connection to AP abc lost', 12))
        self.assertFalse(state.finished(70))
        self.assertTrue(state.finished(71))

    def test_beacon_loss_alone_does_not_end_capture(self):
        state = d.Incident()
        state.arm()
        self.assertFalse(state.observe('wlp12s0: CTRL-EVENT-BEACON-LOSS', 0))
        self.assertFalse(state.finished(1000))

    def test_startup_disconnect_is_ignored_until_connected(self):
        state = d.Incident()
        self.assertFalse(state.observe('wlp12s0: CTRL-EVENT-DISCONNECTED', 1))
        self.assertFalse(state.observe('wlp12s0: CTRL-EVENT-CONNECTED', 2))
        self.assertTrue(state.observe('wlp12s0: CTRL-EVENT-DISCONNECTED', 3))

    def test_suspend_leave_does_not_consume_the_incident_window(self):
        state = d.Incident()
        state.arm()
        self.assertFalse(state.observe(
            'wlp12s0: CTRL-EVENT-DISCONNECTED bssid=bc:f8:7e:c8:03:7e '
            'reason=3 locally_generated=1', 10))
        self.assertFalse(state.finished(10000))
        self.assertTrue(state.observe(
            'wlp12s0: Connection to AP bc:f8:7e:c8:03:7e lost', 10001))

    def test_peer_leave_is_still_an_incident(self):
        state = d.Incident()
        state.arm()
        self.assertTrue(state.observe(
            'wlp12s0: CTRL-EVENT-DISCONNECTED reason=3 locally_generated=0', 10))

    def test_trace_export_keeps_recent_events_when_text_exceeds_limit(self):
        raw = b'old-event\n' * 10000 + b'newest-event\n'
        data, total = d.read_tail(io.BytesIO(raw), 1024)
        self.assertEqual(total, len(raw))
        self.assertEqual(data, raw[-1024:])

    def test_output_is_bounded_and_remains_private(self):
        with tempfile.TemporaryDirectory() as directory:
            log = d.make_log(pathlib.Path(directory), size=1024)
            for _ in range(100):
                log.info('x' * 200)
            log.handlers[0].close()
            paths = list(pathlib.Path(directory).glob('events.jsonl*'))
            self.assertLessEqual(sum(p.stat().st_size for p in paths), 4096)
            self.assertTrue(all(p.stat().st_mode & 0o007 == 0 for p in paths))

    def test_driver_mask_restores_even_when_networkmanager_is_down(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            mask = root / 'mask'
            mask.write_text('4162')
            (root / 'previous-mask').write_text('0')
            (root / 'network-logging.json').write_text('["WARN", "DEFAULT"]')
            with patch.object(d, 'RUNTIME', root), patch.object(d, 'MASK', mask):
                with patch.object(d, 'run', return_value={'rc': 1}):
                    with self.assertRaises(RuntimeError):
                        d.cleanup()
            self.assertEqual(mask.read_text(), '0')
            self.assertTrue((root / 'network-logging.json').exists())

    def test_damaged_logging_baseline_does_not_block_mask_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            mask = root / 'mask'
            mask.write_text('4162')
            (root / 'previous-mask').write_text('0')
            (root / 'network-logging.json').write_text('{')
            with patch.object(d, 'RUNTIME', root), patch.object(d, 'MASK', mask):
                with self.assertRaises(RuntimeError):
                    d.cleanup()
            self.assertEqual(mask.read_text(), '0')

    def test_selected_trace_events_have_no_payload_or_key_events(self):
        forbidden = ('ath12k/', 'set_key', 'control_port', 'rx_mgmt', 'scan_done')
        self.assertTrue(d.EVENTS)
        self.assertFalse(any(word in event for event in d.EVENTS for word in forbidden))


if __name__ == '__main__':
    unittest.main()
