{ user, ... }:

let
  syncRoot = "${user.homeDirectory}/sync";
  syncFolders = [
    "scans"
    "music"
    "media"
    "camera"
    "knowledge"
    "personal"
  ];
in
{
  services.syncthing = {
    enable = true;
    user = user.name;
    group = "users";
    dataDir = syncRoot;
    databaseDir = "${user.homeDirectory}/.local/state/syncthing";
    configDir = "${user.homeDirectory}/.config/syncthing";
    openDefaultPorts = true;
    overrideDevices = true;
    overrideFolders = true;

    settings = {
      devices = {
        V-Smartphone.id = "FMR26EN-JWMX4BZ-BMJKBXK-4XNNBIP-6P7GMWI-EOGHAIH-NXBUWKM-NUFV6A2";
        V-Tablet.id = "6GRGM55-TEQVGTV-FKFESFH-AC3LIWN-NLJDITM-2A5U3VD-SJRYQ7T-GKRH6QL";
      };

      folders = {
        scans = {
          id = "cvh8w-sqnsh";
          label = "scans";
          path = "${syncRoot}/scans";
          type = "sendreceive";
          devices = [ "V-Smartphone" ];
          ignorePatterns = [ ];
        };

        music = {
          id = "edxdj-scujh";
          label = "music";
          path = "${syncRoot}/music";
          type = "sendreceive";
          devices = [ "V-Smartphone" ];
          ignorePatterns = [ ];
        };

        media = {
          id = "kjuh3-ybmkz";
          label = "media";
          path = "${syncRoot}/media";
          type = "sendreceive";
          devices = [
            "V-Smartphone"
            "V-Tablet"
          ];
          ignorePatterns = [ ];
        };

        camera = {
          id = "cj1t7-e1ozi";
          label = "camera";
          path = "${syncRoot}/camera";
          type = "sendreceive";
          devices = [ "V-Smartphone" ];
          ignorePatterns = [ ];
        };

        knowledge = {
          id = "qw4b9-tsser";
          label = "knowledge";
          path = "${syncRoot}/knowledge";
          type = "sendreceive";
          devices = [ "V-Tablet" ];
          ignorePatterns = [ ];
        };

        personal = {
          id = "rrjk6-kxuwh";
          label = "personal";
          path = "${syncRoot}/personal";
          type = "sendreceive";
          devices = [
            "V-Smartphone"
            "V-Tablet"
          ];
          ignorePatterns = [ ];
        };
      };

      options = {
        globalAnnounceEnabled = true;
        localAnnounceEnabled = true;
        relaysEnabled = true;
        natEnabled = true;
      };
    };
  };

  systemd.tmpfiles.rules = [
    "d ${syncRoot} 0750 ${user.name} users - -"
  ]
  ++ map (folder: "d ${syncRoot}/${folder} 0750 ${user.name} users - -") syncFolders;
}
