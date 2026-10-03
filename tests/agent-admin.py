#!/usr/bin/env python3
"""Focused tests for Phoenix's closed privileged diagnostic broker."""

from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "phoenix_agent_admin", ROOT / "modules/development/ai/agent/admin.py"
)
assert SPEC and SPEC.loader
admin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admin)


class FakeStream:
    def fileno(self):
        return 42


class FakeProcess:
    def __init__(self, returncode=0):
        self.stdout = FakeStream()
        self.returncode = returncode
        self.killed = False
        self.wait_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.wait_calls += 1
        return self.returncode


class BrokerFixture(unittest.TestCase):
    ADDRESS = "0000:00:14.0"
    OTHER_ADDRESS = "0000:00:15.0"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sys_root = self.root / "sys"
        self.trace_root = self.sys_root / "kernel/tracing"
        self.device = self.sys_root / "devices/pci0000:00/0000:00:14.0"
        self.device.mkdir(parents=True)
        (self.sys_root / "bus/pci/devices").mkdir(parents=True)
        (self.sys_root / "bus/pci/devices" / self.ADDRESS).symlink_to(self.device)
        (self.device / "class").write_text("0x0c0330\n")
        (self.device / "power").mkdir()
        # Model sysfs semantics where a write replaces the value despite not
        # taking O_TRUNC (ordinary fixture files otherwise retain trailing bytes).
        (self.device / "power/wakeup").write_text("disabled")
        self.trace_root.mkdir(parents=True)
        self.config = {
            "sys_root": str(self.sys_root),
            "tracing_root": str(self.trace_root),
            "wakeup_devices": [self.ADDRESS],
            "status_services": ["coolercontrold.service", "NetworkManager.service"],
            "journalctl": "/nix/store/test-systemd/bin/journalctl",
            "systemctl": "/nix/store/test-systemd/bin/systemctl",
            "dmesg": "/nix/store/test-util-linux/bin/dmesg",
            "client_uid": os.getuid(),
        }
        self.broker = admin.Broker(self.config)

    def test_kernel_journal_uses_fixed_arguments_and_clean_environment(self):
        process = FakeProcess()
        with mock.patch.object(admin.subprocess, "Popen", return_value=process) as popen, \
             mock.patch.object(admin.select, "select", return_value=([42], [], [])), \
             mock.patch.object(admin.os, "read", side_effect=[b"[0.0] fixture\n", b""]):
            output = self.broker.dispatch(["kernel-journal", "123"])
        self.assertEqual(output, "[0.0] fixture\n")
        popen.assert_called_once_with(
            [
                self.config["journalctl"], "--dmesg", "--boot=0", "--no-pager",
                "--output=short-monotonic", "--lines=123",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={"LANG": "C", "SYSTEMD_COLORS": "0"},
        )

    def test_dmesg_is_fixed_and_no_arguments_are_accepted(self):
        process = FakeProcess()
        with mock.patch.object(admin.subprocess, "Popen", return_value=process) as popen, \
             mock.patch.object(admin.select, "select", return_value=([42], [], [])), \
             mock.patch.object(admin.os, "read", side_effect=[b"kernel ring\n", b""]):
            self.assertEqual(self.broker.dispatch(["dmesg"]), "kernel ring\n")
        self.assertEqual(popen.call_args.args[0], [self.config["dmesg"], "--color=never"])
        with self.assertRaises(admin.Rejected):
            self.broker.dispatch(["dmesg", "--follow"])

    def test_trace_summary_filters_events_and_trace_format_is_named(self):
        for name, value in {
            "current_tracer": "nop\n",
            "tracing_on": "0\n",
            "kprobe_events": "p:fixture/probe do_thing\n",
            "available_events": "xhci-hcd:urb_submit\nusb:usb_giveback_urb\nkprobes:probe\nsched:switch\n",
        }.items():
            (self.trace_root / name).write_text(value)
        event_format = self.trace_root / "events/xhci-hcd/urb_submit"
        event_format.mkdir(parents=True)
        (event_format / "format").write_text("name: urb_submit\nID: 12\n")

        result = json.loads(self.broker.dispatch(["trace-summary"]))
        self.assertEqual(result["current_tracer"], "nop\n")
        self.assertIn("xhci-hcd:urb_submit", result["available_events"])
        self.assertIn("usb:usb_giveback_urb", result["available_events"])
        self.assertNotIn("sched:switch", result["available_events"])
        self.assertEqual(
            self.broker.dispatch(["trace-format", "xhci-hcd/urb_submit"]),
            "name: urb_submit\nID: 12\n",
        )
        with self.assertRaises(admin.Rejected):
            self.broker.dispatch(["trace-format", "sched/switch"])

    def test_service_status_is_restricted_to_allowlist(self):
        process = FakeProcess()
        with mock.patch.object(admin.subprocess, "Popen", return_value=process) as popen, \
             mock.patch.object(admin.select, "select", return_value=([42], [], [])), \
             mock.patch.object(
                 admin.os, "read",
                 side_effect=[b"Id=NetworkManager.service\nActiveState=active\n", b""],
             ):
            output = self.broker.dispatch(["service-status", "NetworkManager.service"])
        self.assertIn("ActiveState=active", output)
        self.assertEqual(
            popen.call_args.args[0],
            [
                self.config["systemctl"], "show", "--no-pager",
                "--property=Id,LoadState,ActiveState,SubState,Result,MainPID",
                "--", "NetworkManager.service",
            ],
        )
        with self.assertRaises(admin.Rejected):
            self.broker.dispatch(["service-status", "sshd.service"])

    def test_wakeup_get_and_set_use_allowlisted_xhci_fixture(self):
        self.assertEqual(self.broker.dispatch(["wakeup-get", self.ADDRESS]), "disabled")
        result = json.loads(self.broker.dispatch(["wakeup-set", self.ADDRESS, "enabled"]))
        self.assertEqual(result, {"device": self.ADDRESS, "before": "disabled", "after": "enabled"})
        self.assertEqual(self.broker.dispatch(["wakeup-get", self.ADDRESS]), "enabled\n")
        result = json.loads(self.broker.dispatch(["wakeup-set", self.ADDRESS, "disabled"]))
        self.assertEqual(result["after"], "disabled")

    def test_rejects_unknown_operations_shells_and_command_injection(self):
        for args in (
            ["cat", "/etc/shadow"],
            ["sh", "-c", "id"],
            ["root-shell"],
            ["kernel-journal", "1;touch /tmp/pwned"],
            ["kernel-journal", "0"],
            ["kernel-journal", "2001"],
            ["service-status", "NetworkManager.service;id"],
            ["trace-format", "xhci-hcd/urb_submit;cat"],
            ["wakeup-set", self.ADDRESS, "enabled;id"],
        ):
            with self.subTest(args=args), self.assertRaises(admin.Rejected):
                self.broker.dispatch(args)

    def test_rejects_non_allowlisted_and_non_xhci_devices(self):
        with self.assertRaises(admin.Rejected):
            self.broker.dispatch(["wakeup-get", self.OTHER_ADDRESS])
        (self.device / "class").write_text("0x010802\n")
        with self.assertRaises(admin.Rejected):
            self.broker.dispatch(["wakeup-set", self.ADDRESS, "enabled"])

    def test_rejects_trace_and_sysfs_symlink_escapes(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "format").write_text("outside\n")
        (self.trace_root / "events").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(admin.Rejected):
            self.broker.dispatch(["trace-format", "xhci-hcd/event"])

        (self.trace_root / "events").unlink()
        internal_target = self.trace_root / "other-format"
        internal_target.write_text("internal\n")
        event_format = self.trace_root / "events/xhci-hcd/urb_submit"
        event_format.mkdir(parents=True)
        (event_format / "format").symlink_to(internal_target)
        with self.assertRaises(OSError):
            self.broker.dispatch(["trace-format", "xhci-hcd/urb_submit"])

        (self.device / "power").rename(self.device / "power-original")
        (self.device / "power").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(admin.Rejected):
            self.broker.dispatch(["wakeup-set", self.ADDRESS, "enabled"])

        (self.device / "power").unlink()
        (self.device / "power-original").rename(self.device / "power")
        (self.device / "power/wakeup").unlink()
        (self.device / "power/wakeup").symlink_to(outside / "format")
        with self.assertRaises(admin.Rejected):
            self.broker.dispatch(["wakeup-set", self.ADDRESS, "enabled"])

    def test_run_rejects_oversized_output_and_kills_timed_out_child(self):
        too_large = FakeProcess()
        chunks = [b"x" * 16384 for _ in range(admin.MAX_OUTPUT // 16384 + 1)]
        with mock.patch.object(admin.subprocess, "Popen", return_value=too_large), \
             mock.patch.object(admin.select, "select", return_value=([42], [], [])), \
             mock.patch.object(admin.os, "read", side_effect=chunks):
            with self.assertRaisesRegex(admin.Rejected, "exceeded output limit"):
                self.broker.run(["/fixed/program"])

        timed_out = FakeProcess()
        with mock.patch.object(admin.subprocess, "Popen", return_value=timed_out), \
             mock.patch.object(admin.select, "select", return_value=([], [], [])):
            with self.assertRaisesRegex(admin.Rejected, "timed out"):
                self.broker.run(["/fixed/program"])
        self.assertTrue(timed_out.killed)
        self.assertEqual(timed_out.wait_calls, 1)

    def test_protocol_denies_unknown_keys_wrong_uid_and_oversized_requests(self):
        def request(data, uid=None):
            connection = mock.Mock()
            connection.getsockopt.return_value = struct.pack("3i", 123, os.getuid() if uid is None else uid, 1000)
            connection.makefile.return_value = io.BytesIO(data)
            with mock.patch.object(admin.syslog, "syslog") as log:
                admin.handle(connection, self.broker, self.config)
            return json.loads(connection.sendall.call_args.args[0]), json.loads(log.call_args.args[1])

        for data in (b'{"operation":"dmesg","command":"secret"}\n', b'["private-secret"]\n', b'x' * (admin.MAX_REQUEST + 1) + b'\n'):
            with self.subTest(data=data[:80]):
                response, audit = request(data)
                self.assertFalse(response["ok"])
                self.assertEqual(audit["operation"], "invalid")
                self.assertNotIn("secret", json.dumps(audit))
                self.assertNotIn("error", audit)
        response, audit = request(b'["dmesg"]\n', os.getuid() + 1)
        self.assertFalse(response["ok"])
        self.assertEqual(audit["outcome"], "denied")

    def test_incomplete_socket_request_and_timeout_are_audited(self):
        for stream in (io.BytesIO(b'["dmesg"]'), None):
            connection = mock.Mock()
            connection.getsockopt.return_value = struct.pack("3i", 123, os.getuid(), os.getgid())
            connection.makefile.return_value = stream
            if stream is None:
                connection.makefile.side_effect = TimeoutError("fixture timeout")
            with mock.patch.object(admin.syslog, "syslog") as log:
                admin.handle(connection, self.broker, self.config)
            response = json.loads(connection.sendall.call_args.args[0])
            audit = json.loads(log.call_args.args[1])
            self.assertFalse(response["ok"])
            self.assertEqual(audit["pid"], 123)
            self.assertGreaterEqual(audit["elapsed_ms"], 0)
            self.assertEqual(audit["outcome"], "timeout" if stream is None else "denied")

    def test_malformed_socket_json_gets_error_without_dispatch(self):
        request = b"{not-json}\n"

        class Connection:
            response = None

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def settimeout(self, _timeout):
                pass

            def getsockopt(self, *_args):
                return struct.pack("3i", os.getpid(), os.getuid(), os.getgid())

            def makefile(self, *_args):
                return io.BytesIO(request)

            def sendall(self, data):
                self.response = data

        connection = Connection()

        class StopServing(Exception):
            pass

        class Listener:
            def __init__(self):
                self.accepted = False

            def accept(self):
                if self.accepted:
                    raise StopServing
                self.accepted = True
                return connection, None

        listener = Listener()
        env = {"LISTEN_PID": str(os.getpid()), "LISTEN_FDS": "1"}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(admin.socket, "socket", return_value=listener), \
             mock.patch.object(admin.syslog, "openlog"), \
             mock.patch.object(admin.syslog, "syslog"):
            with self.assertRaises(StopServing):
                admin.serve(self.config)
        response = json.loads(connection.response)
        self.assertFalse(response["ok"])
        self.assertIn("Expecting", response["error"])


if __name__ == "__main__":
    unittest.main()
