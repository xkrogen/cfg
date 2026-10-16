#!/usr/bin/env bash

# One user bus per RDev pod, started by shell/tool bootstrap, not supervised.
# Go credential clients also discover /run/user/<uid>/bus without an environment
# change, so already-running agents can reuse it. An explicit address is respected
# and checked instead. An unhealthy existing endpoint fails without replacement.

set -eu

rdev_bus_ready() {
    gdbus call --address "$1" --dest org.freedesktop.DBus \
        --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetId \
        --timeout 2 >/dev/null
}

# The subshell scopes the startup lock to this call. runtime_dir is the standard
# per-UID directory in production; an isolated directory supports native tests.
ensure_rdev_dbus() (
    local runtime_dir="$1"
    local address="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$runtime_dir/bus}"

    if [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
        rdev_bus_ready "$address" || {
            echo "[rdev-dbus] ERROR: configured bus is unavailable: $address" >&2
            return 1
        }
        return 0
    fi

    if [ ! -d "$runtime_dir" ]; then
        sudo -n install -d -m 700 -o "$(id -u)" -g "$(id -g)" "$runtime_dir"
    fi
    if [ ! -O "$runtime_dir" ]; then
        echo "[rdev-dbus] ERROR: runtime directory is not owned by this UID: $runtime_dir" >&2
        return 1
    fi

    exec 9>"$runtime_dir/dbus-start.lock"
    flock 9
    if [ ! -e "$runtime_dir/bus" ]; then
        # A forked daemon must not retain the bootstrap lock.
        dbus-daemon --session --fork --syslog-only --address="$address" 9>&-
    fi
    rdev_bus_ready "$address" || {
        echo "[rdev-dbus] ERROR: user bus is unavailable: $address; inspect the endpoint before restarting it." >&2
        return 1
    }
)

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    if [ "$(uname -s)" != Linux ]; then
        echo "[rdev-dbus] ERROR: this bootstrap requires Linux." >&2
        exit 1
    fi
    ensure_rdev_dbus "/run/user/$(id -u)"
fi
