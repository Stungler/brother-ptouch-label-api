"""Decode Brother raster commands into a monochrome PBM image."""

from __future__ import annotations

import argparse
import io
import logging
import struct
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Literal

LOGGER = logging.getLogger(__name__)

MODE_ESCP = 0x00
MODE_RASTER = 0x01
MODE_PTOUCH = 0x02
COMPRESSION_RAW = 0
COMPRESSION_TIFF = 2

Pixel = tuple[int, int, int]
RasterRow = list[Pixel]
CaptureFormat = Literal["auto", "bin", "pcap"]

BLACK: Pixel = (0, 0, 0)
WHITE: Pixel = (255, 255, 255)


def _hex(data: bytes) -> str:
    return " ".join(f"{byte:02x}" for byte in data)


def decompress_packbits(data: bytes) -> Iterator[bytes]:
    """Yield chunks decoded from Brother's TIFF/PackBits row compression."""
    position = 0
    while position < len(data):
        marker = struct.unpack("!b", data[position : position + 1])[0]
        if marker < 0:
            if position + 1 >= len(data):
                raise ValueError("Truncated repeated PackBits run")
            count = -marker + 1
            yield data[position + 1 : position + 2] * count
            position += 2
        else:
            length = marker + 1
            end = position + 1 + length
            if end > len(data):
                raise ValueError("Truncated literal PackBits run")
            yield data[position + 1 : end]
            position = end


def _require(data: bytes, position: int, length: int) -> None:
    if position + length > len(data):
        raise ValueError(
            f"Truncated raster command at byte 0x{position:x}; needed {length} more byte(s)"
        )


def _decode_row(row_data: bytes) -> RasterRow:
    row: RasterRow = []
    for byte in row_data:
        for bit_index in range(8):
            is_black = (byte >> (7 - bit_index)) & 0x01
            row.append(BLACK if is_black else WHITE)
    return row


def decode_rows(commands: bytes) -> list[RasterRow]:
    """Decode a Brother command stream into equal-width monochrome rows."""
    position = 0
    while position < len(commands) and commands[position] == 0:
        position += 1
    if position == len(commands):
        raise ValueError("Command stream contains no raster data")

    mode = MODE_PTOUCH
    margin = 0
    compression_mode: int | None = None
    mirroring = False
    decoded_rows: list[RasterRow | None] = []

    while position < len(commands):
        current = commands[position]

        if mode == MODE_RASTER and current == ord("M"):
            _require(commands, position, 2)
            compression_mode = commands[position + 1]
            if compression_mode not in (COMPRESSION_RAW, COMPRESSION_TIFF):
                raise ValueError(f"Unsupported compression mode: {compression_mode}")
            position += 2
            continue

        if mode == MODE_RASTER and current == ord("Z"):
            decoded_rows.append(None)
            position += 1
            continue

        if mode == MODE_RASTER and current == ord("G"):
            _require(commands, position, 3)
            data_length = struct.unpack("<H", commands[position + 1 : position + 3])[0]
            position += 3
            _require(commands, position, data_length)
            row_data = commands[position : position + data_length]
            position += data_length

            if compression_mode == COMPRESSION_TIFF:
                row_data = b"".join(decompress_packbits(row_data))
            elif compression_mode != COMPRESSION_RAW:
                raise ValueError("Raster row encountered before compression mode")

            decoded_rows.append(_decode_row(row_data))
            continue

        if current == 0xFF or (mode == MODE_RASTER and current == 0x1A):
            position += 1
            continue

        if current in (0x0C, 0x0F):
            LOGGER.debug("Ignoring form feed at byte 0x%x", position)
            position += 1
            continue

        if current != 0x1B:
            raise ValueError(f"Expected ESC at byte 0x{position:x}; got 0x{current:02x}")

        _require(commands, position, 2)
        position += 1
        command = commands[position]

        if command == ord("@"):
            pass
        elif command == ord("i"):
            _require(commands, position, 2)
            position += 1
            subcommand = commands[position]

            if subcommand == ord("a"):
                _require(commands, position, 2)
                position += 1
                mode = commands[position]
                if mode not in (MODE_ESCP, MODE_RASTER, MODE_PTOUCH):
                    raise ValueError(f"Unsupported printer command mode: {mode}")
            elif subcommand == ord("c"):
                _require(commands, position, 6)
                LOGGER.debug("Skipping PT-9800PCN initialization")
                position += 5
            elif subcommand == ord("U"):
                _require(commands, position, 2)
                position += 1
                bus_command = commands[position]
                if bus_command == ord("B"):
                    _require(commands, position, 2)
                    position += 1
                elif mode == MODE_RASTER and bus_command == ord("J"):
                    _require(commands, position, 15)
                    position += 14
                else:
                    raise NotImplementedError(
                        f"Unsupported iU bus command 0x{bus_command:02x} in mode {mode}"
                    )
            elif mode == MODE_RASTER and subcommand == ord("z"):
                _require(commands, position, 11)
                LOGGER.debug(
                    "Print information: %s",
                    _hex(commands[position + 1 : position + 11]),
                )
                position += 10
            elif mode == MODE_RASTER and subcommand == ord("A"):
                _require(commands, position, 2)
                LOGGER.debug(
                    "Skipping iA arguments: %s",
                    _hex(commands[position + 1 : position + 2]),
                )
                position += 1
            elif mode == MODE_RASTER and subcommand == ord("k"):
                _require(commands, position, 4)
                LOGGER.debug(
                    "Skipping ik arguments: %s",
                    _hex(commands[position + 1 : position + 4]),
                )
                position += 3
            elif mode == MODE_RASTER and subcommand == ord("K"):
                _require(commands, position, 2)
                position += 1
            elif mode == MODE_RASTER and subcommand == ord("d"):
                _require(commands, position, 3)
                margin = struct.unpack(
                    "<H",
                    commands[position + 1 : position + 3],
                )[0]
                position += 2
            elif subcommand == ord("M"):
                _require(commands, position, 2)
                position += 1
                unsupported_bits = commands[position] & 0x9F
                if unsupported_bits:
                    raise NotImplementedError(
                        f"Unsupported mode-setting bits: 0x{commands[position]:02x}"
                    )
                mirroring = bool(commands[position] & 0x04)
            else:
                raise NotImplementedError(
                    f"Unsupported ESC i subcommand 0x{subcommand:02x} in mode {mode}"
                )
        else:
            raise NotImplementedError(f"Unsupported ESC command 0x{command:02x}")

        position += 1

    if not decoded_rows:
        raise ValueError("Command stream contains no raster rows")

    nonempty_rows = [row for row in decoded_rows if row is not None]
    if not nonempty_rows:
        raise ValueError("Command stream contains only empty raster rows")

    row_width = max(len(row) for row in nonempty_rows)
    padded_rows: list[RasterRow] = []
    for row in [None] * margin + decoded_rows + [None] * margin:
        if row is None:
            padded_rows.append([WHITE] * row_width)
        elif len(row) != row_width:
            raise ValueError("Raster rows have inconsistent widths")
        else:
            padded_rows.append(row)

    if not mirroring:
        for row in padded_rows:
            row.reverse()

    return padded_rows


