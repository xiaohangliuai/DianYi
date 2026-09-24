#!/usr/bin/env bash
set -euo pipefail

install_prefix=${DIANYI_PREFIX:-"$HOME/.local"}
runtime_root="$install_prefix/lib/dianyi"
launcher_path="$install_prefix/bin/dianyi"
config_home=${XDG_CONFIG_HOME:-"$HOME/.config"}
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
cache_home=${XDG_CACHE_HOME:-"$HOME/.cache"}
autostart_path="$config_home/autostart/dianyi.desktop"

rm -f -- "$autostart_path" "$launcher_path"
rm -rf -- "$runtime_root"

if [[ ${1:-} == --purge ]]; then
    rm -rf -- \
        "$config_home/dianyi" \
        "$data_home/dianyi" \
        "$cache_home/dianyi"
    printf '%s\n' 'DianYi and its local data were removed.'
else
    printf '%s\n' 'DianYi was removed; dictionary, cache, and preferences were preserved.'
    printf '%s\n' 'Run this script with --purge to remove those local data files too.'
fi
