# Pinned codex-desktop-linux source evidence: 8e3f6b4 → 664436c

Bounded source evidence for protected review, not approval or a full binary audit. Unrelated tests, docs, CI and inactive optional features are omitted. Requested config: `linuxFeatures=[]`, `computerUseUi=false`, `remoteControl=false`; the default recipe enables internal Nix permissions repair.

## Source identities

| Revision | Source path | NAR SHA-256 |
|---|---|---|
| `8e3f6b4b665b9e9c219b286cf57b89f516bb0bd8` | `/nix/store/dvqlyis96frzdd5z36gx4ls8kd5fq5js-source` | `sha256-mZuRL48CPa7RsPWhEY6JGPI1oBIkj1TP8nrwTkvGqIk=` |
| `664436c7d0f3f7919a626c25999424f92bf4a044` | `/nix/store/j7vsjq4jclh03z3fv1hy4gcp01wk5gw4-source` | `sha256-Fa9OfsikyBoz+gvAZetBAoS2bmIILya+3+c/CJdjpjs=` |

Tree diff: 501→518 files; 103 modified, 17 added, 0 removed. `flake.lock` is unchanged; official Debian pin changes 26.917.71314→26.930.31730 (amd64 SRI `sha256-4BdNjQpfQUEUVFjIFPPC2GPdZ+lCuGh4Wh9drJy6PhY=`, arm64 SRI `sha256-3ZgAhel0b62L1FtINUiF0uo6mtCYieDw1iMvHYGbJrI=`). `nix/upstream-linux-packages.json` SHA-256 changes `5725cd741231985e67742c5f6fd9a3b73f6710b831efa33bbd763bf1d22cd9e6`→`883a623453e2403b383f7aae9ddfda56995cb783932dc2736e78c93358f6cacb`.

## Unchanged dependency evidence

| Path | Bytes | SHA-256 (identical old/new) |
|---|---:|---|
| `nix/nixos-module.nix` | 9026 | `df494beb22ddaa07b675375c6ca722496211f54242b4f1b7107b76966c27b97f` |
| `nix/package-selection.nix` | 557 | `fbaf6e76439cd9c30e1bb7af9abf3a7d4345166a98d978bf0a2d920d02f3c3fc` |
| `nix/bundled-codex-cli.nix` | 374 | `351d0d905f9c7da2f19ec32c504c3b228b214099dbf03814e28cf19495237e9e` |
| `nix/linux-features.nix` | 4395 | `1f9061b88f06b1aad06fffcb571f68a9a3549d289021b63e766b59ba929c03ab` |
| `install.sh` | 6336 | `e9ad814185f6d4188efc09f2377ed5e4d295635be66551c5b745cae5553010e3` |
| `launcher/start.sh.template` | 15697 | `6e297c0a3c0f8a84641f494c815b2910a48cbd84bd4028aa3661c800b5902f6b` |
| `scripts/patches/engine.js` | 17548 | `291b335c69ac97c3300113a93aea9f4c13214cd1ef6e6fde8fee7fa72e568bd7` |
| `nix/elf-runtime.cjs` | 24134 | `1daa9a9ceadc614f7abad741b72d0f6a3698623b1c91575f382418554a40a704` |
| `nix/relocate-elf-interpreter.cjs` | 11806 | `0863f7e822e11f85a8d923fe3c0a04d43452ad1775066276c9070c8f86c09401` |
| `flake.lock` | 1497 | `bd29ff49ad97b6dc5356d13d412b47fcc8aaf4dd174d94a7b77f5b056e832ab5` |

These imported NixOS, selector, install, launcher, engine, ELF and lock inputs are unchanged; no module service, activation hook, session variable or privilege rule changed.

## Exact default recipe, sandbox wrapper and launcher excerpts

### Official upstream selection and pins — `flake.nix:20-55`

```text
          inherit system;
          config.allowUnfree = true;
        };
        lib = pkgs.lib;
        nixLinuxFeatures = import ./nix/linux-features.nix { inherit lib; };
        upstreamPins = builtins.fromJSON (builtins.readFile ./nix/upstream-linux-packages.json);
        codexVersion = upstreamPins.version;
        officialPackage = {
          x86_64-linux = {
            architecture = "amd64";
            url = "https://persistent.oaistatic.com/codex-app-prod/linux/deb/${upstreamPins.amd64.repositoryPath}";
            hash = upstreamPins.amd64.sri;
          };
          aarch64-linux = {
            architecture = "arm64";
            url = "https://persistent.oaistatic.com/codex-app-prod/linux/deb/${upstreamPins.arm64.repositoryPath}";
            hash = upstreamPins.arm64.sri;
          };
        }.${system};
        officialRuntimePaths = {
          x86_64-linux = {
            sky = "resources/cua_node/lib/node_modules/@oai/sky/bin/linux/sky_linux_x64";
            extensionHost = "resources/plugins/openai-bundled/plugins/chrome/extension-host/linux/x64/extension-host";
          };
          aarch64-linux = {
            sky = "resources/cua_node/lib/node_modules/@oai/sky/bin/linux/sky_linux_arm64";
            extensionHost = "resources/plugins/openai-bundled/plugins/chrome/extension-host/linux/arm64/extension-host";
          };
        }.${system};
        upstreamDeb = pkgs.fetchurl {
          inherit (officialPackage) url hash;
          name = "chatgpt_${codexVersion}_${officialPackage.architecture}.deb";
        };
        flakeSourceCommit = self.rev or (self.dirtyRev or "");
        flakeSourceRemote = "https://github.com/ilysenko/codex-desktop-linux.git";
        flakeSourceDateEpoch = toString (self.lastModified or 1);
```

### NixOS bubblewrap wrapper source and dependency — `flake.nix:135-217`

