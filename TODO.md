# Project roadmap

This is a list of possible extensions, not a promise that every item will be
implemented. Contributions can tackle one focused item at a time.

Hardware support must be based on repeatable tests with the exact printer model,
firmware, tape width, and tape type. Keep unverified configurations marked as
experimental and do not change the calibrated 6, 9, or 18 mm PT-P950NW values
without comparing physical output.

## Label creation

- [ ] Add a preview endpoint that returns the rendered PNG without printing it.
- [ ] Support multiline text, wrapping, alignment, and configurable line spacing.
- [ ] Add image and logo placement to the REST API with file-size, dimension, and
      format limits.
- [ ] Add common one-dimensional barcodes such as Code 128 and EAN-13.
- [ ] Add layout options for font family, font size, margins, rotation, and
      horizontal or vertical alignment.
- [ ] Add reusable label templates with named and typed fields.
- [ ] Improve Unicode and fallback-font handling, including clear diagnostics
      when a requested glyph is unavailable.
- [ ] Add optional borders, separators, and simple geometric shapes.

## Printer and media support

- [ ] Hardware-test and calibrate 12, 24, and 36 mm tape on the PT-P950NW.
- [ ] Record calibration results in a documented compatibility matrix, including
      firmware version and tape type.
- [ ] Add a guided calibration command that generates test patterns and records
      measured offsets.
- [ ] Move model-specific raster geometry and capabilities behind a printer-model
      interface before adding more models.
- [ ] Investigate additional Brother P-touch network printers and add each model
      only with protocol fixtures and hardware test results.
- [ ] Detect the installed tape width and reject mismatched jobs when the printer
      exposes reliable media information.
- [ ] Expose supported cutter behavior, such as no-cut, chain printing, and
      half-cut, where the hardware and protocol support it.
- [ ] Investigate USB transport as an alternative to raw TCP port 9100.
- [ ] Document a privacy-safe workflow for capturing and comparing raster command
      streams during protocol research.

## API and print jobs

- [ ] Add optional API-key authentication and document reverse-proxy
      authentication.
- [ ] Persist jobs and printer registrations in SQLite instead of keeping job
      state in memory and registrations in a JSON file.
- [ ] Add cancellation for queued jobs and configurable retry policies for
      transient network failures.
- [ ] Add job retention limits and automatic cleanup of old job records.
- [ ] Add Server-Sent Events or WebSocket notifications for job-state changes.
- [ ] Support batch requests containing different label contents and layouts.
- [ ] Add idempotency keys so clients can safely retry print submissions.
- [ ] Publish machine-readable error codes in addition to human-readable error
      messages.
- [ ] Add rate and queue limits to prevent accidental large print runs.

## User experience

- [ ] Build a small optional web interface for printer setup, label previews, and
      queue monitoring.
- [ ] Add import and export for printer configuration with secrets and private
      addresses excluded by default.
- [ ] Provide ready-to-use example clients for Python, PowerShell, and JavaScript.
- [ ] Add example Home Assistant, Node-RED, or similar local-automation
      integrations.

## Reliability and maintainability

- [ ] Remove the remaining duplication between application tape configuration
      and the low-level raster protocol tables.
- [ ] Add golden-image tests for label layouts as well as golden-byte tests for
      raster commands.
- [ ] Add malformed-input and fuzz tests for the raster decoder.
- [ ] Add network failure tests for timeouts, partial writes, disconnects, and
      unavailable printers.
- [ ] Expand continuous integration across supported Python versions and Windows
      and Linux environments.
- [ ] Add structured logging, request IDs, and optional metrics for queue depth,
      failures, and print duration.
- [ ] Define a stable public Python API for `rasterprynt-ext` and publish it as a
      separately versioned package if there is maintainer demand.
- [ ] Add release automation, a changelog, and documented versioning policy.

## Documentation and community

- [ ] Add issue templates for bugs, hardware compatibility reports, and feature
      requests.
- [ ] Add a pull-request template with hardware-test and privacy checklists.
- [ ] Document the known subset of the Brother raster protocol, citing public
      sources and clearly identifying reverse-engineered behavior.
- [ ] Add a troubleshooting guide for connectivity, alignment, cutting, fonts,
      Docker networking, and SNMP.
- [ ] Add architecture and data-flow documentation for new contributors.

## Contribution guidance

Before starting a larger item, open an issue describing the proposed scope.
Changes that affect raster bytes, tape geometry, cutting, or device control
should include automated fixtures and clearly state what was tested on physical
hardware. Never include real printer addresses, SNMP communities, proprietary
label contents, or packet captures containing private data.
