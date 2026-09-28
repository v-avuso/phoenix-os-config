set -euo pipefail

# systemd-sleep hooks run with a restricted environment and may have no PATH.
export PATH=@DJI_HOOK_PATH@

readonly STATE_DIR=/run/phoenix-dji-hibernate-wakeup
readonly STATE_FILE="$STATE_DIR/controllers.tsv"
readonly LOCK_FILE=/run/lock/phoenix-dji-hibernate-wakeup.lock
log() {
  logger -t phoenix-dji-hibernate-wakeup -- "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

restore_saved_controllers() {
  local pci original sysfs current failed=0

  [[ -f "$STATE_FILE" ]] || return 0

  while IFS=$'\t' read -r pci original; do
    [[ -n "$pci" ]] || continue
    if [[ ! "$pci" =~ ^[[:xdigit:]]{4}:[[:xdigit:]]{2}:[[:xdigit:]]{2}\.[0-7]$ ]] ||
       [[ "$original" != enabled && "$original" != disabled ]]; then
      log "ERROR: invalid saved controller state; leaving $STATE_FILE for inspection"
      failed=1
      continue
    fi

    sysfs="/sys/bus/pci/devices/$pci/power/wakeup"
    if [[ ! -r "$sysfs" || ! -w "$sysfs" ]]; then
      log "ERROR: cannot restore $pci wake state; sysfs path is unavailable"
      failed=1
      continue
    fi

    current=$(<"$sysfs")
    if [[ "$current" != "$original" ]]; then
      if ! printf '%s\n' "$original" > "$sysfs"; then
        log "ERROR: failed to restore $pci power/wakeup=$original"
        failed=1
        continue
      fi
      current=$(<"$sysfs")
    fi

    if [[ "$current" != "$original" ]]; then
      log "ERROR: $pci power/wakeup is $current after restore; expected $original"
      failed=1
    else
      log "restored $pci power/wakeup=$original"
    fi
  done < "$STATE_FILE"

  if (( failed == 0 )); then
    rm -f -- "$STATE_FILE"
    rmdir -- "$STATE_DIR" 2>/dev/null || true
  fi

  return "$failed"
}

sleep_action=${SYSTEMD_SLEEP_ACTION:-${2:-}}
if [[ "$sleep_action" != hibernate ]]; then
  exit 0
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  fail "another invocation holds the state lock"
fi

phase=${1:-}
case "$phase" in
  pre)
    if [[ -e "$STATE_FILE" ]]; then
      log "stale saved state found; attempting recovery before discovery"
      restore_saved_controllers || fail "could not recover stale wake state"
    fi

    declare -A controllers=()
    found_dji=0
    for device in /sys/bus/usb/devices/*; do
      [[ -r "$device/idVendor" && -r "$device/idProduct" ]] || continue
      [[ "$(<"$device/idVendor")" == 2ca3 && "$(<"$device/idProduct")" == 4015 ]] || continue
      found_dji=1
      real_device=$(readlink -f -- "$device") || fail "cannot resolve $device"
      ancestor=$real_device
      while [[ "$ancestor" == /sys/devices/* ]]; do
        pci=${ancestor##*/}
        if [[ "$pci" =~ ^[[:xdigit:]]{4}:[[:xdigit:]]{2}:[[:xdigit:]]{2}\.[0-7]$ ]] &&
           [[ -r "$ancestor/class" && "$(<"$ancestor/class")" == 0x0c0330 ]] &&
           [[ -r "$ancestor/vendor" && -r "$ancestor/device" && -e "$ancestor/power/wakeup" ]]; then
          controllers["$pci"]=1
          break
        fi
        ancestor=${ancestor%/*}
      done
    done

    if (( found_dji == 0 )); then
      log "DJI 2ca3:4015 absent; no controller wake settings changed"
      exit 0
    fi
    if (( ${#controllers[@]} == 0 )); then
      fail "DJI 2ca3:4015 found but no owning PCI xHCI controller was resolved"
    fi

    declare -a selected=()
    for pci in "${!controllers[@]}"; do
      sysfs="/sys/bus/pci/devices/$pci/power/wakeup"
      [[ -r "$sysfs" && -w "$sysfs" ]] || fail "cannot read/write $pci power/wakeup"
      current=$(<"$sysfs")
      case "$current" in
        enabled) selected+=("$pci") ;;
        disabled) log "selected $pci; wakeup was already disabled" ;;
        *) fail "unexpected $pci power/wakeup value: $current" ;;
      esac
    done

    if (( ${#selected[@]} == 0 )); then
      log "DJI found; all owning controller wake settings were already disabled"
      exit 0
    fi

    umask 0077
    mkdir -p -- "$STATE_DIR"
    : > "$STATE_FILE"
    for pci in "${selected[@]}"; do
      sysfs="/sys/bus/pci/devices/$pci/power/wakeup"
      printf '%s\tenabled\n' "$pci" >> "$STATE_FILE"
      if ! printf 'disabled\n' > "$sysfs"; then
        restore_saved_controllers || fail "disable failed and wake-state restoration also failed"
        fail "could not disable wakeup on $pci"
      fi
      current=$(<"$sysfs")
      if [[ "$current" != disabled ]]; then
        restore_saved_controllers || fail "verification failed and wake-state restoration also failed"
        fail "$pci power/wakeup is $current after attempting to disable it"
      fi
      log "DJI found; selected owning controller $pci; temporarily set power/wakeup=disabled (original=enabled)"
    done
    ;;

  post)
    if [[ -f "$STATE_FILE" ]]; then
      restore_saved_controllers || fail "one or more controller wake settings could not be restored"
    else
      log "hibernate post phase; no controller wake state needs restoration"
    fi
    ;;

  *)
    fail "unexpected system-sleep phase: $phase"
    ;;
esac