def rows_to_pbm(rows: Sequence[Sequence[Pixel]]) -> bytes:
    """Encode monochrome rows as a portable bitmap (PBM/P1) image."""
    if not rows or not rows[0]:
        raise ValueError("At least one non-empty row is required")

    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("Rows must have equal widths")
    if any(pixel not in (BLACK, WHITE) for row in rows for pixel in row):
        raise ValueError("Rows must contain only black and white pixels")

    body = b"\n".join(b" ".join(b"1" if pixel == BLACK else b"0" for pixel in row) for row in rows)
    return b"P1\n" + f"{width} {len(rows)}\n".encode() + body


def detect_capture_format(data: bytes) -> Literal["bin", "pcap"]:
    """Detect classic PCAP data; all other input is treated as command bytes."""
    if data[:4] in (b"\xa1\xb2\xc3\xd4", b"\xd4\xc3\xb2\xa1"):
        return "pcap"
    return "bin"


def extract_pcap_payload(data: bytes) -> bytes:
    """Extract TCP/9100 payload bytes from a classic PCAP capture."""
    try:
        from scapy.all import TCP, rdpcap
    except ImportError as exc:
        raise RuntimeError(
            "PCAP decoding requires the optional 'pcap' dependency: "
            "pip install 'rasterprynt-ext[pcap]'"
        ) from exc

    packets = rdpcap(io.BytesIO(data))
    return b"".join(
        bytes(packet[TCP].payload)
        for packet in packets
        if TCP in packet and packet[TCP].dport == 9100
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rasterprynt-decode",
        description="Decode Brother raster commands into a PBM image.",
    )
    parser.add_argument("input", type=Path, help="Binary command stream or PCAP")
    parser.add_argument("output", type=Path, help="Destination PBM file")
    parser.add_argument(
        "--format",
        choices=("auto", "pcap", "bin"),
        default="auto",
        help="Input format (default: auto)",
    )
    parser.add_argument(
        "--write-bin",
        type=Path,
        metavar="FILE",
        help="Also write the extracted command stream",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    commands = args.input.read_bytes()

    input_format = detect_capture_format(commands) if args.format == "auto" else args.format
    if input_format == "pcap":
        commands = extract_pcap_payload(commands)

    if args.write_bin:
        args.write_bin.write_bytes(commands)

    rows = decode_rows(commands)
    args.output.write_bytes(rows_to_pbm(rows))
    print(f"Decoded {len(rows[0])} x {len(rows)} pixels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