```text
        mkNixosBwrap = { realBwrap, runtimeInterpreter ? genericRuntimeInterpreter }:
          let
            source = pkgs.writeText "codex-desktop-nixos-bwrap.c" ''
              #define _XOPEN_SOURCE 700
              #include <errno.h>
              #include <stdio.h>
              #include <stdlib.h>
              #include <string.h>
              #include <unistd.h>

              static const char *real_bwrap = "${realBwrap}";
              static const char *generic_interpreter = "${runtimeInterpreter}";
              static const char *nix_ld = "${pkgs.nix-ld}/libexec/nix-ld";
              static const char *dynamic_linker = "${dynamicLinker}";
              static const char *runtime_library_path = "${workspaceRuntimeLibraryPath}";

              int main(int argc, char **argv) {
                int separator = -1;
                for (int index = 1; index < argc; index++) {
                  if (strcmp(argv[index], "--") == 0) {
                    separator = index;
                    break;
                  }
                }
                if (separator < 0) {
                  execv(real_bwrap, argv);
                  perror("execv real bubblewrap");
                  return 127;
                }

                char *mount_destination = realpath(generic_interpreter, NULL);
                if (mount_destination == NULL) {
                  if (errno == ENOENT) {
                    fprintf(stderr,
                            "codex-desktop: generic interpreter %s is unavailable; "
                            "cached generic runtimes remain disabled\n",
                            generic_interpreter);
                    execv(real_bwrap, argv);
                    perror("execv real bubblewrap");
                    return 127;
                  }
                  perror("resolve generic interpreter");
                  return 127;
                }

                const int extra_count = 9;
                char **rewritten = calloc((size_t)argc + (size_t)extra_count + 1,
                                          sizeof(*rewritten));
                if (rewritten == NULL) {
                  perror("allocate bubblewrap arguments");
                  return 127;
                }

                int output = 0;
                for (int index = 0; index < separator; index++) {
                  rewritten[output++] = argv[index];
                }
                rewritten[output++] = "--ro-bind";
                rewritten[output++] = (char *)nix_ld;
                rewritten[output++] = mount_destination;
                rewritten[output++] = "--setenv";
                rewritten[output++] = "NIX_LD";
                rewritten[output++] = (char *)dynamic_linker;
                rewritten[output++] = "--setenv";
                rewritten[output++] = "NIX_LD_LIBRARY_PATH";
                rewritten[output++] = (char *)runtime_library_path;
                for (int index = separator; index < argc; index++) {
                  rewritten[output++] = argv[index];
                }
                rewritten[output] = NULL;
                execv(real_bwrap, rewritten);
                perror("execv real bubblewrap");
                return 127;
              }
            '';
          in pkgs.runCommandCC "codex-desktop-nixos-bwrap" { } ''
            mkdir -p "$out/bin"
            "$CC" -std=c11 -O2 -Wall -Wextra -Werror \
              -o "$out/bin/bwrap" ${source}
          '';
        nixosBwrap = mkNixosBwrap {
          realBwrap = "${pkgs.bubblewrap}/bin/bwrap";
        };
```

### NixOS runtime launcher — `flake.nix:218-225`

```text
        nixRuntimeLauncher = pkgs.writeShellScript "codex-desktop-nix-runtime-launcher" ''
          set -euo pipefail
          [ "$#" -gt 0 ]
          if [[ -e /etc/NIXOS ]]; then
            export PATH="${nixosBwrap}/bin:''${PATH-}"
          fi
          exec "$@"
        '';
```

### Complete default mkCodexDesktop recipe block — `flake.nix:477-624`

