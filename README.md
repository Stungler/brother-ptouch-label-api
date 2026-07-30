# labelprynt

A self-hosted Python REST API for printing labels directly to Brother P-touch
network printers. It generates raster images, converts them to Brother printer
commands, and sends them to TCP port 9100—no Brother P-touch Editor installation
or proprietary desktop printer driver is required.

The project is built around an extended version of
[Philipp Hagemeister's `rasterprynt`](https://github.com/boxine/rasterprynt),
with a FastAPI service, text/QR label generation, a JSON printer registry,
per-printer queues, and optional SNMP status/reboot support.

> [!IMPORTANT]
> The Brother raster protocol support and tape calibration are based on
> reverse engineering and hardware testing. This project is not affiliated
> with or endorsed by Brother Industries.

## What it can do

- Print over the network directly to a Brother PT-P950NW on raw TCP port 9100
- Generate `TEXT`, `QR`, and combined `TEXT_QR` labels
- Route jobs automatically to a printer with the requested tape width
- Serialize jobs per printer while allowing different printers to work in parallel
- Track queued, running, completed, and failed jobs through the API
- Check reachability and printer state through ping/TCP and SNMP
- Reboot a printer through SNMP when explicitly requested
- Use any Pillow-compatible image with the lower-level Python printing function

The built-in layouts are intentionally small and understandable. You can extend
`core/label_generator.py` with images, logos, multiple text lines, barcodes, or
other content that Pillow can render.

## Hardware support

| Printer | Tape width | Status |
| --- | ---: | --- |
| Brother PT-P950NW | 6 mm | Hardware verified |
| Brother PT-P950NW | 9 mm | Hardware verified |
| Brother PT-P950NW | 18 mm | Hardware verified |
| Brother PT-P950NW | 12 mm | Experimental; calibration may be required |
| Brother PT-P950NW | 24 mm | Experimental; calibration may be required |
| Brother PT-P950NW | 36 mm | Experimental; calibration may be required |

Other Brother P-touch models may share parts of the protocol, but they have not
been tested by this project's maintainer. Print-head geometry, margins, media
commands, cutting, and model detection may need adjustment.

## Quick start

Requirements:

- Python 3.11 or newer
- A supported printer reachable from the API host
- TCP port 9100 open between the API host and printer

Create a virtual environment and install the application:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

On PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Open `http://127.0.0.1:8000/docs` for the interactive Swagger UI.

### Register a printer

Replace `192.168.1.50` with the address of your printer:

```bash
curl -X POST http://127.0.0.1:8000/printers \
  -H "Content-Type: application/json" \
  -d '{
    "printer_id": "labels-18mm",
    "name": "Workshop PT-P950NW",
    "ip": "192.168.1.50",
    "model": "PT-P950NW",
    "tape_size_mm": 18
  }'
```

### Queue a label

Use `auto` to select an enabled printer configured for the requested tape size:

```bash
curl -X POST http://127.0.0.1:8000/printers/auto/print \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ASSET-0001",
    "label_type": "TEXT_QR",
    "tape_size": 18,
    "copies": 1
  }'
```

The response contains a `job_id`. Poll it with:

```bash
curl http://127.0.0.1:8000/print-jobs/YOUR_JOB_ID
```

More registration, batch-printing, status, and reboot examples are in
[`docs/API_EXAMPLES.md`](docs/API_EXAMPLES.md).

## Docker

Copy the example configuration, review it, and start the service:

```bash
cp .env.example .env
docker compose up --build
```

Docker Compose publishes the API on `http://127.0.0.1:8000` by default. Change
`PORT` in `.env` if needed. The `data` directory is mounted so printer
registrations survive container recreation.

Container networking must be able to reach the printer LAN. Docker Desktop,
VLANs, firewalls, and VPN routing can affect that connectivity.

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/printers` | Register a printer |
| `GET` | `/printers` | List registered printers |
| `GET` | `/printers/{printer_id}` | Read one printer |
| `PATCH` | `/printers/{printer_id}` | Update a printer |
| `DELETE` | `/printers/{printer_id}` | Remove a printer |
| `GET` | `/printers/status` | Get live status for all printers |
| `GET` | `/printers/{printer_id}/status` | Get live status for one printer |
| `POST` | `/printers/{printer_id}/print` | Queue a print job; use `auto` as the ID for tape-based selection |
| `GET` | `/printers/{printer_id}/queue` | Inspect active jobs for a printer |
| `GET` | `/print-jobs/{job_id}` | Read a print job's state |
| `POST` | `/printers/{printer_id}/reboot` | Request an SNMP reboot |
| `GET` | `/printer/sizes` | List configured tape widths |
| `GET` | `/printer/font-check` | Check the bundled rendering font |

The legacy `/printer/init` and `/printer/print` endpoints remain available for
existing single-printer integrations. New integrations should use the queued
`/printers/{printer_id}/print` endpoint.

## Configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8000` | Host port used by Docker Compose |
| `PRINTER_REGISTRY_PATH` | `data/printers.json` | JSON printer-registry location |
| `PRINTER_SNMP_READ_COMMUNITY` | `public` | SNMP v1 community used for status reads |
| `PRINTER_SNMP_WRITE_COMMUNITY` | `private` | SNMP v1 community used for reboot requests and automatic error recovery |

Do not commit a populated `data/printers.json` or a real `.env` file. Both are
ignored by Git and the Docker build context.

## Printing an arbitrary image

The REST API currently exposes the built-in label layouts. The lower-level
Python interface accepts Pillow images, so custom PNG-based workflows can be
added without changing the raster transport:

```python
from PIL import Image

from core.printing import print_labels_to_ip

image = Image.open("my-label.png")
print_labels_to_ip(
    labels=[image],
    printer_ip="192.168.1.50",
    tape_mm=18,
)
```

The image is flattened onto white, padded to the configured print-head stripe,
converted to Brother raster commands, and sent to port 9100.

## Security

This API has no authentication or authorization. It can print, reveal configured
printer addresses, and request device reboots. Bind it to localhost or place it
behind authentication on a trusted network. Do not expose it directly to the
public internet.

SNMP v1 community strings are transmitted without encryption. Use restricted
network access and set device-specific values through environment variables.
See [`SECURITY.md`](SECURITY.md) for additional guidance.

## Calibration and limitations

- Queue and job state are in memory and reset when the API process restarts.
- Printer registrations are stored in a local JSON file.
- Automatic recovery only runs when SNMP reports the exact status `ERROR`.
- Tape geometry lives in `core/ptp950nw_config.py` and the raster backend's
  `STRIPE_SIZE` table.
- The calibration notebook in `examples/tape_width_calibration.ipynb` previews
  every configured width without containing printer addresses or saved outputs.

When testing a new tape width, start with one copy, inspect vertical alignment
and cut margins, then adjust the calibration values in small increments.

## Development

Run the application and raster-backend tests:

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s printers/rasterprynt_ext/tests -v
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`docs/TESTING.md`](docs/TESTING.md) for the full workflow. Possible extensions
and maintainer-sized project ideas are tracked in [`TODO.md`](TODO.md).

## License and attribution

The project is released under the MIT License; see [`LICENSE`](LICENSE).

The bundled raster transport is derived from
[`boxine/rasterprynt`](https://github.com/boxine/rasterprynt), originally
copyright Philipp Hagemeister and also MIT licensed. The bundled DejaVu Sans
font has its own permissive license. Third-party notices and license locations
are listed in [`NOTICE`](NOTICE).
