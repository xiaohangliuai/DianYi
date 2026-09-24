# DianYi (点译)

Select English. See Chinese.

DianYi is an offline English-to-Simplified-Chinese desktop utility for Ubuntu
24.04 on an X11 session. The project is currently at the capture-prototype
milestone described in [MVP_PLAN.md](MVP_PLAN.md).

## Development

The prototype uses Ubuntu's system Python bindings for GTK, AT-SPI, and X11.
Run its dependency check with:

```bash
PYTHONPATH=src python3 -m dianyi --check
```

Run the unit tests with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run the capture-only prototype from an Ubuntu X11 session with:

```bash
PYTHONPATH=src python3 -m dianyi --capture
```

Install the pinned, checksum-verified ECDICT release once:

```bash
PYTHONPATH=src python3 -m dianyi --install-dictionary
```

Sentence translation additionally requires the optional Argos runtime and
the pinned model:

```bash
python3 -m pip install '.[translation]'
PYTHONPATH=src python3 -m dianyi --install-model
```

Then double-click an English word. If its application exposes a fresh AT-SPI
text selection, DianYi displays its local dictionary entry near the pointer.
Select a phrase or sentence and press `Super+T` to translate it offline; a
loading state appears immediately while Argos works on its background thread.
Click elsewhere to close the popup; press `Ctrl+C` in the launching terminal
to stop the service. No selected text is logged or persisted.
