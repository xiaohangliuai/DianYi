# DianYi (点译)

Double-click an English word. See its Chinese meaning.

DianYi is an offline English-to-Simplified-Chinese word-lookup utility for
Ubuntu 24.04 on an X11 session. Sentence translation is intentionally outside
the MVP scope.

## Development

The application uses Ubuntu's system Python bindings for GTK, AT-SPI, and X11.
Check those dependencies with:

```bash
PYTHONPATH=src python3 -m dianyi --check
```

Run the unit tests with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Personal installation

Install the application, pinned ECDICT dictionary, and GNOME autostart entry
under your user account:

```bash
./scripts/install.sh
```

No administrator access is required. Remove the runtime while preserving local
data with `./scripts/uninstall.sh`, or explicitly remove all DianYi data with
`./scripts/uninstall.sh --purge`.

To run directly from the repository in an Ubuntu X11 session:

```bash
PYTHONPATH=src python3 -m dianyi --install-dictionary
PYTHONPATH=src python3 -m dianyi --capture
```

Double-click one English word in an application that exposes a fresh AT-SPI
text selection. DianYi displays its local dictionary entry near the pointer.
Phrases and sentences are ignored. Click elsewhere or press Escape to close
the popup; press `Ctrl+C` in the launching terminal to stop the service. No
selected text is logged or persisted.
