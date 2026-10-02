{ user, ... }:

{
  xdg.autostart.enable = true;

  programs.keepassxc = {
    enable = true;
    autostart = true;

    settings = {
      General = {
        RememberLastDatabases = true;
        OpenPreviousDatabasesOnStartup = true;
        LastOpenedDatabases = "${user.homeDirectory}/sync/personal/keypass.kdbx";
      };

      Browser = {
        Enabled = true;
        UpdateBinaryPath = false;
      };
    };
  };
}