```text
        mkCodexDesktop = {
          linuxFeatureIds ? [ ],
          enableComputerUseUi ? false,
        }:
          let
            userFeatureIds = nixLinuxFeatures.normalize (
              linuxFeatureIds ++ lib.optional enableComputerUseUi "computer-use-linux"
            );
            internalNixFeatureIds = [ "nix-store-bundled-marketplace-permissions" ];
            effectiveFeatureIds = nixLinuxFeatures.normalizeAll (
              userFeatureIds ++ internalNixFeatureIds
            );
            recordReplayBackendEnabled =
              lib.elem "chronicle-skysight" effectiveFeatureIds
              || lib.elem "record-and-replay" effectiveFeatureIds;
            workspaceHelpers = mkWorkspaceHelpers effectiveFeatureIds;
            watchboundEnabled = lib.elem "directory-only-working-tree-watch" effectiveFeatureIds;
            codexMicroEnabled = lib.elem "codex-micro" effectiveFeatureIds;
            featuresConfig = pkgs.writeText "codex-linux-features.json" (builtins.toJSON {
              enabled = effectiveFeatureIds;
            });
            suffix = if userFeatureIds == [ ] then "" else "-${lib.concatStringsSep "-" userFeatureIds}";
          in
          pkgs.stdenv.mkDerivation {
            pname = "codex-desktop${suffix}";
            version = codexVersion;
            src = sourceRoot;
            # This derivation's fail-closed audit owns ELF interpreters and
            # RUNPATHs. Generic fixups would shrink them again and cannot
            # safely strip the current amd64 Tectonic payload.
            dontPatchELF = true;
            dontStrip = true;
            dontFixup = true;
            nativeBuildInputs = [
              pkgs.asar pkgs.bash pkgs.coreutils pkgs.curl pkgs.dpkg pkgs.gnupg
              pkgs.makeWrapper pkgs.nodejs pkgs.patchelf pkgs.python3 pkgs.util-linux
            ];
            dontConfigure = true;
            dontBuild = true;
            installPhase = ''
              runHook preInstall
              export HOME="$TMPDIR/home"
              export SOURCE_DATE_EPOCH="${flakeSourceDateEpoch}"
              mkdir -p "$HOME"
              source_dir="$TMPDIR/source"
              cp -R "$src" "$source_dir"
              chmod -R u+w "$source_dir"
              upstream_contract_root="$TMPDIR/upstream-contract"
              mkdir -p "$upstream_contract_root"
              dpkg-deb -x ${upstreamDeb} "$upstream_contract_root"
              node "$source_dir/nix/elf-runtime.cjs" validate-upstream \
                --root "$upstream_contract_root/usr/lib/chatgpt" \
                --arch ${officialPackage.architecture}
              export CODEX_ASAR_BIN="${pkgs.asar}/bin/asar"
              export CODEX_INSTALL_TRANSACTION_ACTIVE=1
              export CODEX_INSTALL_DIR="$out/opt/codex-desktop"
              export CODEX_LINUX_FEATURES_CONFIG="${featuresConfig}"
              export CODEX_INTERNAL_LINUX_FEATURE_IDS="${lib.concatStringsSep "," internalNixFeatureIds}"
              ${lib.optionalString (flakeSourceCommit != "") ''
              export CODEX_LINUX_SOURCE_COMMIT="${flakeSourceCommit}"
              export CODEX_LINUX_SOURCE_REMOTE="${flakeSourceRemote}"
              ''}
              ${lib.optionalString (lib.elem "computer-use-linux" effectiveFeatureIds) ''
              export CODEX_COMPUTER_USE_BINARY_SOURCE="${workspaceHelpers}/bin/codex-computer-use-linux"
              export CODEX_COMPUTER_USE_COSMIC_BINARY_SOURCE="${workspaceHelpers}/bin/codex-computer-use-cosmic"
              ''}
              ${lib.optionalString (lib.elem "read-aloud-mcp" effectiveFeatureIds) ''
              export CODEX_LINUX_READ_ALOUD_MCP_SOURCE="${workspaceHelpers}/bin/codex-read-aloud-linux"
              ''}
              ${lib.optionalString recordReplayBackendEnabled ''
              export CODEX_RECORD_REPLAY_LINUX_SOURCE="${workspaceHelpers}/bin/codex-record-replay-linux"
              ''}
              ${lib.optionalString (lib.elem "global-dictation" effectiveFeatureIds) ''
              export CODEX_GLOBAL_DICTATION_LINUX_SOURCE="${globalDictationHelper}/bin/codex-global-dictation-linux"
              ''}
              ${lib.optionalString (lib.elem "mcp-helper-reaper" effectiveFeatureIds) ''
              export CODEX_MCP_HELPER_REAPER_SOURCE="${mcpReaperHelper}/bin/codex-mcp-helper-reaper"
              ''}
              ${lib.optionalString watchboundEnabled ''
              export CODEX_WATCHBOUND_PACKAGE_ROOT="${watchboundPackage}/lib/node_modules"
              ''}
              bash "$source_dir/install.sh" "${upstreamDeb}"

              app="$out/opt/codex-desktop"
              test -d "$app"
              node "$source_dir/scripts/ci/validate-patch-report.js" \
                "$app/.codex-linux/patch-report.json" \
                --require-enabled-feature nix-store-bundled-marketplace-permissions
              dynamic_linker="$(cat ${pkgs.stdenv.cc}/nix-support/dynamic-linker)"
              node "$source_dir/nix/elf-runtime.cjs" fix \
                --root "$app" \
                --arch ${officialPackage.architecture} \
                --dynamic-linker "$dynamic_linker" \
                --runtime-library-path "${runtimeLibraryPath}" \
                --patchelf "${pkgs.patchelf}/bin/patchelf" \
                --chatgpt-relocator "$source_dir/nix/relocate-elf-interpreter.cjs"
              patchShebangs --build "$app"

              install -Dm0644 "$app/.codex-linux/codex-desktop.png" \
                "$out/share/icons/hicolor/256x256/apps/codex-desktop.png"
              ${lib.optionalString codexMicroEnabled ''
              install -Dm0644 \
                "$source_dir/linux-features/codex-micro/resources/70-codex-micro.rules" \
                "$out/lib/udev/rules.d/70-codex-micro.rules"
              ''}
              mkdir -p "$out/share/applications"
              awk '
                /^\[Desktop Action CheckForUpdates\]$/ { skip = 1; next }
                /^\[Desktop Action InstallReadyUpdate\]$/ { skip = 1; next }
                /^\[/ { skip = 0 }
                skip { next }
                /^Actions=/ { print "Actions=new-window;"; next }
                { print }
              ' "$source_dir/packaging/linux/codex-desktop.desktop" \
                > "$out/share/applications/codex-desktop.desktop"
              substituteInPlace "$out/share/applications/codex-desktop.desktop" \
                --replace-fail "/usr/bin/codex-desktop" "$out/bin/codex-desktop" \
                --replace-fail "/usr/share/applications/codex-desktop.desktop" "$out/share/applications/codex-desktop.desktop"
              makeWrapper "${nixRuntimeLauncher}" "$out/bin/codex-desktop" \
                --prefix PATH : "${runtimePathFor effectiveFeatureIds}" \
                --set-default ALSA_PLUGIN_DIR "${pkgs.pipewire}/lib/alsa-lib" \
                --set-default CODEX_OZONE_PLATFORM x11 \
                --run 'export XDG_DATA_DIRS="''${XDG_DATA_DIRS:-${xdgDefaultDataDirs}}"' \
                --prefix XDG_DATA_DIRS : "${gsettingsSchemaDataDirs}" \
                --set-default BAMF_DESKTOP_FILE_HINT "$out/share/applications/codex-desktop.desktop" \
                --set-default CODEX_CLI_PATH "$app/resources/codex" \
                --add-flags "$app/start.sh"
              node "$source_dir/nix/elf-runtime.cjs" audit \
                --root "$app" \
                --arch ${officialPackage.architecture} \
                --dynamic-linker "$dynamic_linker" \
                --runtime-library-path "${runtimeLibraryPath}" \
                --patchelf "${pkgs.patchelf}/bin/patchelf"
              node "$source_dir/nix/relocate-elf-interpreter.cjs" check \
                "$app/ChatGPT" "$dynamic_linker"
              runHook postInstall
            '';
            passthru = {
              linuxFeatureIds = userFeatureIds;
              effectiveLinuxFeatureIds = effectiveFeatureIds;
              inherit upstreamDeb workspaceRuntimeLibraries;
              upstreamVersion = codexVersion;
              upstreamArchitecture = officialPackage.architecture;
            };
            meta = {
              description = "Custom codex-desktop distribution based on OpenAI's official Linux package";
              homepage = "https://github.com/ilysenko/codex-desktop-linux";
              license = lib.licenses.unfree;
```
Launcher excerpts (full SHA-256 in table) cover environment hooks, CODEX_HOME canonicalization and final launch. Omitted lines: 1-89, 125-382.

