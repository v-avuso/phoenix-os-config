"""Offline fixed-window ordering/lock tests; no root, auth, model or systemd."""
import contextlib
import importlib.util
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('window', Path(__file__).with_name('review-window.py'))
w = importlib.util.module_from_spec(spec); spec.loader.exec_module(w)


class WindowTests(unittest.TestCase):
    def descriptor(self):
        return dict(off='/off', on='/on', busctl='/busctl', systemctl='/systemctl', systemdRun='/systemd-run',
                    python='/python', script='/script', descriptor='/descriptor')

    @contextlib.contextmanager
    def fake_system(self, fail_on=False):
        d, events = self.descriptor(), []
        @contextlib.contextmanager
        def locks(deadline):
            events.append('locked'); yield (11, 12); events.append('unlocked')
        def query(d, *args):
            return 'active' if args[0] == 'is-active' else 'not-found'
        def switch(d, closure, fds):
            self.assertEqual(fds, (11, 12)); events.append(closure)
            if fail_on and closure == '/on': raise ValueError('on-failed')
        with mock.patch.multiple(w, verify_off=lambda d: events.append('verified-off'),
                configuration=lambda p: (['same'], {}), locks=locks, query=query,
                checked=lambda argv, **kw: events.append('armed'), switch=switch,
                reload_on=lambda d, command: events.append('reload-requested'),
                event=lambda stage: events.append(stage), timer_ready=lambda d: None), \
             mock.patch.dict(os.environ, PKEXEC_UID='1000'), \
             mock.patch.object(Path, 'resolve', lambda p, **kw: Path('/on') if str(p) == str(w.RUNTIME) else Path('/off')):
            yield d, events

    def test_runtime_symlink_resolved_before_strict_configuration_parser(self):
        production_configuration = w.configuration
        unit = ('ExecStart=/python -I /controller /config serve\n')
        with self.fake_system() as (d, events):
            def resolve(p, **kwargs):
                if str(p) == str(w.RUNTIME): return Path('/off')
                if str(p) == str(w.PROFILE): return Path('/off')
                return p
            def read(p, **kwargs):
                return '{}' if str(p) == '/config' else unit
            # Keep the production parser's canonical-path guard active. The
            # runtime symlink is resolved by setup, descriptor aliases stay denied.
            with mock.patch.object(w, 'configuration', production_configuration), \
                 mock.patch.object(w, 'immutable', side_effect=lambda p: Path('/off') if str(p) == str(w.RUNTIME) else Path(p)), \
                 mock.patch.object(Path, 'read_text', read), mock.patch.object(Path, 'resolve', resolve), \
                 mock.patch.object(w, 'query', return_value='loaded'):
                with self.assertRaisesRegex(ValueError, 'owned-unit-already-exists'): w.setup(d, [])
                with self.assertRaisesRegex(ValueError, 'closure-alias-denied'): w.configuration(str(w.RUNTIME))

    def test_setup_arms_before_activation_and_preserves_profile(self):
        with self.fake_system() as (d, events):
            w.setup(d, ['on-controller'])
            self.assertLess(events.index('armed'), events.index('/on'))
            self.assertEqual(events[-1], 'on-ready')

    def test_on_failure_releases_setup_locks_before_recovery(self):
        with self.fake_system(fail_on=True) as (d, events):
            # A real contextmanager releases even when its body throws.
            @contextlib.contextmanager
            def locks(deadline):
                events.append('locked')
                try: yield (11, 12)
                finally: events.append('unlocked')
            with mock.patch.object(w, 'locks', locks), self.assertRaisesRegex(ValueError, 'on-failed'):
                w.setup(d, ['on-controller'])
            self.assertLess(events.index('unlocked'), events.index('recovery-queued'))
            self.assertIn('/off', events)
            self.assertIn('off-restored', events)

    def test_overdue_timer_recovers_after_releasing_setup_locks(self):
        with self.fake_system() as (d, events):
            @contextlib.contextmanager
            def locks(deadline):
                events.append('locked')
                try: yield (11, 12)
                finally: events.append('unlocked')
            with mock.patch.object(w, 'locks', locks), \
                 mock.patch.object(w, 'timer_ready', side_effect=ValueError('timer-window-too-short')):
                with self.assertRaisesRegex(ValueError, 'timer-window-too-short'): w.setup(d, [])
            self.assertLess(events.index('unlocked'), events.index('recovery-queued'))
            self.assertIn('/off', events); self.assertNotIn('on-ready', events)

    def test_selected_timer_clock_and_remaining_window(self):
        with mock.patch.object(w, 'query', return_value='waiting'), \
             mock.patch.object(w.time, 'monotonic_ns', return_value=1_000_000_000), \
             mock.patch.object(w, 'run', return_value=((b't 200000000', b''), 0)):
            w.timer_ready(self.descriptor())
        with mock.patch.object(w, 'query', return_value='running'):
            with self.assertRaisesRegex(ValueError, 'timer-not-waiting'): w.timer_ready(self.descriptor())
        with mock.patch.object(w, 'query', return_value='waiting'), \
             mock.patch.object(w.time, 'monotonic_ns', return_value=1_000_000_000), \
             mock.patch.object(w, 'run', return_value=((b't 1000000', b''), 0)):
            with self.assertRaisesRegex(ValueError, 'timer-window-too-short'): w.timer_ready(self.descriptor())

    def test_timer_arm_failure_never_activates(self):
        with self.fake_system() as (d, events):
            with mock.patch.object(w, 'checked', side_effect=ValueError('arm-failed')):
                with self.assertRaises(ValueError): w.setup(d, [])
            self.assertNotIn('/on', events); self.assertNotIn('/off', events)

    def test_existing_unit_refused_before_locks_or_activation(self):
        with self.fake_system() as (d, events):
            with mock.patch.object(w, 'query', return_value='loaded'):
                with self.assertRaisesRegex(ValueError, 'owned-unit-already-exists'): w.setup(d, [])
            self.assertNotIn('locked', events)

    def test_real_flock_contention_and_guard_inheritance(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / name for name in ('deployment.lock', 'activation.lock')]
            for p in paths: p.touch(mode=0o600)
            paths[0].chmod(0o644)
            real_stat = os.fstat
            real_lstat = Path.lstat
            def root_stat(value):
                values = list(value); values[4] = 0; return os.stat_result(values)
            with mock.patch.object(w, 'DEPLOYMENT', paths[0]), mock.patch.object(w, 'ACTIVATION', paths[1]), \
                 mock.patch.object(os, 'fstat', lambda fd: root_stat(real_stat(fd))), \
                 mock.patch.object(Path, 'lstat', lambda p: root_stat(real_lstat(p))):
                with w.locks(time.monotonic()) as fds:
                    self.assertEqual(len(fds), 2)
                    with self.assertRaisesRegex(ValueError, 'recovery-lock-busy'):
                        with w.locks(time.monotonic()): pass
                with w.locks(time.monotonic()): pass
                paths[0].chmod(0o664)
                with self.assertRaisesRegex(ValueError, 'unsafe-lock'):
                    with w.locks(time.monotonic()): pass
                paths[0].chmod(0o644)
            paths[0].unlink(); paths[0].symlink_to(paths[1])
            with self.assertRaises(OSError):
                with w.locks(time.monotonic()): pass

    def test_switch_passes_guard_fds_and_uses_only_test(self):
        with mock.patch.object(w, 'checked') as checked:
            w.switch(self.descriptor(), '/off', (11, 12))
        checked.assert_called_once_with(['/off/bin/switch-to-configuration', 'test'],
                                        timeout=600, pass_fds=(11, 12))

    def test_recovery_requests_reload_before_wait_and_never_updates_boot(self):
        with self.fake_system() as (d, events):
            w.recover(d, ['on-controller'])
            self.assertLess(events.index('reload-requested'), events.index('locked'))
            self.assertEqual(events.count('/off'), 1)
            self.assertNotIn('/on', events)


if __name__ == '__main__': unittest.main()
