{ ... }:

{
  services.xserver.xkb.options = "compose:menu";

  services.keyd = {
    enable = true;
    keyboards.default = {
      ids = [ "*" ];
      settings = {
        main.capslock = "layer(symbols)";
        # Standard US Compose sequences avoid keyd-specific Cancel encodings.
        symbols = {
          a = "macro(compose S-apostrophe a)";
          o = "macro(compose S-apostrophe o)";
          u = "macro(compose S-apostrophe u)";
          s = "macro(compose s s)";
          e = "macro(compose e equal)";
          "-" = "macro(compose minus minus dot)";
          grave = "macro(S-6)";
        };
        "symbols+shift" = {
          a = "macro(compose S-apostrophe S-a)";
          o = "macro(compose S-apostrophe S-o)";
          u = "macro(compose S-apostrophe S-u)";
        };
      };
    };
  };
}
