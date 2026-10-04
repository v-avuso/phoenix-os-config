#!/usr/bin/env python3
"""Hardware-free state, transport and lifecycle acceptance fixtures."""
import errno
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('debounce', Path(__file__).parents[1] / 'modules/input/mouse-side-button-debounce.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
MS = 1_000_000


class Event:
    def __init__(self, code, value, kind=1):
        self.type, self.code, self.value = kind, code, value


class Dropped(Exception):
    pass


class API:
    EV_KEY = 1
    SYN_REPORT = 0
    EventsDroppedException = Dropped
    evbit = staticmethod(lambda kind, code: code)
    InputEvent = staticmethod(lambda code, value: Event(code, value, 0 if code == 0 else 1))


class Fixture:
    def __init__(self, batches, *, grab_error=False):
        self.batches, self.now, self.sent, self.log = iter(batches), 0, [], []
        self.done, self.fd, self.grab_error = False, 1, grab_error

    def grab(self):
        self.log.append('grab')
        if self.grab_error:
            raise OSError('grab failed')

    def ungrab(self):
        self.log.append('ungrab')

    def make_output(self):
        fixture = self
        class Output:
            def send_events(self, events):
                fixture.sent.extend((event.type, event.code, event.value) for event in events)
            def __del__(self):
                fixture.log.append('destroy')
        return Output()

    def wait(self, reads, writes, errors, timeout):
        try:
            self.now, self.batch = next(self.batches)
        except StopIteration:
            self.done = True
            return [], [], []
        if self.batch is None:
            return [], [], []
        return reads, [], []

    def events(self):
        if isinstance(self.batch, Exception):
            raise self.batch
        return iter(self.batch)

    def sync(self):
        return iter([Event(275, 0), Event(0, 0, 0)])

    def run(self):
        m.relay(self, self.make_output, API, clock=lambda: self.now, wait=self.wait, stopping=lambda: self.done)


class Tests(unittest.TestCase):
    def test_release_boundary_and_duplicate_release(self):
        s = m.Debouncer()
        self.assertTrue(s.update(275, 1, 0))
        self.assertFalse(s.update(275, 0, 0))
        s.update(275, 0, 100 * MS)
        self.assertEqual(s.due(179 * MS), [])
        self.assertEqual(s.due(180 * MS), [275])
        self.assertTrue(s.update(275, 1, 181 * MS))

    def test_long_hold_chatter_and_independent_buttons(self):
        s = m.Debouncer()
        s.update(275, 1, 0)
        self.assertEqual(s.due(20_000 * MS), [])
        s.update(275, 0, 20_000 * MS)
        self.assertFalse(s.update(275, 1, 20_179 * MS))
        self.assertEqual(s.due(21_000 * MS), [])
        self.assertTrue(s.update(276, 1, 21_000 * MS))
        s.update(276, 0, 21_001 * MS)
        self.assertEqual(s.due(21_181 * MS), [276])
        self.assertEqual(s.clear(), [275])

    def test_normal_events_and_stable_release_frames(self):
        normal = [Event(0, 4, 2), Event(11, 120, 2), Event(272, 1), Event(272, 0), Event(0, 0, 0)]
        f = Fixture([(0, [Event(275, 1)] + normal), (10 * MS, [Event(275, 0)]), (189 * MS, None), (190 * MS, None)])
        f.run()
        self.assertEqual(f.sent, [(1, 275, 1)] + [(e.type, e.code, e.value) for e in normal] + [(1, 275, 0), (0, 0, 0)])
        self.assertEqual(f.log, ['grab', 'ungrab', 'destroy'])

    def test_drop_resynchronizes_and_releases(self):
        f = Fixture([(0, [Event(275, 1)]), (MS, Dropped()), (181 * MS, None)])
        f.run()
        self.assertEqual(f.sent, [(1, 275, 1), (0, 0, 0), (1, 275, 0), (0, 0, 0)])

    def test_start_failure_does_not_grab(self):
        f = Fixture([])
        with self.assertRaises(RuntimeError):
            m.relay(f, lambda: (_ for _ in ()).throw(RuntimeError('create failed')), API)
        self.assertEqual(f.log, [])
        f = Fixture([], grab_error=True)
        with self.assertRaises(OSError):
            f.run()
        self.assertEqual(f.log, ['grab', 'destroy'])

    def test_disconnect_and_shutdown_release_ungrab_destroy(self):
        f = Fixture([(0, [Event(275, 1), Event(276, 1)]), (MS, OSError(errno.ENODEV, 'disconnected'))])
        with self.assertRaises(OSError):
            f.run()
        self.assertEqual(f.sent[-3:], [(1, 275, 0), (1, 276, 0), (0, 0, 0)])
        self.assertEqual(f.log, ['grab', 'ungrab', 'destroy'])
        f = Fixture([(0, [Event(275, 1)])])
        f.run()
        self.assertEqual(f.sent[-2:], [(1, 275, 0), (0, 0, 0)])


if __name__ == '__main__':
    unittest.main()
