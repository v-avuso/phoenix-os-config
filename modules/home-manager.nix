{ inputs, user, ... }:

{
  imports = [
    inputs.home-manager.nixosModules.home-manager
  ];

  home-manager = {
    useGlobalPkgs = true;
    useUserPackages = true;
    backupFileExtension = "backup";
    extraSpecialArgs = {
      inherit inputs user;
    };
    sharedModules = [
      inputs.arkenfox-nixos.hmModules.arkenfox
      inputs.plasma-manager.homeModules.plasma-manager
    ];

    users.${user.name} = import ../home;
  };
}
