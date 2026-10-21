# Pass the module directory from a Git-flake source, not a checkout-wide path copy.
{ pkgs, typstRoot, letterPro }:
let
  templates = builtins.path {
    path = typstRoot + "/templates";
    name = "phoenix-typst-templates-snapshot";
  };
in
pkgs.runCommand "phoenix-typst-source-layout" {
  nativeBuildInputs = [ pkgs.python3 pkgs.typst ];
  TYPST_FONT_PATHS = "${pkgs.liberation_ttf}/share/fonts";
} ''
  # The aggregation link must stay within the common module source tree.
  adapter=${typstRoot}/template-adapters/omd2typst/phoenix-letter.typ
  canonical=${typstRoot}/templates/phoenix-letter/adapters/omd2typst/phoenix-letter.typ
  test -L "$adapter"
  test "$(realpath "$adapter")" = "$canonical"
  test -r "$adapter"

  # Home Manager's templates snapshot and the legacy package bridge also resolve.
  test -r ${templates}/phoenix-letter/template/lib.typ
  test -r ${templates}/phoenix-letter/lib.typ
  test -r ${templates}/phoenix-letter/typst.toml

  mkdir -p "$TMPDIR/vault/.obsidian/plugins/omd-to-typst" "$TMPDIR/data/typst/packages/local/phoenix-letter" \
    "$TMPDIR/data/typst/packages/preview/letter-pro"
  ln -s ${templates}/phoenix-letter/template "$TMPDIR/data/typst/packages/local/phoenix-letter/0.1.0"
  ln -s ${letterPro} "$TMPDIR/data/typst/packages/preview/letter-pro/3.0.0"
  export XDG_DATA_HOME="$TMPDIR/data"
  echo '{}' > "$TMPDIR/vault/.obsidian/plugins/omd-to-typst/data.json"
  python3 ${typstRoot}/deploy-vault.py --source ${typstRoot}/template-adapters/omd2typst \
    --register "$TMPDIR/vault"
  cmp "$TMPDIR/vault/3-misc/phoenix-typst/omd2typst/phoenix-letter.typ" "$canonical"

  cat > "$TMPDIR/letter.typ" <<EOF_TYPST
  #import "$adapter": template
  #show: template.with(fm: (
    sender_name: "Erika Beispiel", sender_address: "Musterstraße 12, 12345 Musterstadt",
    recipient: [Sozialgericht Musterstadt], subject: "Nix-store integration check", language: "de",
  ))
  == Sachverhalt
  Ein Brief aus dem unveränderlichen Quellbaum.
  EOF_TYPST
  mkdir -p "$out"
  typst compile --root / --pdf-standard ua-1 "$TMPDIR/letter.typ" "$out/letter.pdf"
  echo "PASS: store aggregation, template snapshot, package resolution and vault deployment" > "$out/result"
''
