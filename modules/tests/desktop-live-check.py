import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('guard', Path(__file__).parents[1] / 'desktop-live-check.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class DesktopCheck(unittest.TestCase):
    def test_native_nixpkgs_wrapper_and_kernel_process_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / 'proc'; proc.mkdir()
            binary = root / 'Hyprland'; binary.touch()
            wrapped = root / '.Hyprland-wrapped'; wrapped.touch()
            process = proc / '42'; process.mkdir()
            process.joinpath('comm').write_text('.Hyprland-wrapp\n')
            process.joinpath('exe').symlink_to(wrapped)
            guard.check(binary, proc)
            other = root / 'other'; other.touch()
            process.joinpath('exe').unlink()
            process.joinpath('exe').symlink_to(other)
            with self.assertRaisesRegex(ValueError, 'stopped live activation'):
                guard.check(binary, proc)

    def test_running_and_candidate_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / 'proc'; proc.mkdir()
            candidate = root / 'new'; candidate.touch()
            old = root / 'old'; old.touch()
            guard.check(candidate, proc)  # No graphical session.
            process = proc / '42'; process.mkdir()
            process.joinpath('comm').write_text('Hyprland\n')
            process.joinpath('exe').symlink_to(old)
            with self.assertRaisesRegex(ValueError, 'stopped live activation'):
                guard.check(candidate, proc)
            process.joinpath('exe').unlink()
            process.joinpath('exe').symlink_to(candidate)
            alias = root / 'wrapper'; alias.symlink_to(candidate)
            guard.check(alias, proc)  # Compare resolved binaries, not wrapper paths.
            process.joinpath('comm').write_text('unrelated\n')
            process.joinpath('exe').unlink()
            process.joinpath('exe').symlink_to(old)
            guard.check(candidate, proc)
            process.joinpath('comm').write_text('Hyprland\n')
            process.joinpath('exe').unlink()
            with self.assertRaisesRegex(ValueError, 'cannot inspect'):
                guard.check(candidate, proc)


if __name__ == '__main__':
    unittest.main()
