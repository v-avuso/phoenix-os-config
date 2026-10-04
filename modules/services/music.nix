{
  config,
  inputs,
  lib,
  pkgs,
  user,
  ...
}:

let
  # First use: after activation, open http://127.0.0.1:4533 to create the
  # initial local Navidrome account. Then launch Psysonic and add a server at
  # that URL with the account above. These one-time steps leave Navidrome as
  # the local backend; normal use happens through Psysonic.
  # Keep the URL aligned with Address and Port below. Navidrome listens only
  # on localhost and is not exposed to the LAN or Internet. Psysonic has no
  # supported declarative server-profile interface; upstream stores the URL
  # and credentials as private app state, so this module does not pre-seed it.

  # Keep this aligned with the existing Syncthing music folder. The NixOS
  # Navidrome service exposes only this tree read-only at its internal music
  # path; a named ACL gives the service user read/traverse rights there
  # without opening /home/v or granting the broad `users` group.
  musicDirectory = "${user.homeDirectory}/sync/music";
  serviceMusicDirectory = "/var/lib/navidrome/music";
  quotedMusicDirectory = lib.escapeShellArg musicDirectory;
  system = pkgs.stdenv.hostPlatform.system;
in
{
  system.activationScripts.navidromeMusicAccess = {
    deps = [ "users" ];
    text = ''
      if [ -d ${quotedMusicDirectory} ]; then
        ${pkgs.acl}/bin/setfacl -R -m g:navidrome:r-X -- ${quotedMusicDirectory}
        ${pkgs.findutils}/bin/find ${quotedMusicDirectory} -type d \
          -exec ${pkgs.acl}/bin/setfacl -m d:g:navidrome:r-X -- {} +
      fi
    '';
  };

  services.navidrome = {
    enable = true;
    openFirewall = false;
    settings = {
      Address = "127.0.0.1";
      Port = 4533;
      Plugins.Enabled = false;
    };
  };

  systemd.services.navidrome = {
    # The upstream module automatically binds JSON MusicFolder at the SAME host
    # path. Use Navidrome's supported environment setting instead so that only
    # our explicit source:destination mapping owns this mount. Upstream still
    # creates its default music directory under StateDirectory and retains its
    # CA/store/etc mounts and all service hardening. ProtectHome=yes cannot
    # expose a bind destination below /home (systemd.exec BindReadOnlyPaths).
    environment.ND_MUSICFOLDER = serviceMusicDirectory;
    serviceConfig.BindReadOnlyPaths = [ "${musicDirectory}:${serviceMusicDirectory}" ];
  };

  # The client stays independent from the server; another Subsonic client can
  # replace this package without changing Navidrome or its library settings.
  home-manager.users.${user.name}.home.packages = [
    inputs.psysonic.packages.${system}.psysonic
  ];
}