### Environment hooks and CODEX_HOME canonicalization — `launcher/start.sh.template:90-124`

```text

run_hook_directory() {
    local directory="$1"
    local phase="$2"
    local hook
    [ -d "$directory" ] || return 0
    while IFS= read -r -d '' hook; do
        CODEX_LINUX_FEATURE_HOOK_PHASE="$phase" "$hook" "${ORIGINAL_ARGS[@]}"
    done < <(find "$directory" -maxdepth 1 -type f -perm -u+x -print0 | sort -z)
}

load_environment_hooks() {
    local file
    [ -d "$HOOK_ROOT/env.d" ] || return 0
    while IFS= read -r -d '' file; do
        set -a
        # shellcheck disable=SC1090
        . "$file"
        set +a
    done < <(find "$HOOK_ROOT/env.d" -maxdepth 1 -type f -print0 | sort -z)
}

canonicalize_codex_home() {
    local requested_codex_home="${CODEX_HOME:-$HOME/.codex}"
    local physical_codex_home

    [ -d "$requested_codex_home" ] || return 0
    if [ "$requested_codex_home" = "-" ]; then
        requested_codex_home="./-"
    fi
    physical_codex_home="$(CDPATH='' cd -P -- "$requested_codex_home" && pwd -P)"
    export CODEX_HOME="$physical_codex_home"
}

refresh_legacy_bundled_plugin_cache() {
```

### Hook ordering and final exec — `launcher/start.sh.template:383-413`

```text
load_environment_hooks
canonicalize_codex_home
refresh_legacy_bundled_plugin_caches
load_user_electron_args
load_electron_args
run_hook_directory "$HOOK_ROOT/prelaunch.d" prelaunch
run_launcher_hooks "${ELECTRON_ARGS[@]}" "${ORIGINAL_ARGS[@]}"
append_ozone_platform

if [ -f "$HOOK_ROOT/codex-packaged-runtime.sh" ]; then
    # shellcheck disable=SC1091
    . "$HOOK_ROOT/codex-packaged-runtime.sh"
    declare -F codex_packaged_runtime_export_env >/dev/null && codex_packaged_runtime_export_env
    declare -F codex_packaged_runtime_prelaunch >/dev/null && codex_packaged_runtime_prelaunch
fi

report_daily_usage
run_hook_directory "$HOOK_ROOT/cold-start.d" cold-start &

if [ ! -d "$HOOK_ROOT/after-exit.d" ] ||
   ! find "$HOOK_ROOT/after-exit.d" -maxdepth 1 -type f -perm -u+x -print -quit | grep -q .; then
    exec "$CHATGPT_BINARY" "${ELECTRON_ARGS[@]}" "${ORIGINAL_ARGS[@]}"
fi

set +e
"$CHATGPT_BINARY" "${ELECTRON_ARGS[@]}" "${ORIGINAL_ARGS[@]}"
status=$?
CODEX_LINUX_ELECTRON_EXIT_STATUS="$status" run_hook_directory \
    "$HOOK_ROOT/after-exit.d" after-exit
set -e
exit "$status"
```
## Raw diffs: changed default build/runtime path

### Unified diff — `flake.nix`

```text
--- /nix/store/dvqlyis96frzdd5z36gx4ls8kd5fq5js-source/flake.nix
+++ /nix/store/j7vsjq4jclh03z3fv1hy4gcp01wk5gw4-source/flake.nix
@@ -633,0 +634,7 @@
+        # Maximal profiles keep the historical shared-profile feature set.
+        # Community profile isolation intentionally conflicts with
+        # shared-app-server-socket and is validated by its dedicated signed
+        # feature-only job instead.
+        maximalSharedProfileFeatureIds = lib.filter (
+          featureId: featureId != "community-profile-isolation"
+        ) nixLinuxFeatures.supportedFeatureIds;
@@ -636 +643 @@
-        ) nixLinuxFeatures.supportedFeatureIds;
+        ) maximalSharedProfileFeatureIds;
@@ -639 +646 @@
-        ) nixLinuxFeatures.supportedFeatureIds;
+        ) maximalSharedProfileFeatureIds;
@@ -1036 +1043 @@
-            test "$("$app/resources/plugins/openai-bundled/plugins/latex/bin/tectonic" --version)" = \
+            test "$("$app/resources/tectonic/tectonic" --version)" = \
@@ -1068 +1075,2 @@
-              --require-applied feature:nix-store-bundled-marketplace-permissions:bundled-marketplace-staging-copy-permissions
+              --require-applied feature:nix-store-bundled-marketplace-permissions:bundled-marketplace-staging-copy-permissions \
+              --require-applied feature:nix-store-bundled-marketplace-permissions:executor-plugin-copy-permissions
@@ -1202 +1210 @@
-            test "$("$CODEX_INSTALL_DIR/resources/plugins/openai-bundled/plugins/latex/bin/tectonic" --version)" = \
+            test "$("$CODEX_INSTALL_DIR/resources/tectonic/tectonic" --version)" = \
```

### Unified diff — `scripts/lib/asar-patch.sh`

