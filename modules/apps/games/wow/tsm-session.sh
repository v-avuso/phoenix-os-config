# Embedded in a systemd user service, independent of the Lutris/Battle.net PID.
# Both launch routes use this lock; never adopt/kill a foreground-owned instance.
exec 8>"$XDG_RUNTIME_DIR/phoenix-tsm.lock"
flock -n 8 || exit 0
# systemd owns all descendants, including a replacement started by the updater.
tsm-app &

# Allow Battle.net two minutes to start. While it is open, wait indefinitely
# for Play; after it exits, allow a minute for Wine's game startup handoff.
remaining=120
seen_wow=0
while true; do
  if pgrep -u "$(id -u)" -i -x 'Wow(-64|T|B|Classic|ClassicT|ClassicB)?\.exe' >/dev/null; then
    seen_wow=1
  else
    status=$?
    (( status == 1 )) || exit "$status"
    (( seen_wow == 0 )) || exit 0
    if pgrep -u "$(id -u)" -i -x 'Battle\.net\.exe' >/dev/null; then
      remaining=60
    else
      status=$?
      (( status == 1 )) || exit "$status"
      remaining=$((remaining - 2))
      (( remaining > 0 )) || exit 0
    fi
  fi
  sleep 2
done
