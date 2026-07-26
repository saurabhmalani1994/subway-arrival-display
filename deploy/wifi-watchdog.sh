#!/usr/bin/env bash
#
# Wi-Fi watchdog for a headless Raspberry Pi.
#
# The failure this exists for: on a power cut, the Pi boots faster than the
# router. It finds no network, gives up, and sits there unreachable until
# someone attaches a monitor and keyboard. This notices and reconnects.
#
# Health check is "can I reach my default gateway", NOT "am I on a specific
# SSID". That matters: if you rescue the Pi with a phone hotspot, the watchdog
# must see that as healthy and leave it alone rather than fighting you.
#
# Install: see docs/TROUBLESHOOTING.md

set -uo pipefail

STATE_FILE="/run/wifi-watchdog.failures"
RECONNECT_AFTER=2   # consecutive failures before trying to re-associate
REBOOT_AFTER=6      # consecutive failures before rebooting (0 disables)
PING_TIMEOUT=5

log() { echo "wifi-watchdog: $*"; }

read_failures() {
    [[ -f "$STATE_FILE" ]] && cat "$STATE_FILE" 2>/dev/null || echo 0
}

gateway() {
    ip route show default 2>/dev/null | awk '/default/ {print $3; exit}'
}

healthy() {
    local gw
    gw=$(gateway)
    if [[ -z "$gw" ]]; then
        log "no default gateway"
        return 1
    fi
    if ping -c 1 -W "$PING_TIMEOUT" "$gw" >/dev/null 2>&1; then
        return 0
    fi
    log "gateway $gw did not respond"
    return 1
}

reconnect() {
    log "attempting to re-associate"
    # Bring up whichever wifi profile NetworkManager thinks is best. This will
    # happily pick a pre-saved phone hotspot if home wifi is gone.
    if command -v nmcli >/dev/null 2>&1; then
        nmcli radio wifi on >/dev/null 2>&1
        if ! nmcli device connect wlan0 >/dev/null 2>&1; then
            log "device connect failed; cycling networking"
            nmcli networking off
            sleep 2
            nmcli networking on
        fi
    else
        log "nmcli not found; falling back to interface bounce"
        ip link set wlan0 down && sleep 2 && ip link set wlan0 up
    fi
}

main() {
    if healthy; then
        if [[ "$(read_failures)" != "0" ]]; then
            log "connectivity restored"
        fi
        echo 0 > "$STATE_FILE"
        exit 0
    fi

    failures=$(( $(read_failures) + 1 ))
    echo "$failures" > "$STATE_FILE"
    log "failure $failures"

    if (( REBOOT_AFTER > 0 && failures >= REBOOT_AFTER )); then
        log "still down after $failures checks — rebooting"
        echo 0 > "$STATE_FILE"
        systemctl reboot
        exit 0
    fi

    if (( failures >= RECONNECT_AFTER )); then
        reconnect
    fi
}

main "$@"
