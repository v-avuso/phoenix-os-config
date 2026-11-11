# WoWInterface returns Retail files regardless of profile. TomTom's current
# shared archive supports Forever; retain this narrow, explicitly accepted
# exception and recheck if its author changes packaging.
wow_sync_forever() {
  local manifest=$1 addon installed output status
  while IFS= read -r addon; do
    if [[ $addon == wowi:* && $addon != wowi:7032 ]]; then
      echo "Forever: skipping $addon (WoWInterface cannot select Forever files)"
      continue
    fi
    if declare -F wow_check_or_skip > /dev/null; then wow_check_or_skip; fi
    installed=$(instawow -v -p phoenix-forever list --format json "$addon") || return "$?"
    if [[ $(jq length <<< "$installed") != 0 ]]; then continue; fi
    if [[ -n ${started+x} ]]; then
      if (( SECONDS - started >= 300 )); then
        echo 'Forever sync exceeded the scheduled network budget.' >&2
        return 1
      fi
      export INSTAWOW_NETWORK_TIMEOUT=$((300 - (SECONDS - started)))
    fi
    if output=$(instawow -v -p phoenix-forever install "$addon" 2>&1); then
      printf '%s\n' "$output"
    else
      status=$?
      printf '%s\n' "$output" >&2
      # This pinned InstaWoW result means no release matches its flavour rules.
      # Fail on all other errors, including authentication and rate limits.
      if [[ $addon == github:* && $output == *'no files found for:'* ]]; then
        echo "Forever: no matching release for $addon"
      else
        return "$status"
      fi
    fi
  done < <(jq -r '.[]' "$manifest")
}
