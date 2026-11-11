# Embedded in wow-addons after acquiring its shared lock. wow_sync and instawow
# come from that wrapper. Keep all attempts in one service invocation so only a
# terminal failure reaches systemd's OnFailure notification.
wow_require_idle() {
  local status
  if pgrep --ignore-case --exact 'Wow(-64|T|B|Classic|ClassicT|ClassicB)?\.exe' > /dev/null; then
    echo 'WoW is running; skipping scheduled add-on updates.'
    return 1
  else
    status=$?
    if (( status != 1 )); then
      echo "Cannot determine whether WoW is running (pgrep status $status)." >&2
      return 2
    fi
  fi
}

wow_check_or_skip() {
  local status
  if wow_require_idle; then
    return 0
  else
    status=$?
    if (( status == 1 )); then
      exit 0
    fi
    exit "$status"
  fi
}

wow_update_profile() {
  local profile=$1 status=1 started=$SECONDS delay INSTAWOW_NETWORK_TIMEOUT=300
  export INSTAWOW_NETWORK_TIMEOUT
  for delay in 0 60 300 900; do
    if (( SECONDS - started + delay >= 300 )); then
      echo "Scheduled WoW $profile network budget exhausted; no further batch retry." >&2
      break
    fi
    if (( delay > 0 )); then
      echo "Retrying scheduled WoW $profile add-on update in $delay seconds." >&2
      sleep "$delay"
    fi
    wow_check_or_skip
    if { if [[ $profile == phoenix-forever ]]; then wow_sync_forever "$wow_manifest"; else wow_sync; fi; }; then
      wow_check_or_skip
      if (( SECONDS - started >= 300 )); then
        status=1
      elif INSTAWOW_NETWORK_TIMEOUT=$((300 - (SECONDS - started))) instawow -v -p "$profile" update; then
        return 0
      else
        status=$?
      fi
    else
      status=$?
    fi
    echo "Scheduled WoW $profile add-on update failed (status $status)." >&2
  done
  return "$status"
}

# Each client gets an independent bounded budget and is attempted even if the
# other fails; retain a failure for the existing terminal notification.
result=0
wow_update_profile phoenix-forever || result=$?
wow_update_profile phoenix-retail || result=$?
exit "$result"