```text
--- /nix/store/dvqlyis96frzdd5z36gx4ls8kd5fq5js-source/scripts/lib/asar-patch.sh
+++ /nix/store/j7vsjq4jclh03z3fv1hy4gcp01wk5gw4-source/scripts/lib/asar-patch.sh
@@ -75,6 +75,36 @@
 NODE
 }
 
+# Resolve the ASAR CLI to a real executable path and invoke it directly.
+#
+# `npx --yes @electron/asar` re-parses its arguments through a shell on POSIX,
+# and that shell performs brace expansion: the `{*.node,*.so,*.dylib}` unpack
+# glob and multi-directory `--unpack-dir "{a,b}"` patterns reach asar as
+# separate words, so asar silently honors only the first alternative. Calling
+# the resolved CLI keeps glob arguments intact.
+resolve_asar_command() {
+    if [ -n "${CODEX_ASAR_BIN:-}" ]; then
+        [ -x "$CODEX_ASAR_BIN" ] || error "Configured ASAR tool is not executable: $CODEX_ASAR_BIN"
+        printf '%s\n' "$CODEX_ASAR_BIN"
+        return 0
+    fi
+
+    # The Ubuntu/Debian nodejs package ships node without npm/npx, and
+    # check_deps() can only warn. Fail with actionable guidance here.
+    command -v npx >/dev/null 2>&1 || error \
+        "npx is required to patch app.asar with enabled feature descriptors, but was not found on PATH." \
+        "Install npm (Debian/Ubuntu: sudo apt install npm) or make the version-manager Node bin directory" \
+        "visible to this shell, then retry."
+
+    local asar_cli
+    asar_cli="$(npx --yes --package=@electron/asar -- sh -c 'command -v asar' 2>/dev/null | tail -n 1)"
+    [ -n "$asar_cli" ] && [ -x "$asar_cli" ] || error \
+        "Could not resolve the @electron/asar CLI through npx." \
+        "Set CODEX_ASAR_BIN to an existing asar executable, then retry." \
+        "Resolved path: ${asar_cli:-<none>}"
+    printf '%s\n' "$asar_cli"
+}
+
 patch_asar() {
     local app_dir="$1"
     local resources_dir="$app_dir/resources"
@@ -82,9 +112,11 @@
     local patch_report_json="${CODEX_PATCH_REPORT_JSON:-$WORK_DIR/patch-report.json}"
     local descriptor_count
     local core_descriptor_count
+    local unpack_dir_pattern
     local upstream_sha
     local patched_sha
     local -a asar_command
+    local -a asar_pack_command
 
     [ -f "$app_asar" ] || error "app.asar not found in $resources_dir"
     core_descriptor_count="$(node - "$SCRIPT_DIR/scripts/patches/runner.js" <<'NODE'
@@ -101,21 +133,11 @@
         return 0
     fi
 
-    if [ -n "${CODEX_ASAR_BIN:-}" ]; then
-        [ -x "$CODEX_ASAR_BIN" ] || error "Configured ASAR tool is not executable: $CODEX_ASAR_BIN"
-        asar_command=("$CODEX_ASAR_BIN")
-    else
-        # The Ubuntu/Debian nodejs package ships node without npm/npx, and
-        # check_deps() can only warn. Fail with actionable guidance here.
-        command -v npx >/dev/null 2>&1 || error \
-            "npx is required to patch app.asar with enabled feature descriptors, but was not found on PATH." \
-            "Install npm (Debian/Ubuntu: sudo apt install npm) or make the version-manager Node bin directory" \
-            "visible to this shell, then retry."
-        asar_command=(npx --yes @electron/asar)
-    fi
+    asar_command=("$(resolve_asar_command)")
 
     upstream_sha="$(sha256sum "$app_asar" | awk '{print $1}')"
     info "Extracting a temporary app.asar copy for $descriptor_count active descriptor(s)"
+    "${asar_command[@]}" list --is-pack "$app_asar" > "$WORK_DIR/app.asar.upstream-layout"
     "${asar_command[@]}" extract "$app_asar" "$WORK_DIR/app-extracted"
     if [ -d "$resources_dir/app.asar.unpacked" ]; then
         cp -a "$resources_dir/app.asar.unpacked/." "$WORK_DIR/app-extracted/"
@@ -135,12 +157,25 @@
         return 0
     fi
 
-    (cd "$WORK_DIR/app-extracted" && find . -type f -printf '%P\n' | LC_ALL=C sort) > "$WORK_DIR/app.asar.ordering"
-    "${asar_command[@]}" pack \
+    node "$SCRIPT_DIR/scripts/patches/lib/asar-layout.js" \
+        "$WORK_DIR/app.asar.upstream-layout" \
+        "$WORK_DIR/app-extracted" \
+        "$WORK_DIR/app.asar.ordering" \
+        "$WORK_DIR/app.asar.unpack-dir-pattern"
+    unpack_dir_pattern="$(<"$WORK_DIR/app.asar.unpack-dir-pattern")"
+    asar_pack_command=("${asar_command[@]}" pack \
         "$WORK_DIR/app-extracted" \
         "$WORK_DIR/app.asar" \
         --ordering "$WORK_DIR/app.asar.ordering" \
-        --unpack "{*.node,*.so,*.dylib}"
+        --unpack "{*.node,*.so,*.dylib}")
+    if [ -n "$unpack_dir_pattern" ]; then
+        asar_pack_command+=(--unpack-dir "$unpack_dir_pattern")
+    fi
+    "${asar_pack_command[@]}"
+    "${asar_command[@]}" list --is-pack "$WORK_DIR/app.asar" > "$WORK_DIR/app.asar.output-layout"
+    node "$SCRIPT_DIR/scripts/patches/lib/asar-layout.js" verify \
+        "$WORK_DIR/app.asar.upstream-layout" \
+        "$WORK_DIR/app.asar.output-layout"
     mv "$WORK_DIR/app.asar" "$app_asar"
     if [ -d "$WORK_DIR/app.asar.unpacked" ]; then
         remove_tree_safely "$resources_dir/app.asar.unpacked"
```

### Unified diff — `scripts/patches/core/quit-confirmation-focus/patch.js`

