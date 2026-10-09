{
  inputs,
  config,
  lib,
  pkgs,
  user,
  ...
}:

let
  system = pkgs.stdenv.hostPlatform.system;
  baseCodecPolicy = builtins.fromJSON (builtins.readFile ./codec-policy.json);
  codecPolicy = pkgs.writeText "phoenix-media-codec-policy.json" (
    builtins.toJSON (
      baseCodecPolicy
      // {
        audio = baseCodecPolicy.audio // {
          quality = "${toString config.phoenix.media.audioBitrateKbps}K";
        };
      }
    )
  );
  # yt-dlp resolves only the supplied source URL and handles stream post-processing.
  ytDlpPackage = inputs.nixpkgs-unstable.legacyPackages.${system}.yt-dlp;
  # pyacoustid performs Chromaprint lookup; Mutagen edits canonical tags without a library database.
  mediaPython = pkgs.python3.withPackages (pythonPackages: [
    pythonPackages.pyacoustid
    pythonPackages.mutagen
  ]);
  # Bound local fingerprint work as well as the remote service calls below.
  boundedFpcalc = pkgs.writeShellApplication {
    name = "phoenix-fpcalc";
    runtimeInputs = [ pkgs.coreutils ];
    text = ''
      exec ${pkgs.coreutils}/bin/timeout --signal=KILL 10s ${pkgs.chromaprint}/bin/fpcalc "$@"
    '';
  };
  musicDirectory = "${user.homeDirectory}/sync/music";
  unsortedDirectory = "${musicDirectory}/_unsorted";
  reviewDirectory = "${unsortedDirectory}/_review";
  videoDirectory = "${user.homeDirectory}/Downloads/videos";
  mediaIngest = pkgs.writeShellApplication {
    name = "phoenix-media-ingest";
    # Secret Service provides the key at runtime without putting it in arguments or files.
    runtimeInputs = [
      mediaPython
      pkgs.libsecret
    ];
    text = ''
      export FPCALC=${boundedFpcalc}/bin/phoenix-fpcalc
      exec ${mediaPython}/bin/python3 ${./media-ingest.py} \
        --inbox ${unsortedDirectory} \
        --music-root ${musicDirectory} "$@"
    '';
  };
  phoenixSecret = pkgs.writeShellApplication {
    name = "phoenix-secret";
    runtimeInputs = [
      mediaPython
      pkgs.libsecret
    ];
    text = ''
      exec ${mediaPython}/bin/python3 ${./phoenix-secret.py} "$@"
    '';
  };
  downloadCommand = pkgs.writeShellApplication {
    name = "download";
    runtimeInputs = [
      ytDlpPackage
      mediaPython
      # Full FFmpeg adds VMAF for upstream ab-av1 search and completed-output gates.
      pkgs.ffmpeg-full
      pkgs.ab-av1
    ];
    text = ''
      export PHOENIX_VIDEO_DIRECTORY=${videoDirectory}/
      export PHOENIX_MUSIC_DIRECTORY=${unsortedDirectory}/
      export PHOENIX_MEDIA_INGEST_COMMAND=${mediaIngest}/bin/phoenix-media-ingest
      export PHOENIX_MEDIA_PYTHON=${mediaPython}/bin/python3
      export PHOENIX_MEDIA_CLI_HELPER=${./media-cli.py}
      export PHOENIX_MEDIA_CODEC_POLICY=${codecPolicy}
      export PHOENIX_MEDIA_PLUGIN_DIRECTORY=${./plugins}
      export PHOENIX_MEDIA_FFMPEG_DIRECTORY=${pkgs.ffmpeg-full}/bin
      export PHOENIX_MEDIA_AB_AV1=${pkgs.ab-av1}/bin/ab-av1
    ''
    + builtins.readFile ./download;
  };
  commandLinks = pkgs.runCommand "phoenix-media-command-links" { } ''
    mkdir -p "$out/bin"
    for name in dl dlm dlv; do
      ln -s ${downloadCommand}/bin/download "$out/bin/$name"
    done
  '';
  mediaCommands = pkgs.symlinkJoin {
    name = "phoenix-media-commands";
    paths = [
      downloadCommand
      commandLinks
    ];
  };
in
{
  options.phoenix.media.audioBitrateKbps = lib.mkOption {
    type = lib.types.ints.positive;
    default = 160;
    description = "Maximum Opus VBR bitrate in kbit/s for non-Opus audio; a reliable lower source audio bitrate is used when available. Existing Opus streams are copied.";
  };

  config = {
    systemd.tmpfiles.rules = [
      "d ${musicDirectory} 0755 ${user.name} users - -"
      "d ${unsortedDirectory} 0755 ${user.name} users - -"
      "d ${reviewDirectory} 0755 ${user.name} users - -"
      "d ${videoDirectory} 0755 ${user.name} users - -"
    ];

    home-manager.users.${user.name}.home.packages = [
      # Picard stays installed for manual MusicBrainz release review and tag correction in _review.
      pkgs.picard
      # Manage the AcoustID application key in GNOME Keyring through Secret Service.
      phoenixSecret
      # pyacoustid fingerprints completed downloads against AcoustID; Mutagen writes tags without a library database.
      mediaIngest
      # yt-dlp and FFmpeg provide exact-source audio/video downloads and lossless container remuxing.
      mediaCommands
    ];
  };
}
