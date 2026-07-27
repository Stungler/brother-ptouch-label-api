# Contributing

Bug reports, hardware test results, documentation fixes, and focused pull
requests are welcome.

## Before opening an issue

- Check whether the printer model and tape width are already documented.
- Include the printer model, tape width, operating system, Python version, and
  whether the API runs directly or in Docker.
- Remove printer addresses, SNMP communities, label contents, hostnames, and
  other private data from logs and screenshots.
- For alignment problems, describe the direction and approximate size of the
  offset and include a redacted photo when possible.

Use the private reporting guidance in `SECURITY.md` for vulnerabilities.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run both test suites before submitting a change:

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s printers/rasterprynt_ext/tests -v
```

Changes to tape geometry should preserve existing values unless they have been
checked on hardware. Clearly label unverified model or tape-width support.

## Pull requests

Keep changes focused and explain:

- what behavior changed;
- how it was tested without exposing private network information;
- which printer models and tape widths were tested on hardware;
- whether the API schema or raster output changed.

Third-party code and assets must include compatible licenses and attribution.
