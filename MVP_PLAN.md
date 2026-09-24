# DianYi (点译) MVP Plan

**Tagline:** Select English. See Chinese.

## Summary

DianYi is a personal, offline English-to-Simplified-Chinese utility for Ubuntu 24.04 with GNOME 46 on X11.

- Double-clicking one English word opens a small dictionary popup near the pointer.
- Selecting a phrase or sentence and pressing `Super+T` opens its Chinese translation.
- Clicking elsewhere or pressing Escape closes the popup.
- The application starts automatically after login and can be paused from a tray menu.
- The MVP targets X11. Wayland support is deferred until its capture method is separately proven.

## Implementation

### Capture and validation

- Run one Python 3.12 background process using X11 input events.
- Detect double-clicks using the desktop's configured click-time and movement thresholds.
- Combine the click with a fresh AT-SPI text-selection event or X11 PRIMARY-selection update; never translate an older selection.
- Automatically look up only a single word. Dragged multiword selections wait for the sentence shortcut.
- Refuse empty selections, password fields, non-English text, and selections from applications in the user's blocklist.
- Register `Super+T` as the default configurable X11 global shortcut.
- Detect shortcut-registration conflicts and show a clear warning instead of silently failing.

### Word lookup

- Convert a pinned release of the MIT-licensed [ECDICT](https://github.com/skywind3000/ECDICT) dataset into an indexed local SQLite database during installation.
- Look up the exact word first, then resolve common inflections such as `running` to `run` and `children` to `child` through a reverse inflection index.
- Show the selected word, normalized headword when different, phonetic spelling, parts of speech, and Chinese meanings.
- If the dictionary has no entry, use the sentence engine as a labeled fallback rather than displaying nothing.

### Sentence translation

- Use the offline Argos `en` to `zh` model published in its [model index](https://github.com/argosopentech/argospm-index/blob/main/index.json).
- Load the model lazily on the first sentence request and run translation on a worker thread so the desktop and popup remain responsive.
- Show a loading state immediately, cache recent results in memory, and discard late results when a newer request exists.
- Keep the translator behind the internal interfaces `lookup_word(text)` and `translate_sentence(text)` so another offline engine can replace Argos after quality evaluation.

### Popup and controls

- Build the popup and preferences with GTK 3 for reliable X11 positioning.
- Keep the popup above normal windows without taking keyboard focus or altering the selection.
- Clamp it to the active monitor, wrap long content, and provide scrolling for sentence results.
- Close it when the user clicks elsewhere or presses Escape; a new request replaces the existing popup.
- Add a tray menu with Pause/Resume, Preferences, and Quit.
- Allow changing the sentence shortcut, toggling automatic word lookup, and managing blocked applications by X11 `WM_CLASS`.
- Store preferences locally and never log or persist selected text.

### Installation

- Provide personal install and uninstall scripts under `~/.local`, plus an XDG autostart entry.
- Create an isolated Python environment while using Ubuntu's system GTK and AT-SPI bindings.
- Download pinned dictionary and translation-model versions during installation and verify their checksums.
- Require no network connection after installation.
- Download the Argos model rather than redistributing it. A future public release must separately audit model-data licensing.

## Test and Acceptance Plan

- Start with a capture-only prototype. Continue to the dictionary, translator, and finished UI only after it reliably obtains the newly selected word in Firefox, Chromium, GNOME Text Editor, Terminal, LibreOffice, and Document Viewer.
- Test repeated selection of the same word, punctuation, hyphenated words, contractions, inflections, non-English text, empty areas, desktop icons, and stale PRIMARY-selection content.
- Confirm dragged sentences never trigger automatic lookup and translate only through `Super+T`.
- Confirm password fields, blocked applications, paused mode, shortcut conflicts, service restart, and application exit behave safely.
- Verify outside-click and Escape dismissal, no focus stealing, multi-monitor placement, fractional scaling, light and dark themes, rapid successive requests, and model errors.
- Target dictionary display within 200 ms after selection becomes available; show sentence-loading feedback within 100 ms.
- Evaluate Argos with 50 representative sentences from normal reading. Accept it for the MVP if at least 40 preserve the essential meaning and none produce runaway or repeated output; otherwise replace the sentence engine before release.
- Disconnect networking after installation and repeat word and sentence tests to confirm fully offline operation.

## Assumptions

- The target is Ubuntu 24.04 with GNOME 46 running an X11 session.
- Output is Simplified Chinese.
- The MVP is for personal use and is installed through scripts rather than a `.deb` package or extension store.
- Images, scanned PDFs, games, remote desktops, canvas-only text, and applications that expose neither PRIMARY selection nor AT-SPI text remain unsupported.
- Wayland is a separate follow-up milestone with its own capture feasibility test; the dictionary, translator, preferences, and popup behavior remain reusable.
