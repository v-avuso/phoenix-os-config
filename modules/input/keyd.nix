{ ... }:

{
  services.keyd = {
    enable = true;
    keyboards.default = {
      ids = [ "*" ];
      settings = {
        main.capslock = "layer(symbols)";
        symbols = {
          a = "ä";
          o = "ö";
          u = "ü";
          s = "ß";
          e = "€";
          "-" = "–";
          grave = "macro(S-6)";
        };
        "symbols+shift" = {
          a = "Ä";
          o = "Ö";
          u = "Ü";
        };
      };
    };
  };
}
