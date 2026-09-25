# DianYi · 点译

**Double-click an English word. See its Chinese meaning.**

DianYi is a small, offline dictionary utility for Ubuntu on X11. Look up a word
while reading in Chrome, the ChatGPT desktop app, OnlyOffice, or another
compatible application—without switching to a dictionary window.

## See it in action

![Animated DianYi demo: double-click curious, see its Chinese meanings, then click away to close the popup.](docs/assets/double-click-demo.gif)

*Illustrated interaction using the real ECDICT entry for “curious.” The popup
uses this rounded blue card style; font rendering and display scaling may vary.
[View a still image](docs/assets/double-click-preview.png).*

## Features

- **Offline English → Simplified Chinese:** local ECDICT definitions, phonetic
  spelling, and parts of speech when available.
- **Double-click to look up:** the popup appears about 0.5 cm right and below
  the click, adjusted for display scaling and screen edges.
- **Inflection lookup:** resolves dictionary-listed forms to their headword
  when there is no exact entry.
- **Browser support:** accessibility selections plus a fresh X11 selection
  fallback for Chrome and compatible desktop apps.
- **Tray controls:** pause or resume lookup, manage blocked applications, and quit.
- **Local operation:** no account, API key, selected-text history, or sentence model.

This MVP looks up **one English word at a time**. It does not translate sentences
or recognize text inside images and scanned PDFs. Chrome, the ChatGPT desktop
app, and OnlyOffice have been confirmed working on the development machine;
other applications depend on how they expose selected text.

## Small dictionary, small footprint

DianYi currently uses a compact ECDICT database to keep storage use low. The
installed dictionary on the development machine is approximately **34 MiB**, with
about **399,000 word entries**. The installer also keeps a roughly **63 MiB CSV
download cache**, so the dictionary and its cache together use about **97 MiB**.
These figures exclude system dependencies and the source checkout; your size
may vary. No large neural translation model is installed.

The tradeoff is dictionary coverage and detail: results can be brief, dated, or
missing specialized meanings. A word's definition may also differ from its
meaning in the sentence you are reading. DianYi displays dictionary entries;
it does not interpret sentence context.

**Want richer results?** A larger, well-curated English–Chinese dictionary with
more senses, examples, or specialist vocabulary may improve coverage, at the
cost of more storage. A bigger file alone does not guarantee better definitions.

There is currently **no built-in dictionary selector or one-click upgrade**.
Replacing the dataset is a developer task: use a suitably licensed dictionary,
convert it to the supported ECDICT CSV fields or adapt the importer, rebuild
the SQLite database, and update the installer source, checksum, and attribution.
See [the importer](src/dianyi/dictionary/importer.py),
[the installer](src/dianyi/dictionary/install.py), and
[third-party notices](THIRD_PARTY_NOTICES.md).

## Install

The supported target is **Ubuntu 24.04, Python 3.12, and an X11 desktop session**.
Wayland is not supported yet. Check your session with:

```bash
echo "$XDG_SESSION_TYPE"
```

It should print `x11`. On Ubuntu, choose **Ubuntu on Xorg** at the login screen
if necessary.

Install these Ubuntu dependencies if missing. This step requires administrator
access; DianYi itself installs into your user account.

```bash
sudo apt install git python3-gi python3-cairo python3-gi-cairo \
  gir1.2-gtk-3.0 gir1.2-atspi-2.0 python3-xlib
```

Then clone and install:

```bash
git clone https://github.com/xiaohangliuai/DianYi.git
cd DianYi
./scripts/install.sh
```

The installer creates a private Python environment under `~/.local/lib/dianyi`,
downloads and verifies the pinned ECDICT dictionary, and adds a GNOME login
autostart entry. Installation needs internet access; lookup works offline
afterwards. If `ensurepip` is unavailable, the installer supports a pip-free
installation using the system GTK and X11 bindings.

## Use

Start DianYi once:

```bash
~/.local/bin/dianyi --capture
```

There is no main window: the tray icon indicates that the service is running.
Leave the launching terminal open. DianYi will also start automatically after
your next GNOME login; avoid launching another copy if it is already running.

1. Double-click a single English word in selectable text.
2. Read its Chinese dictionary entry in the popup.
3. Click elsewhere or press **Escape** to dismiss it.

Click the tray icon to open the menu. A checked **Pause word lookup** item means
lookup is paused; uncheck it to resume. **Preferences** contains automatic lookup
and the application blocklist. Use **Quit**, or `Ctrl+C` in the launching terminal,
to stop the service.

## If no popup appears

- Confirm the session is X11 and **Pause word lookup** is unchecked.
- In Preferences, confirm automatic lookup is enabled and the app is not blocked.
- Double-click actual selectable English text. Phrases, images, scanned PDFs,
  and empty areas do not trigger a lookup.
- Browser fallback requires XFixes and XRes 1.2. It rejects old selections and
  selections whose owner cannot be matched to the active application's process.
- Check system Python dependencies with `~/.local/bin/dianyi --check`. This checks
  imports; it does not prove that a particular app exposes selections.
- If the dictionary is missing, run `~/.local/bin/dianyi --install-dictionary`.

## Update or uninstall

Quit DianYi from its tray menu before updating, then run from the repository:

```bash
git pull --ff-only
./scripts/install.sh
~/.local/bin/dianyi --capture
```

Remove the installed runtime and autostart entry while keeping your dictionary,
cache, and preferences:

```bash
./scripts/uninstall.sh
```

To also delete DianYi's saved data, use `./scripts/uninstall.sh --purge`.

## Privacy and data

Word lookup runs locally. Selected text is not logged, persisted, or sent to a
translation service. The X11 fallback reads PRIMARY selected text only for a
fresh double-click, checks the owner and active application, and rejects
multiword text. It does not send Copy keystrokes or overwrite the clipboard.

Definitions come from the pinned MIT-licensed ECDICT dataset. Its license is
saved beside the installed database. See [third-party notices](THIRD_PARTY_NOTICES.md)
and the [MVP plan](MVP_PLAN.md).

## Development

```bash
PYTHONPATH=src python3 -m dianyi --check
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m dianyi --capture
```

To regenerate the illustrated GIF and still image, install Pillow plus the
DejaVu Sans and Noto Sans CJK fonts, then run `python3 scripts/render_demo.py`.
These are documentation tools, not application runtime dependencies.
