"""Exercise the real rendered NixOS hook with temporary homes and package stubs."""

import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("nix-instantiate"), "requires nix-instantiate")
class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture.cleanup)
        self.root = Path(self.fixture.name)
        self.config_home = self.root / "custom config home"
        self.packages = self.root / "packages"
        self.packages.joinpath("bin").mkdir(parents=True)
        self.writer = self.packages / "writer"
        self.writer.write_text(
            '#!/bin/sh\nexec '
            + shlex.quote(shutil.which("python3"))
            + ' '
            + shlex.quote(str(ROOT / "home/mutable-json-settings.py"))
            + ' "$@"\n'
        )
        self.writer.chmod(0o755)
        runuser = self.packages / "bin/runuser"
        # Package stub executes as the current fixture user, never changes uid.
        runuser.write_text('#!/bin/sh\nshift 3\nexec "$@"\n')
        runuser.chmod(0o755)
        self.baseline = self.root / "object.json"
        self.baseline.write_text('{"enabled":true}')
        self.array_baseline = self.root / "array.json"
        self.array_baseline.write_text('[{"command":"declared"}]')

    def render(self, caelestia=False):
        # Evaluate the actual module without importing Nixpkgs, building packages,
        # contacting the Nix daemon, or reading the user's Home Manager state.
        expression = '''
          let
            module = import MODULE;
            fixture = module {
              config.home-manager.users.fixture = {
                programs.vscodium.enable = true;
                CAELESTIA
                xdg.configHome = CONFIG_HOME;
                xdg.dataFile = {
                  "vscodium/settings.json.nix-baseline".source = OBJECT;
                  "vscodium/keybindings.json.nix-baseline".source = ARRAY;
                  "caelestia/shell.json.nix-baseline".source = OBJECT;
                };
              };
              inputs.home-manager.nixosModules.home-manager = "unused";
              user.name = "fixture";
              pkgs = {
                util-linux = PACKAGES;
                writeShellScript = name: script: WRITER;
              };
              lib = {
                optionals = condition: values: if condition then values else [];
                concatMapStringsSep = separator: fn: values:
                  builtins.concatStringsSep separator (map fn values);
                escapeShellArg = value: "'" + value + "'";
                mkIf = condition: value: if condition then value else {};
              };
            };
          in {
            hook = fixture.system.activationScripts.mutableApplicationSettings.text;
            preserve = fixture.systemd.services.home-manager-fixture.environment.PHOENIX_PRESERVE_MUTABLE_BASELINES;
          }
        '''
        substitutions = {
            "MODULE": str(ROOT / "modules/home-manager.nix"),
            "CAELESTIA": "programs.caelestia.enable = true;" if caelestia else "",
            "CONFIG_HOME": json.dumps(str(self.config_home)),
            "OBJECT": json.dumps(str(self.baseline)),
            "ARRAY": json.dumps(str(self.array_baseline)),
            "PACKAGES": json.dumps(str(self.packages)),
            "WRITER": json.dumps(str(self.writer)),
        }
        for name, value in substitutions.items():
            expression = expression.replace(name, value)
        result = subprocess.run(
            ["nix-instantiate", "--eval", "--strict", "--json", "--expr", expression],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

    def activate(self, hook, action):
        environment = os.environ.copy()
        environment.pop("NIXOS_ACTION", None)
        if action is not None:
            environment["NIXOS_ACTION"] = action
        subprocess.run(
            ["bash", "-c", hook], env=environment, check=True, capture_output=True, text=True
        )

    def test_boot_and_non_activation_actions_leave_existing_experiments(self):
        rendered = self.render()
        self.assertEqual(rendered["preserve"], "1")
        target = self.config_home / "VSCodium/User/settings.json"
        target.parent.mkdir(parents=True)
        target.write_text('{"experiment":true}')
        for action in (None, "boot", "dry-activate", "build"):
            self.activate(rendered["hook"], action)
            self.assertEqual(target.read_text(), '{"experiment":true}')
            self.assertFalse(target.with_name("keybindings.json").exists())

    def test_switch_and_test_initialize_exact_config_home_and_reassert(self):
        rendered = self.render()
        settings = self.config_home / "VSCodium/User/settings.json"
        keybindings = settings.with_name("keybindings.json")
        for action in ("switch", "test"):
            self.activate(rendered["hook"], action)
            self.assertEqual(settings.read_bytes(), self.baseline.read_bytes())
            self.assertEqual(keybindings.read_bytes(), self.array_baseline.read_bytes())
            self.assertFalse(self.config_home.joinpath("caelestia").exists())
            settings.write_text('{"experiment":true}')
            keybindings.write_text('[]')

    def test_caelestia_participates_only_when_enabled(self):
        rendered = self.render(caelestia=True)
        self.activate(rendered["hook"], "test")
        target = self.config_home / "caelestia/shell.json"
        self.assertEqual(target.read_bytes(), self.baseline.read_bytes())

    def test_earlier_writer_failure_is_not_hidden_by_later_writes(self):
        rendered = self.render()
        invalid_target = self.config_home / "VSCodium/User/settings.json"
        invalid_target.mkdir(parents=True)
        with self.assertRaises(subprocess.CalledProcessError):
            self.activate(rendered["hook"], "switch")
        self.assertTrue(invalid_target.is_dir())
        self.assertFalse(invalid_target.with_name("keybindings.json").exists())


if __name__ == "__main__":
    unittest.main()
