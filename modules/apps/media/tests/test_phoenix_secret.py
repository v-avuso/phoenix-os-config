import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "phoenix-secret.py"
SPEC = importlib.util.spec_from_file_location("phoenix_secret", SCRIPT)
phoenix_secret = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = phoenix_secret
SPEC.loader.exec_module(phoenix_secret)


class PhoenixSecretTests(unittest.TestCase):
    def test_set_reads_hidden_input_and_sends_value_only_over_stdin(self):
        success = phoenix_secret.subprocess.CompletedProcess([], 0, "", "")
        with (
            patch.object(phoenix_secret.sys.stdin, "isatty", return_value=True),
            patch.object(phoenix_secret.sys.stderr, "isatty", return_value=True),
            patch.object(phoenix_secret.getpass, "getpass", return_value="dummy-client-key") as getpass,
            patch.object(phoenix_secret.subprocess, "run", return_value=success) as run,
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = phoenix_secret.main(["set", "acoustid"])
        self.assertEqual(0, status)
        getpass.assert_called_once_with("AcoustID client key: ")
        self.assertNotIn("dummy-client-key", run.call_args.args[0])
        self.assertEqual("dummy-client-key", run.call_args.kwargs["input"])
        self.assertEqual(60, run.call_args.kwargs["timeout"])
        self.assertIn("--label=Phoenix AcoustID application key", run.call_args.args[0])
        self.assertNotIn("dummy-client-key", output.getvalue())

    def test_check_reports_only_availability(self):
        result = phoenix_secret.subprocess.CompletedProcess([], 0, "dummy-client-key\n", "")
        with patch.object(phoenix_secret.subprocess, "run", return_value=result):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = phoenix_secret.main(["check", "acoustid"])
        self.assertEqual(0, status)
        self.assertEqual("AcoustID client key is available.\n", output.getvalue())
        self.assertNotIn("dummy-client-key", output.getvalue())

    def test_delete_uses_fixed_secret_service_identity(self):
        success = phoenix_secret.subprocess.CompletedProcess([], 0, "", "")
        with patch.object(phoenix_secret.subprocess, "run", return_value=success) as run:
            with contextlib.redirect_stdout(io.StringIO()):
                status = phoenix_secret.main(["delete", "acoustid"])
        self.assertEqual(0, status)
        self.assertEqual(
            ["secret-tool", "clear", "service", "phoenix-media", "key", "acoustid-client"],
            run.call_args.args[0],
        )


if __name__ == "__main__":
    unittest.main()
