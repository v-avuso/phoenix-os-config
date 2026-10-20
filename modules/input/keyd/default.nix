{ ... }:

{
  # Keep ordinary US typing; the third/fourth levels provide desktop symbols.
  services.xserver.xkb.variant = "altgr-weur";

  services.keyd = {
    enable = true;
    keyboards.default = {
      ids = [ "*" ];
      settings = {
        main.capslock = "layer(symbols)";
        # Single chords avoid application-specific Compose handling entirely.
        symbols = {
          a = "G-a";
          o = "G-o";
          u = "G-u";
          s = "G-8";
          e = "G-5";
          "-" = "G-minus";
          grave = "S-6";
        };
        "symbols+shift" = {
          a = "G-S-a";
          o = "G-S-o";
          u = "G-S-u";
        };
      };
    };
  };
}
