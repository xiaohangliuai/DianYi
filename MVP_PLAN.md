# DianYi (点译) MVP Plan

**Tagline:** Double-click an English word. See Chinese.

## Summary

DianYi is a personal, offline English-to-Simplified-Chinese word-lookup utility
for Ubuntu 24.04 with GNOME 46 on X11. Sentence translation and its global
shortcut are not part of this MVP.

- Double-clicking one English word opens a dictionary popup near the pointer.
- Phrases, sentences, and non-English selections are ignored.
- Clicking elsewhere or pressing Escape closes the popup.
- The application starts automatically after login and can be paused from a tray menu.
- The MVP targets X11. Wayland support is deferred until its capture method is separately proven.

## Implementation

### Capture and validation

- Run one Python 3.12 background process using X11 input events.
- Detect double-clicks using the desktop's configured click-time and movement thresholds.
- Combine the click with a fresh AT-SPI text-selection event; never look up an older selection.
- Automatically look up only a single English word.
- Refuse empty selections, password fields, multiword selections, non-English text, and selections from applications in the user's blocklist.

### Word lookup

- Convert a pinned release of the MIT-licensed [ECDICT](https://github.com/skywind3000/ECDICT) dataset into an indexed local SQLite database during installation.
- Look up the exact word first, then resolve common inflections such as `running` to `run` and `children` to `child` through a reverse inflection index.
- Show the selected word, normalized headword when different, phonetic spelling, parts of speech, and Chinese meanings.
- Show a clear dictionary-miss message when no entry exists.

### Popup and controls

- Build the popup and preferences with GTK 3 for reliable X11 positioning.
- Keep the popup above normal windows without taking keyboard focus or altering the selection.
- Clamp it to the active monitor, wrap long meanings, and scroll when necessary.
- Close it when the user clicks elsewhere or presses Escape; a new lookup replaces the existing popup.
- Add a tray menu with Pause/Resume, Preferences, and Quit.
- Allow toggling automatic word lookup and managing blocked applications by X11 `WM_CLASS`.
- Store preferences locally and never log or persist selected text.

### Installation

- Provide personal install and uninstall scripts under `~/.local`, plus an XDG autostart entry.
- Create an isolated Python environment while using Ubuntu's system GTK and AT-SPI bindings.
- Download the pinned dictionary version during installation and verify its checksum.
- Require no network connection after installation.

## Test and Acceptance Plan

- Confirm fresh word capture in Firefox, Chromium, GNOME Text Editor, Terminal, LibreOffice, and Document Viewer.
- Test repeated selection of the same word, punctuation, hyphenated words, contractions, inflections, non-English text, empty areas, desktop icons, and stale selections.
- Confirm dragged phrases and sentences never trigger lookup.
- Confirm password fields, blocked applications, paused mode, service restart, and application exit behave safely.
- Verify outside-click and Escape dismissal, no focus stealing, multi-monitor placement, fractional scaling, light and dark themes, and rapid successive lookups.
- Target dictionary display within 200 ms after selection becomes available.
- Disconnect networking after installation and repeat word tests to confirm fully offline operation.

## Assumptions

- The target is Ubuntu 24.04 with GNOME 46 running an X11 session.
- Output is Simplified Chinese dictionary data.
- The MVP is for personal use and is installed through scripts rather than a `.deb` package or extension store.
- Images, scanned PDFs, games, remote desktops, canvas-only text, and applications that do not expose AT-SPI text remain unsupported.
- Wayland is a separate follow-up milestone; the dictionary, preferences, and popup behavior remain reusable.
