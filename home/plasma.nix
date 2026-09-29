{ ... }:

{
  programs.plasma = {
    enable = true;

    input.mice = [
      {
        name = "Razer Razer Viper V2 Pro";
        vendorId = "1532";
        productId = "00a6";
        acceleration = -0.35;
      }
    ];

    session.sessionRestore.restoreOpenApplicationsOnLogin = "onLastLogout";

    shortcuts.kwin = {
      "Overview" = [
        "Meta+W"
        "Meta+Tab"
      ];
      "Walk Through Windows" = "Alt+Tab";
    };

    workspace.enableMiddleClickPaste = false;

    # Keep the existing panel and its widgets intact. The typed panels option
    # regenerates plasma-org.kde.plasma.desktop-appletsrc on activation.
    configFile = {
      "dolphinrc".General.ShowHiddenFiles = true;
      "plasmaparc".General.AudioFeedback = false;
      "plasmashellrc"."PlasmaViews/Panel 4".panelVisibility = 2;
      "inputdevicesrc"."Libinput/Razer Razer Viper V2 Pro".MouseButtonScrollingEnabled = true;
    };
  };
}
