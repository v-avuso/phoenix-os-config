{ pkgs }:
let
  # Follow the official 1.2.0 flake recipe, using Phoenix's existing package set.
  # Its httplib API requires 0.46; the locked Phoenix set supplies 0.30.
  httplib = pkgs.httplib.overrideAttrs (_: {
    version = "0.46.0";
    src = pkgs.fetchFromGitHub {
      owner = "yhirose";
      repo = "cpp-httplib";
      rev = "008e107d0fcddee7cb96dc5ad3c3189fd090e40a";
      hash = "sha256-Vzr51oo344jFNwmqdtLWxClJpuCTzmnMqXyLCz8UZj4=";
    };
  });
in
pkgs.stdenv.mkDerivation {
  pname = "huenicorn";
  version = "1.2.0";
  src = pkgs.fetchFromGitLab {
    owner = "openjowelsofts";
    repo = "huenicorn";
    rev = "ede353ac329ba1922d354aae89adf5fe6ddb03f5";
    hash = "sha256-Xni/sjF+mUiGiddR39ngG+0POXPP4Bn/128Bx7Oj+FQ=";
  };
  nativeBuildInputs = with pkgs; [ cmake pkg-config ];
  buildInputs = with pkgs; [
    curl glib glm httplib mbedtls nlohmann_json opencv
    libX11 libXext libXcursor libXrandr libXi pipewire
  ];
  cmakeFlags = [ "-DHUENICORN_FETCH_DEPS=OFF" ];
  installPhase = ''
    runHook preInstall
    install -Dm755 huenicorn $out/bin/huenicorn
    runHook postInstall
  '';
  meta = {
    description = "Philips Hue screen synchronization with native rectangular sampling";
    homepage = "https://gitlab.com/openjowelsofts/huenicorn";
    license = pkgs.lib.licenses.gpl3Only;
    platforms = pkgs.lib.platforms.linux;
    mainProgram = "huenicorn";
  };
}
