{
  config,
  lib,
  pkgs,
  inputs,
  ...
}:

let
  extensions = inputs.nix-vscode-extensions.extensions.${pkgs.system};

  # Spyglass is currently outdated on Open VSX, so use Marketplace release.
  marketplace = extensions.vscode-marketplace-release;
  settingsPath = "${config.xdg.configHome}/VSCodium/User/settings.json";
  keybindingsPath = "${config.xdg.configHome}/VSCodium/User/keybindings.json";
  settingsBaseline = config.home.file.${settingsPath}.source;
  keybindingsBaseline = config.home.file.${keybindingsPath}.source;
  settingsWriter = import ./mutable-json-settings.nix { inherit pkgs; };
in
{
  programs.vscodium = {
    enable = true;

    # Dedicated module owns VSCodium paths, including .vscode-oss extensions.
    package = pkgs.vscodium;

    # Keep extensions declarative. GUI-installed extensions will not be persistent.
    mutableExtensionsDir = false;

    profiles.default = {
      enableUpdateCheck = false;
      enableExtensionUpdateCheck = false;

      extensions = [
        # Floating/universal search popup; closest VSCodium approximation to JetBrains Search Everywhere.
        marketplace.garroter.spyglass

        # Nix language support: syntax highlighting, LSP integration, formatting hooks.
        pkgs.vscode-extensions.jnoortheen.nix-ide

        # TOML support via Taplo: syntax, schema validation, navigation, formatting.
        marketplace.tamasfe."even-better-toml"

        # Markdown linting for README/SKILL/AGENTS/spec docs without aggressive auto-reflow.
        marketplace.davidanson.vscode-markdownlint

        # Honors .editorconfig across projects for indentation, charset, final newline, etc.
        marketplace.editorconfig.editorconfig

        # Loads direnv/devShell environment into VSCodium workspaces.
        marketplace.mkhl.direnv
      ];

      userSettings = {
        # General editor hygiene.
        "editor.formatOnSave" = true;
        "editor.formatOnSaveMode" = "file";
        "editor.rulers" = [ 100 ];
        "files.trimTrailingWhitespace" = true;
        "files.insertFinalNewline" = true;
        "files.trimFinalNewlines" = true;

        # Spyglass.
        "spyglass.defaultScope" = "project";
        "spyglass.maxResults" = 300;
        "spyglass.openOnSide" = false;

        # Nix language server via nix-ide.
        "nix.enableLanguageServer" = true;
        "nix.serverPath" = "nixd";
        "nix.serverSettings" = {
          nixd = {
            formatting = {
              command = [ "nixfmt" ];
            };
          };
        };

        "[nix]" = {
          "editor.defaultFormatter" = "jnoortheen.nix-ide";
        };

        # TOML.
        "[toml]" = {
          "editor.defaultFormatter" = "tamasfe.even-better-toml";
        };

        # Markdown: lint + visual wrap, but avoid noisy prose/spec autoformatting.
        "[markdown]" = {
          "editor.formatOnSave" = false;
          "editor.wordWrap" = "on";
        };

        # Extension updates are managed by Nix/Home Manager.
        "extensions.autoCheckUpdates" = false;
        "extensions.autoUpdate" = false;
      };

      keybindings = [
        # JetBrains-like double Shift → floating Spyglass popup.
        {
          key = "shift shift";
          command = "spyglass.open";
          when = "!terminalFocus";
        }

        # Replace default sidebar Find in Files with Spyglass popup.
        {
          key = "ctrl+shift+f";
          command = "spyglass.open";
          when = "!terminalFocus";
        }

        # Keep built-in Find in Files reachable.
        {
          key = "ctrl+alt+shift+f";
          command = "workbench.action.findInFiles";
        }

        # Keep Spyglass sidebar reachable.
        {
          key = "ctrl+alt+e";
          command = "spyglass.focusSidebar";
        }

        # Remove Spyglass default popup binding if you only want Shift Shift / Ctrl+Shift+F.
        {
          key = "ctrl+alt+f";
          command = "-spyglass.open";
        }
      ];
    };
  };

  # Keep HM's generated JSON as the canonical baseline, but deploy only these
  # preferences as writable files. Profile/storage/session data remain separate.
  home.file.${settingsPath}.enable = lib.mkForce false;
  home.file.${keybindingsPath}.enable = lib.mkForce false;
  xdg.dataFile."vscodium/settings.json.nix-baseline".source = settingsBaseline;
  xdg.dataFile."vscodium/keybindings.json.nix-baseline".source = keybindingsBaseline;

  home.activation.vscodiumMutableSettings = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    mode=reassert
    if [ "''${PHOENIX_PRESERVE_MUTABLE_BASELINES:-0}" = 1 ]; then
      mode=preserve
    fi
    run ${settingsWriter} "$mode" ${settingsBaseline} ${lib.escapeShellArg settingsPath} object
    run ${settingsWriter} "$mode" ${keybindingsBaseline} ${lib.escapeShellArg keybindingsPath} array
  '';

}