```text
--- /nix/store/dvqlyis96frzdd5z36gx4ls8kd5fq5js-source/scripts/patches/core/quit-confirmation-focus/patch.js
+++ /nix/store/j7vsjq4jclh03z3fv1hy4gcp01wk5gw4-source/scripts/patches/core/quit-confirmation-focus/patch.js
@@ -1,4 +1,12 @@
 "use strict";
+
+const fs = require("node:fs");
+const path = require("node:path");
+
+const {
+  applyShellEnvironmentStartup,
+  matchesShellEnvironment,
+} = require("../shell-env-startup/shell-env.js");
 
 const HELPER_NAME = "codexLinuxQuitDialogParent";
 const HELPER_SOURCE =
@@ -95,15 +103,57 @@
   return source.slice(0, start) + HELPER_SOURCE + patchedBody + source.slice(end);
 }
 
+function patchRequiredCoreBlockers(extractedDir) {
+  const buildDir = path.join(extractedDir, ".vite", "build");
+  const modules = fs.readdirSync(buildDir)
+    .filter((name) => name.endsWith(".js"))
+    .sort()
+    .map((name) => ({
+      file: path.join(buildDir, name),
+      source: fs.readFileSync(path.join(buildDir, name), "utf8"),
+    }));
+  const mainCandidates = modules.filter(({ source }) =>
+    source.includes("messageId:`desktop.quitConfirmation.quit`"));
+  if (mainCandidates.length !== 1) {
+    throw new Error("Expected exactly one official main-process Quit module");
+  }
+  const [{ file: mainPath, source: mainSource }] = mainCandidates;
+  const patchedMain = applyQuitConfirmationFocus(mainSource);
+  const shellCandidates = modules.filter(({ source }) => matchesShellEnvironment(source));
+  if (shellCandidates.length !== 1) {
+    throw new Error("Expected exactly one official shell environment module");
+  }
+  const [{ file: shellPath, source: shellSource }] = shellCandidates;
+  const sameModule = mainPath === shellPath;
+  const patchedShell = applyShellEnvironmentStartup(
+    sameModule ? patchedMain : shellSource,
+  );
+
+  // Resolve both semantic contracts before writing either file. The required
+  // core repair is one fail-closed transaction and one patch-report entry.
+  if (sameModule) {
+    if (patchedShell !== mainSource) fs.writeFileSync(mainPath, patchedShell, "utf8");
+  } else {
+    if (patchedMain !== mainSource) fs.writeFileSync(mainPath, patchedMain, "utf8");
+    if (patchedShell !== shellSource) fs.writeFileSync(shellPath, patchedShell, "utf8");
+  }
+  return {
+    changed: sameModule
+      ? patchedShell !== mainSource
+      : patchedMain !== mainSource || patchedShell !== shellSource,
+  };
+}
+
 const descriptors = [{
   id: "quit-confirmation-focus",
-  phase: "main-bundle",
+  phase: "extracted-app:pre-webview",
   ciPolicy: "required-upstream",
-  apply: applyQuitConfirmationFocus,
+  apply: patchRequiredCoreBlockers,
 }];
 
 module.exports = {
   HELPER_SOURCE,
   applyQuitConfirmationFocus,
+  patchRequiredCoreBlockers,
   descriptors,
 };
```

### Unified diff — `scripts/patches/core/shell-env-startup/shell-env.js`

