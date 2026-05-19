{ pkgs, inputs, ... }:

let
  extensions = inputs.nix-vscode-extensions.extensions.${pkgs.system};

  # Spyglass is currently outdated on Open VSX, so use Marketplace release.
  marketplace = extensions.vscode-marketplace-release;
in
{
  programs.vscode = {
    enable = true;

    # Home Manager's module is named `vscode`, but we point it at VSCodium.
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
}
