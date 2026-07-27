# API examples

These examples assume the API is running on `http://127.0.0.1:8000`.
Replace `192.168.1.50` with your printer's address.

## Register a printer

```bash
curl -X POST http://127.0.0.1:8000/printers \
  -H "Content-Type: application/json" \
  -d '{
    "printer_id": "labels-18mm",
    "name": "PT-P950NW with 18 mm tape",
    "ip": "192.168.1.50",
    "model": "PT-P950NW",
    "tape_size_mm": 18
  }'
```

Register each physical printer separately when you keep multiple tape widths
loaded. The API accepts 6, 9, 12, 18, 24, and 36 mm configurations. Only 6, 9,
and 18 mm have been verified on hardware by the maintainer.

## Print one label

Let the API choose a printer by tape width:

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

Or target a registered printer explicitly:

```bash
curl -X POST http://127.0.0.1:8000/printers/labels-18mm/print \
  -H "Content-Type: application/json" \
  -d '{
    "text": "SHELF-A-0042",
    "label_type": "TEXT",
    "tape_size": 18,
    "copies": 2
  }'
```

Valid `label_type` values are `TEXT`, `QR`, and `TEXT_QR`.

## Submit a numbered batch

This queues `ASSET-0001` through `ASSET-0010`:

```bash
for number in $(seq -w 1 10); do
  curl -sS -X POST http://127.0.0.1:8000/printers/auto/print \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"ASSET-00${number}\",\"label_type\":\"TEXT_QR\",\"tape_size\":18,\"copies\":1}"
  echo
done
```

## Track jobs and queues

Every successful queue response includes a `job_id`:

```bash
curl http://127.0.0.1:8000/print-jobs/YOUR_JOB_ID
curl http://127.0.0.1:8000/printers/labels-18mm/queue
```

Job states are `queued`, `running`, `done`, or `failed`.

## Read printer status

```bash
curl http://127.0.0.1:8000/printers/status
curl http://127.0.0.1:8000/printers/labels-18mm/status
```

The service tries ping first, then selected TCP ports, and reads the printer
status through SNMP. Configure the read community with
`PRINTER_SNMP_READ_COMMUNITY` when the printer does not use `public`.

## Reboot through SNMP

The write community is read from `PRINTER_SNMP_WRITE_COMMUNITY` when the
request does not provide one:

```bash
curl -X POST http://127.0.0.1:8000/printers/labels-18mm/reboot \
  -H "Content-Type: application/json" \
  -d '{
    "wait_until_online": true,
    "timeout_s": 120,
    "grace_s": 5
  }'
```

You can override it for one request, but environment-based configuration avoids
placing a community string in shell history:

```json
{
  "community": "device-specific-write-community",
  "wait_until_online": true
}
```

## Update or remove a printer

```bash
curl -X PATCH http://127.0.0.1:8000/printers/labels-18mm \
  -H "Content-Type: application/json" \
  -d '{"name": "Workshop labels", "enabled": true}'

curl -X DELETE http://127.0.0.1:8000/printers/labels-18mm
```

## Utility and legacy endpoints

```bash
curl http://127.0.0.1:8000/printer/sizes
curl http://127.0.0.1:8000/printer/font-check
```

The legacy single-printer flow is retained for compatibility:

```bash
curl -X POST "http://127.0.0.1:8000/printer/init?ip=192.168.1.50&model=PT-P950NW"

curl -X POST http://127.0.0.1:8000/printer/print \
  -H "Content-Type: application/json" \
  -d '{
    "text": "LEGACY-0001",
    "label_type": "TEXT_QR",
    "tape_size": 18,
    "copies": 1
  }'
```