```text
--- /dev/null
+++ /nix/store/j7vsjq4jclh03z3fv1hy4gcp01wk5gw4-source/scripts/patches/core/shell-env-startup/shell-env.js
@@ -0,0 +1,42 @@
+"use strict";
+
+const MARKER = "/* codex-linux-shell-env-startup */";
+// A microtask still runs during early browser initialization. Yield one loop
+// turn before uv_spawn installs SIGCHLD, which browser startup otherwise resets.
+const DEFER = `${MARKER}if(process.platform===\`linux\`)await new Promise(setImmediate);`;
+const IDENT = "[A-Za-z_$][\\w$]*";
+const START = new RegExp(
+  `async function ${IDENT}\\(${IDENT},${IDENT}\\)\\{(?=let ${IDENT}=Date\\.now\\(\\);${IDENT}\\.app\\.isPackaged)`,
+  "g",
+);
+
+function matchesShellEnvironment(source) {
+  return source.includes("`Failed to load shell env`") &&
+    source.includes("resultSource:`load`") &&
+    source.includes("new AbortController");
+}
+
+function applyShellEnvironmentStartup(source) {
+  if (!matchesShellEnvironment(source)) {
+    throw new Error("Official shell environment loader contract changed");
+  }
+  const markerCount = source.split(MARKER).length - 1;
+  const original = markerCount === 1 ? source.replace(DEFER, "") : source;
+  const matches = [...original.matchAll(START)];
+  if (matches.length !== 1 || markerCount > 1 ||
+      (markerCount === 1 && original.includes(MARKER))) {
+    throw new Error("Expected exactly one intact shell environment startup function");
+  }
+  const index = matches[0].index + matches[0][0].length;
+  const patched = original.slice(0, index) + DEFER + original.slice(index);
+  if (markerCount === 1 && patched !== source) {
+    throw new Error("Shell environment startup patch is in the wrong location");
+  }
+  return patched;
+}
+
+module.exports = {
+  DEFER,
+  applyShellEnvironmentStartup,
+  matchesShellEnvironment,
+};
```

### Unified diff — `scripts/patches/lib/asar-layout.js`

```text
--- /dev/null
+++ /nix/store/j7vsjq4jclh03z3fv1hy4gcp01wk5gw4-source/scripts/patches/lib/asar-layout.js
@@ -0,0 +1,155 @@
+#!/usr/bin/env node
+"use strict";
+
+const fs = require("node:fs");
+const path = require("node:path");
+
+const SAFE_UNPACK_DIR = /^[A-Za-z0-9@._+/-]+$/;
+const NATIVE_FILE = /\.(?:node|so|dylib)$/;
+
+function parsePackState(source) {
+  const lines = source.trimEnd().split("\n");
+  if (lines.length === 1 && lines[0] === "") {
+    throw new Error("Official app.asar layout is empty");
+  }
+  return lines.map((line) => {
+    const match = /^(pack|unpack)\s+: \/(.*)$/.exec(line);
+    if (match == null || match[2] === "" || match[2].split("/").includes("..")) {
+      throw new Error(`Invalid app.asar layout entry: ${line}`);
+    }
+    return { path: match[2], unpacked: match[1] === "unpack" };
+  });
+}
+
+function requireUniquePaths(entries, description) {
+  const seen = new Set();
+  for (const entry of entries) {
+    if (seen.has(entry.path)) {
+      throw new Error(`${description} app.asar layout contains a duplicate entry: ${entry.path}`);
+    }
+    seen.add(entry.path);
+  }
+  return seen;
+}
+
+function verifyRepackedLayout(upstreamSource, outputSource) {
+  const upstream = parsePackState(upstreamSource);
+  const output = parsePackState(outputSource);
+  const upstreamPaths = requireUniquePaths(upstream, "Official");
+  requireUniquePaths(output, "Repacked");
+
+  let upstreamIndex = 0;
+  for (const entry of output) {
+    const expected = upstream[upstreamIndex];
+    if (expected != null && entry.path === expected.path) {
+      if (entry.unpacked !== expected.unpacked) {
+        throw new Error(
+          `Repacked app.asar changed official unpack metadata: ${entry.path}`,
+        );
+      }
+      upstreamIndex += 1;
+      continue;
+    }
+    if (upstreamPaths.has(entry.path)) {
+      throw new Error(`Repacked app.asar changed official entry ordering: ${entry.path}`);
+    }
+  }
+
+  if (upstreamIndex !== upstream.length) {
+    throw new Error(
+      `Repacked app.asar is missing official layout entry: ${upstream[upstreamIndex].path}`,
+    );
+  }
+}
+
+function hasAncestor(relativePath, directories) {
+  return directories.some((directory) =>
+    relativePath === directory || relativePath.startsWith(`${directory}/`),
+  );
+}
+
+function deriveUpstreamLayout(source, extractedDir) {
+  const entries = parsePackState(source);
+  const unpackDirectories = [];
+  const unpackFiles = [];
+
+  for (const entry of entries) {
+    const extractedPath = path.join(extractedDir, ...entry.path.split("/"));
+    let stat;
+    try {
+      stat = fs.lstatSync(extractedPath);
+    } catch (error) {
+      throw new Error(`Official app.asar layout entry is missing after extraction: ${entry.path}`, {
+        cause: error,
+      });
+    }
+    if (!entry.unpacked) {
+      continue;
+    }
+    if (stat.isDirectory()) {
+      if (!hasAncestor(entry.path, unpackDirectories)) {
+        if (!SAFE_UNPACK_DIR.test(entry.path)) {
+          throw new Error(`Cannot safely preserve upstream unpack directory: ${entry.path}`);
+        }
+        unpackDirectories.push(entry.path);
+      }
+    } else if (!hasAncestor(entry.path, unpackDirectories)) {
+      unpackFiles.push(entry.path);
+    }
+  }
+
+  const unsupportedUnpackFiles = unpackFiles.filter((entry) => !NATIVE_FILE.test(entry));
+  if (unsupportedUnpackFiles.length > 0) {
+    throw new Error(
+      `Cannot preserve non-native upstream unpack files: ${unsupportedUnpackFiles.join(", ")}`,
+    );
+  }
+  const packedNativeFiles = entries
+    .filter((entry) => !entry.unpacked && NATIVE_FILE.test(entry.path))
+    .map((entry) => entry.path);
+  if (packedNativeFiles.length > 0) {
+    throw new Error(
+      `Cannot preserve packed native upstream files with the ASAR packer: ${packedNativeFiles.join(", ")}`,
+    );
+  }
+
+  return {
+    ordering: entries.map((entry) => entry.path),
+    unpackDirectories,
+    unpackDirectoryPattern: unpackDirectories.length === 0
+      ? ""
+      : unpackDirectories.length === 1
+        ? unpackDirectories[0]
+        : `{${unpackDirectories.join(",")}}`,
+  };
+}
+
+function main(args) {
+  if (args[0] === "verify" && args.length === 3) {
+    verifyRepackedLayout(
+      fs.readFileSync(args[1], "utf8"),
+      fs.readFileSync(args[2], "utf8"),
+    );
+    return;
+  }
+  if (args.length !== 4) {
+    throw new Error(
+      "Usage: asar-layout.js verify <upstream-pack-state> <output-pack-state> | " +
+        "asar-layout.js <pack-state> <extracted-dir> <ordering-output> <unpack-dir-pattern-output>",
+    );
+  }
+  const [packStatePath, extractedDir, orderingPath, unpackDirectoryPatternPath] = args;
+  const layout = deriveUpstreamLayout(fs.readFileSync(packStatePath, "utf8"), extractedDir);
+  fs.writeFileSync(orderingPath, `${layout.ordering.join("\n")}\n`);
+  fs.writeFileSync(unpackDirectoryPatternPath, layout.unpackDirectoryPattern);
+}
+
+if (require.main === module) {
+  main(process.argv.slice(2));
+}
+
+module.exports = {
+  deriveUpstreamLayout,
+  parsePackState,
+  verifyRepackedLayout,
+};
```

### Unified diff — `linux-features/nix-store-bundled-marketplace-permissions/patch.js`

```text
--- /nix/store/dvqlyis96frzdd5z36gx4ls8kd5fq5js-source/linux-features/nix-store-bundled-marketplace-permissions/patch.js
+++ /nix/store/j7vsjq4jclh03z3fv1hy4gcp01wk5gw4-source/linux-features/nix-store-bundled-marketplace-permissions/patch.js
@@ -2,10 +2,12 @@
 
 const { mainBundlePatch } = require("../../scripts/patches/descriptor.js");
 
-const PATCH_MARKER = "codex-linux-bundled-marketplace-staging-copy-permissions-v1";
+const STAGING_PATCH_MARKER = "codex-linux-bundled-marketplace-staging-copy-permissions-v3";
+const EXECUTOR_PATCH_MARKER = "codex-linux-executor-plugin-copy-permissions-v1";
+const HELPER_MARKER = "codex-linux-bundled-plugin-copy-permissions-helper-v1";
 const IDENT = "[A-Za-z_$][\\w$]*";
 
-const HELPER_SOURCE = `/* ${PATCH_MARKER} */
+const HELPER_SOURCE = `/* ${HELPER_MARKER} */
 async function codexLinuxMakeBundledPluginStageNodesWritable(fs,destination){
   let stat;
   try{stat=await fs.lstat(destination)}catch(error){if(error?.code==="ENOENT")return;throw error}
@@ -55,26 +57,60 @@
 }
 
 function applyBundledMarketplaceStagingCopyPermissions(source) {
-  if (source.includes(PATCH_MARKER)) return source;
+  if (source.includes(STAGING_PATCH_MARKER)) return source;
   const contracts = stagingCopyContracts(source);
   if (contracts.length !== 1) {
     throw new Error(`bundled marketplace staging copy contract matched ${contracts.length} times`);
   }
   const { match } = contracts[0];
   const [, fsName, , destinationName] = match;
-  const replacement = `try{${match[0]}}finally{await codexLinuxMakeBundledPluginStageNodesWritable(${fsName}.default,${destinationName})}`;
-  const patched = `${source.slice(0, match.index)}${replacement}${source.slice(match.index + match[0].length)}`;
-  return `${HELPER_SOURCE}${patched}`;
+  const replacement = `/* ${STAGING_PATCH_MARKER} */try{${match[0]}}finally{await codexLinuxMakeBundledPluginStageNodesWritable(${fsName}.default,${destinationName})}`;
+  return replaceCopyWithWritableRepair(source, match, replacement);
+}
+
+function applyExecutorPluginCopyPermissions(source) {
+  if (source.includes(EXECUTOR_PATCH_MARKER)) return source;
+  const executorCopies = [...source.matchAll(new RegExp(
+    `await (${IDENT})\\.default\\.cp\\((${IDENT})\\.cwd,(${IDENT}),\\{recursive:!0\\}\\)`, "g",
+  ))].filter(match => {
+    const fn = functionContaining(source, match.index);
+    return fn?.source.includes("executorPluginRoot:") &&
+      fn.source.includes("CODEX_APP_TOOLS_CALLER_HOST_ID") &&
+      fn.source.includes("`.mcp.json`");
+  });
+  if (executorCopies.length !== 1) {
+    throw new Error(`executor plugin copy contract matched ${executorCopies.length} times`);
+  }
+  const executor = executorCopies[0];
+  const writable = `codexLinuxMakeBundledPluginStageNodesWritable(${executor[1]}.default,${executor[3]})`;
+  // Repair an old read-only cache before cp tries to unlink its files, and
+  // repair newly copied Nix modes before upstream writes .mcp.json.
+  const replacement = `/* ${EXECUTOR_PATCH_MARKER} */await (async()=>{await ${writable};try{${executor[0]}}finally{await ${writable}}})()`;
+  return replaceCopyWithWritableRepair(source, executor, replacement);
+}
+
+function replaceCopyWithWritableRepair(source, match, replacement) {
+  const patched = source.slice(0, match.index) + replacement + source.slice(match.index + match[0].length);
+  return source.includes(HELPER_MARKER) ? patched : `${HELPER_SOURCE}${patched}`;
 }
 
 module.exports = {
-  PATCH_MARKER,
+  STAGING_PATCH_MARKER,
+  EXECUTOR_PATCH_MARKER,
+  HELPER_MARKER,
   applyBundledMarketplaceStagingCopyPermissions,
+  applyExecutorPluginCopyPermissions,
   descriptors: [mainBundlePatch({
     id: "bundled-marketplace-staging-copy-permissions",
     ciPolicy: "optional",
     enforceWhenEnabled: false,
     order: 20_170,
     apply: applyBundledMarketplaceStagingCopyPermissions,
+  }), mainBundlePatch({
+    id: "executor-plugin-copy-permissions",
+    ciPolicy: "optional",
+    enforceWhenEnabled: false,
+    order: 20_171,
+    apply: applyExecutorPluginCopyPermissions,
   })],
 };
```

### Unified diff — `scripts/patches/runner.js`

```text
--- /nix/store/dvqlyis96frzdd5z36gx4ls8kd5fq5js-source/scripts/patches/runner.js
+++ /nix/store/j7vsjq4jclh03z3fv1hy4gcp01wk5gw4-source/scripts/patches/runner.js
@@ -193,17 +193,15 @@
 
 function allPatchPolicies(options = {}) {
   return [
-    ...corePatchDescriptors(options).map(({ id, name, ciPolicy, phase, appliesTo }) => ({
+    ...corePatchDescriptors(options).map(({ id, name, ciPolicy, phase }) => ({
       name: name ?? id,
       ciPolicy,
       phase,
-      appliesTo,
     })),
-    ...featurePatchDescriptors(featurePatchOptions(options)).map(({ id, name, ciPolicy, phase, appliesTo }) => ({
+    ...featurePatchDescriptors(featurePatchOptions(options)).map(({ id, name, ciPolicy, phase }) => ({
       name: name ?? id,
       ciPolicy,
       phase,
-      appliesTo,
     })),
     ...CUSTOM_PATCH_POLICIES,
   ];
@@ -213,11 +211,8 @@
   if (profile !== "upstream-build") {
     return [];
   }
-  const linux = options.linuxTarget ?? detectLinuxTargetContext(options.linuxTargetOptions);
-  const context = { linux, linuxTarget: linux, enableComputerUseUi: false };
   return allPatchPolicies(options)
     .filter((patch) => patch.ciPolicy === REQUIRED_UPSTREAM)
-    .filter((patch) => patch.appliesTo == null || patch.appliesTo(context) !== false)
     .map((patch) => patch.name);
 }
```
## Limits

`community-profile-isolation` is optional/default-disabled and unselected. This source evidence does not audit the complete official Debian binary.
