from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PTP950NWConfig:
    """Tape and raster calibration values for the Brother PT-P950NW.

    Stripe heights must be multiples of eight because the raster transport
    serializes one byte for every eight print-head dots. Values for tape widths
    other than 6, 9, and 18 mm should be treated as starting points and
    calibrated against real hardware.
    """

    supported_tape_sizes_mm: tuple[int, ...] = (6, 9, 12, 18, 24, 36)

    stripe_height_px_by_tape: dict[int, int] = field(
        default_factory=lambda: {
            6: 328,
            9: 352,
            12: 368,
            18: 408,
            24: 456,
            36: 536,
        }
    )

    y_offset_px_by_tape: dict[int, int] = field(
        default_factory=lambda: {
            6: 7,
            9: 20,
            12: 20,
            18: 20,
            24: 35,
            36: 55,
        }
    )

    horizontal_padding_px_by_tape: dict[int, tuple[int, int]] = field(
        default_factory=lambda: {
            6: (18, 9),
            9: (28, 14),
            12: (36, 18),
            18: (48, 24),
            24: (60, 30),
            36: (84, 42),
        }
    )

    px_per_mm: int = 12

    def stripe_height(self, tape_mm: float) -> int:
        numeric_tape = float(tape_mm)
        if not numeric_tape.is_integer():
            raise ValueError(
                f"Tape width must be a whole number of millimeters: {tape_mm}"
            )
        tape = int(numeric_tape)
        if tape not in self.stripe_height_px_by_tape:
            supported = sorted(self.stripe_height_px_by_tape)
            raise ValueError(
                f"Unsupported tape width {tape_mm} mm. Supported widths: {supported}"
            )

        height = self.stripe_height_px_by_tape[tape]
        if height % 8 != 0:
            raise ValueError(
                f"Raster stripe height for {tape} mm must be a multiple of 8; "
                f"got {height}"
            )
        return height

    def y_offset_px(self, tape_mm: float) -> int:
        return self.y_offset_px_by_tape.get(int(tape_mm), 0)

    def horizontal_padding(self, tape_mm: float) -> tuple[int, int]:
        return self.horizontal_padding_px_by_tape.get(int(tape_mm), (0, 0))


PTP950NW = PTP950NWConfig()
