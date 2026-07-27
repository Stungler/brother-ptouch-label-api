# rasterprynt-ext

`rasterprynt-ext` is the low-level Brother raster encoder and TCP transport used
by the parent Brother P-touch Network Label API. It is derived from
[`boxine/rasterprynt`](https://github.com/boxine/rasterprynt), originally
written by Philipp Hagemeister and released under the MIT License.

This extension adds calibrated PT-P950NW tape widths, modern Python packaging,
type annotations, explicit validation, a decoder utility, and byte-level
regression tests.

## Supported protocol paths

| Model | Configured tape widths |
| --- | --- |
| PT-P950NW | 3.5, 6, 9, 12, 18, 24, and 36 mm |
| PT-9800PCN | 18 mm, inherited from upstream |

Within the parent project, only PT-P950NW widths 6, 9, and 18 mm have been
verified on hardware by the maintainer. Other entries are calibration starting
points, not hardware-support guarantees.

## Installation

From this directory:

```bash
python -m pip install .
```

For development or PCAP decoding:

```bash
python -m pip install ".[dev]"
python -m pip install ".[pcap]"
```

The parent project installs this package from its local path automatically.

## Python API

```python
from PIL import Image
import rasterprynt

image = Image.open("label.png")
rasterprynt.print_images(
    [image],
    "192.168.1.50",
    tape_size="18mm",
    printer_model="P950NW",
)
```

The clearer public names are:

- `render(...)` — iterate over command-byte chunks
- `render_bytes(...)` — return one complete command stream
- `print_images(...)` — render and send to TCP port 9100
- `detect_printer_model(...)` — inspect the printer's embedded web page
- `send(...)` — send already-rendered bytes

The upstream names `cat(...)` and `prynt(...)` remain as compatibility wrappers.

## Command line

Print images:

```bash
rasterprynt 192.168.1.50 label.png \
  --printer-model P950NW \
  --tape-size 18mm
```

Generate command bytes without contacting a printer:

```bash
rasterprynt 192.0.2.10 label.png \
  --printer-model P950NW \
  --tape-size 18mm \
  --to-file label.bin
```

Decode a command stream into a portable bitmap:

```bash
rasterprynt-decode label.bin label.pbm
```

Classic PCAP extraction is available when the `pcap` optional dependency is
installed.

## Development

```bash
python -m unittest discover -s tests -v
python -m ruff check rasterprynt tests examples
python -m ruff format --check rasterprynt tests examples
```

Golden SHA-256 fixtures verify that refactoring does not alter emitted command
bytes for any configured media entry.

## License

The original and modified code is distributed under the MIT License in
[`LICENSE`](LICENSE). The original project URL and authorship remain in the
package metadata and the parent repository's `NOTICE`.
