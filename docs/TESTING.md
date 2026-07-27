# Testing

The automated suite checks label rendering, tape configuration, registry
persistence, API-to-print parameter forwarding, and the raster transport. It
never connects to a real printer.

## Automated tests

From the repository root:

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s printers/rasterprynt_ext/tests -v
```

## API smoke test

Start the API:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

Check endpoints that do not contact hardware:

```bash
curl http://127.0.0.1:8000/printer/sizes
curl http://127.0.0.1:8000/printer/font-check
curl http://127.0.0.1:8000/printers
```

Use a temporary registry during development when you do not want to modify your
normal configuration:

```bash
PRINTER_REGISTRY_PATH=/tmp/ptouch-printers.json \
  uvicorn main:app --host 127.0.0.1 --port 8000
```

## Hardware test

Hardware tests send raw commands and may consume or cut tape. Use a noncritical
printer and begin with one copy.

1. Register the printer with its real address and loaded tape width.
2. Call `/printers/{printer_id}/status`.
3. Print a short `TEXT` label.
4. Print a `QR` label and scan it.
5. Print a `TEXT_QR` label and inspect vertical placement and cut margins.
6. Confirm that a mismatched requested tape width is rejected.
7. Test reboot only if SNMP write access is configured and a reboot is safe.

Record the exact printer model, firmware version, tape width, tape type, and
calibration changes. Never commit the real registry or SNMP communities.

The output-free notebook at `examples/tape_width_calibration.ipynb` can preview
all configured tape widths before a physical test.
