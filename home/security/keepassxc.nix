{ user, ... }:

{
  programs.keepassxc = {
    enable = true;

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
