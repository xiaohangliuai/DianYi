# DianYi TODO

This list tracks known gaps and the functions most likely to need improvement.
Items are not complete until they work on Ubuntu 24.04 in an X11 session and
have automated regression coverage where practical.

## High priority: application compatibility

### OnlyOffice word lookup does not work reliably

- [ ] Reproduce the failure in an editable document and record whether
  `object:text-selection-changed` is emitted after a double-click.
- [ ] Improve `selection_from_accessible()` in
  `src/dianyi/capture/atspi.py` for the accessible object and text ranges that
  OnlyOffice exposes.
- [ ] Review `X11SelectionSource.__call__()` in
  `src/dianyi/capture/primary_word.py`. OnlyOffice may place the PRIMARY
  selection and active window in different cooperating processes, so strict
  PID equality may reject a valid selection.
- [ ] Add a safe way to attribute related multi-process windows without
  accepting text owned by an unrelated application.
- [ ] Add unit tests for the discovered OnlyOffice event/range and X11 owner
  behavior.
- [ ] Verify repeated double-clicks, a word selected after editing, and a word
  selected in a read-only document.

### Terminal word lookup does not work reliably

- [ ] Reproduce in GNOME Terminal and note whether AT-SPI, X11 PRIMARY, or both
  expose the selected word.
- [ ] Check `AtspiSelectionWatcher._handle_event()` in
  `src/dianyi/capture/atspi.py` for terminal-specific event sources and
  delayed selection updates.
- [ ] Check `SelectionChange.belongs_to()` and
  `PrimaryWordReader.request_word()` in
  `src/dianyi/capture/primary_word.py`; the current 80 ms/750 ms timing limits
  may reject terminal selection updates that arrive later.
- [ ] Make the settle/freshness timing configurable per capture path if traces
  show that timing is the cause. Do not loosen freshness checks globally
  without tests for stale selections.
- [ ] Add regression tests using the event order and timestamps observed in
  the terminal.
- [ ] Verify normal output, wrapped lines, URLs, shell prompts, and rapid
  repeated selections. Confirm that DianYi never types into the terminal or
  changes the CLIPBOARD selection.

## Diagnostics needed for both applications

- [ ] Add an opt-in debug mode that records event type, timestamps, accessible
  role, application name, window ID, PID, and rejection reason.
- [ ] Never log selected text, clipboard contents, dictionary queries, or
  password-field contents.
- [ ] Show which capture path handled a selection (AT-SPI or X11 PRIMARY) and
  why the other path was unavailable or rejected.
- [ ] Add a short troubleshooting guide explaining how to collect a sanitized
  compatibility trace.

## Compatibility acceptance criteria

- [ ] A fresh double-click on one English word opens the correct definition in
  OnlyOffice and GNOME Terminal.
- [ ] Old selections, phrases, password fields, blocked applications, and text
  owned by another application remain rejected.
- [ ] The popup appears only once per gesture and remains responsive during
  rapid repeated lookups.
- [ ] All automated tests pass with
  `PYTHONPATH=src python3 -m unittest discover -s tests -v`.

