{ config, lib, pkgs, ... }:

let
  allow = name: description: operator: {
    inherit name description operator;
    enabled = true;
    action = "allow";
    duration = "always";
  };

  allowAll = name: description: list: {
    inherit name description;
    enabled = true;
    action = "allow";
    duration = "always";
    operator = {
      type = "list";
      operand = "list";
      inherit list;
    };
  };

  process = path: {
    type = "simple";
    operand = "process.path";
    data = path;
  };

  network = cidr: {
    type = "network";
    operand = "dest.network";
    data = cidr;
  };

  networkList = cidrs: {
    type = "lists";
    operand = "lists.nets";
    data = "${
      pkgs.writeTextDir "opensnitch-networks.list"
        (lib.concatStringsSep "\n" cidrs + "\n")
    }";
  };

  processRegex = pattern: {
    type = "regexp";
    operand = "process.path";
    data = pattern;
  };

  destPortRegex = pattern: {
    type = "regexp";
    operand = "dest.port";
    data = pattern;
  };
in
{
  "000-allow-localhost" =
    allow "000-allow-localhost"
      "Allow loopback/localhost traffic used by desktop services and local IPC."
      (network "127.0.0.0/8");

  "010-allow-networkmanager" =
    allow "010-allow-networkmanager"
      "Allow NetworkManager to manage DHCP/connectivity for the active network connection."
      (process "${pkgs.networkmanager}/bin/NetworkManager");

  "020-allow-nsncd" =
    allow "020-allow-nsncd"
      "Allow nsncd to perform DNS/name-resolution requests for applications."
      (process "${lib.getExe pkgs.nsncd}");

  # nixos-rebuild-ng can invoke a different nix derivation than
  # config.nix.package, so exact process.path matching is too brittle here.
  # Keep this regex anchored to /nix/store/*-nix-*/bin/nix and restrict it to
  # DNS + HTTP(S), instead of allowing arbitrary outbound ports.
  "030-allow-nix" =
    allowAll "030-allow-nix"
      "Allow the Nix CLI to fetch flakes, inputs, narinfo metadata, and source archives."
      [
        (processRegex "^/nix/store/[^/]+-nix-[^/]+/bin/nix$")
        (destPortRegex "^(53|80|443)$")
      ];

  "031-allow-nix-daemon" =
    allow "031-allow-nix-daemon"
      "Allow nix-daemon to fetch substituters, narinfo metadata, store paths, and build inputs."
      (process "${config.nix.package}/bin/nix-daemon");

  "032-allow-git-remote-http" =
    allow "032-allow-git-remote-http"
      "Allow Git HTTPS remotes used by flakes and source fetches."
      (process "${pkgs.git}/libexec/git-core/git-remote-http");

  "040-allow-freshclam" =
    allow "040-allow-freshclam"
      "Allow ClamAV freshclam to download and update malware signature databases."
      (process "${pkgs.clamav}/bin/freshclam");

  "050-allow-systemd-timesyncd-ntp" =
    allowAll "050-allow-systemd-timesyncd-ntp"
      "Allow systemd-timesyncd to synchronize system time via NTP/SNTP."
      [
        {
          type = "simple";
          operand = "process.path";
          data = "${pkgs.systemd}/lib/systemd/systemd-timesyncd";
        }
        {
          type = "simple";
          operand = "protocol";
          data = "UDP";
        }
        {
          type = "simple";
          operand = "dest.port";
          data = "123";
        }
      ];

    "100-allow-codex-desktop-quic" =
    allowAll "100-allow-codex-desktop-quic"
      "Allow Codex Desktop's Electron network service to use QUIC/HTTP3 over UDP 443."
      [
        (processRegex "^/nix/store/[^/]+-codex-desktop-[^/]+/opt/codex-desktop/electron$")
        {
          type = "simple";
          operand = "protocol";
          data = "UDP";
        }
        {
          type = "simple";
          operand = "dest.port";
          data = "443";
        }
      ];

  "101-allow-codex-desktop-https" =
    allowAll "101-allow-codex-desktop-https"
      "Allow Codex Desktop's Electron network service to use HTTPS over TCP 443."
      [
        (processRegex "^/nix/store/[^/]+-codex-desktop-[^/]+/opt/codex-desktop/electron$")
        {
          type = "simple";
          operand = "protocol";
          data = "TCP";
        }
        {
          type = "simple";
          operand = "dest.port";
          data = "443";
        }
      ];

  "102-allow-codex-app-server-https" =
    allowAll "102-allow-codex-app-server-https"
      "Allow the Codex CLI app-server used by Codex Desktop to connect to backend services over HTTPS."
      [
        (processRegex "^/nix/store/[^/]+-codex-[^/]+/bin/\\.codex-wrapped$")
        {
          type = "simple";
          operand = "protocol";
          data = "TCP";
        }
        {
          type = "simple";
          operand = "dest.port";
          data = "443";
        }
      ];

  "103-allow-codex-desktop-dns-cloudflare" =
    allowAll "103-allow-codex-desktop-dns-cloudflare"
      "Allow Codex Desktop's Electron process to resolve hostnames via the configured Cloudflare DNS resolver."
      [
        (processRegex "^/nix/store/[^/]+-codex-desktop-[^/]+/opt/codex-desktop/electron$")
        {
          type = "simple";
          operand = "protocol";
          data = "UDP";
        }
        {
          type = "simple";
          operand = "dest.port";
          data = "53";
        }
        (network "1.1.1.1/32")
      ];

  "110-allow-vscodium-github-cdn-https" =
    allowAll "110-allow-vscodium-github-cdn-https"
      "Allow VSCodium to fetch GitHub-hosted extension, update, and webview resources over HTTPS from GitHub CDN."
      [
        (processRegex "^/nix/store/[^/]+-vscodium-[^/]+/lib/vscode/codium$")
        {
          type = "simple";
          operand = "protocol";
          data = "TCP";
        }
        {
          type = "simple";
          operand = "dest.port";
          data = "443";
        }
        (networkList [
          "185.199.108.133/32"
          "185.199.110.133/32"
          "185.199.111.133/32"
        ])
      ];
}
