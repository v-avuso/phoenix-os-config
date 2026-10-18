{ pkgs }:

pkgs.stdenv.mkDerivation {
  pname = "nms-frame-generation-fix";
  version = "2026-09-30";

  src = ./.;

  buildInputs = [ pkgs.vulkan-headers ];
  dontConfigure = true;

  buildPhase = ''
    runHook preBuild
    $CC -shared -fPIC -pthread -O2 -Wall -Wextra \
      -I${pkgs.vulkan-headers}/include \
      -o libnms_fix.so nms_fix.c
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    install -Dm755 libnms_fix.so "$out/lib/libnms_fix.so"
    install -Dm644 VkLayer_NMS_fix.json \
      "$out/share/vulkan/explicit_layer.d/VkLayer_NMS_fix.json"
    substituteInPlace "$out/share/vulkan/explicit_layer.d/VkLayer_NMS_fix.json" \
      --replace-fail '@NMS_FIX_LIBRARY@' "$out/lib/libnms_fix.so"
    runHook postInstall
  '';

  meta = {
    description = "Vulkan semaphore workaround for No Man's Sky DLSS Frame Generation";
    platforms = [ "x86_64-linux" ];
  };
}
