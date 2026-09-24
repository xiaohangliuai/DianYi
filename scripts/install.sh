#!/usr/bin/env bash
set -euo pipefail

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
install_prefix=${DIANYI_PREFIX:-"$HOME/.local"}
runtime_root="$install_prefix/lib/dianyi"
venv_path="$runtime_root/venv"
launcher_path="$install_prefix/bin/dianyi"
config_home=${XDG_CONFIG_HOME:-"$HOME/.config"}
autostart_path="$config_home/autostart/dianyi.desktop"

if ! python3 -c 'import ensurepip' >/dev/null 2>&1; then
    printf '%s\n' 'Missing Ubuntu package: python3.12-venv' >&2
    printf '%s\n' 'Install it with: sudo apt install python3.12-venv' >&2
    exit 1
fi

for module in gi Xlib; do
    if ! python3 -c "import $module" >/dev/null 2>&1; then
        printf 'Missing Ubuntu system Python module: %s\n' "$module" >&2
        printf '%s\n' 'Install python3-gi, gir1.2-gtk-3.0, gir1.2-atspi-2.0, and python3-xlib first.' >&2
        exit 1
    fi
done

mkdir -p "$runtime_root" "$install_prefix/bin" "$(dirname -- "$autostart_path")"
python3 -m venv --clear --system-site-packages "$venv_path"

"$venv_path/bin/python" -m pip install --disable-pip-version-check --upgrade "$project_root"
ln -sfn "$venv_path/bin/dianyi" "$launcher_path"

if [[ ${DIANYI_SKIP_DOWNLOADS:-0} != 1 ]]; then
    "$launcher_path" --install-dictionary
fi

escaped_launcher=${launcher_path//\\/\\\\}
escaped_launcher=${escaped_launcher//\"/\\\"}
desktop_temporary=$(mktemp "$(dirname -- "$autostart_path")/.dianyi.desktop.XXXXXX")
trap 'rm -f -- "$desktop_temporary"' EXIT
{
    printf '%s\n' '[Desktop Entry]'
    printf '%s\n' 'Type=Application'
    printf '%s\n' 'Name=DianYi'
    printf '%s\n' 'Comment=Offline English-to-Chinese word lookup'
    printf 'Exec="%s" --capture\n' "$escaped_launcher"
    printf '%s\n' 'Terminal=false'
    printf '%s\n' 'OnlyShowIn=GNOME;'
    printf '%s\n' 'X-GNOME-Autostart-enabled=true'
} >"$desktop_temporary"
chmod 0644 "$desktop_temporary"
mv -f -- "$desktop_temporary" "$autostart_path"
trap - EXIT

printf 'DianYi installed. Start it with: %s --capture\n' "$launcher_path"
