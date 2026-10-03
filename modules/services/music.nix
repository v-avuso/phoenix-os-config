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
  # Navidrome module exposes only MusicFolder read-only inside its service
  # namespace; a named ACL gives the service user read/traverse rights there
  # without opening /home/v or granting the broad `users` group.
  musicDirectory = "${user.homeDirectory}/sync/music";
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
      MusicFolder = musicDirectory;
      Plugins.Enabled = false;
    };
  };

  # The client stays independent from the server; another Subsonic client can
  # replace this package without changing Navidrome or its library settings.
  home-manager.users.${user.name}.home.packages = [
    inputs.psysonic.packages.${system}.psysonic
  ];
}
