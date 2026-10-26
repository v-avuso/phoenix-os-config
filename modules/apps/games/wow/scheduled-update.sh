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

status=1
for delay in 0 60 300 900; do
  if (( delay > 0 )); then
    echo "Retrying scheduled WoW add-on update in $delay seconds." >&2
    sleep "$delay"
  fi
  wow_check_or_skip
  if wow_sync; then
    # A launch during sync cannot be made atomic with an external game launcher;
    # recheck before update, and never terminate or restart game processes.
    wow_check_or_skip
    if instawow -v -p phoenix-retail update; then
      exit 0
    else
      status=$?
    fi
  else
    status=$?
  fi
  echo "Scheduled WoW add-on update failed (status $status)." >&2
done
exit "$status"
