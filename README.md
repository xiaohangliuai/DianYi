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

The interactive capture service will be enabled in a later milestone.
