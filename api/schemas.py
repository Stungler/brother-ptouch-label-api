from typing import Literal

from pydantic import BaseModel, Field

from core.label_generator import LabelType

PrinterModel = Literal["PT-P950NW"]
TapeWidthMm = Literal[6, 9, 12, 18, 24, 36]


class PrinterCreateRequest(BaseModel):
    printer_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    ip: str = Field(min_length=1)
    model: PrinterModel = "PT-P950NW"
    tape_size_mm: TapeWidthMm


class PrinterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    ip: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    tape_size_mm: TapeWidthMm | None = None


class PrinterRecord(BaseModel):
    printer_id: str
    name: str
    ip: str
    model: PrinterModel
    tape_size_mm: TapeWidthMm | None = None
    enabled: bool = True
    created_at: str
    updated_at: str


class PrintRequest(BaseModel):
    text: str = Field(min_length=1)
    label_type: LabelType
    tape_size: TapeWidthMm
    copies: int = Field(default=1, ge=1, le=100)


class QueuePrintRequest(BaseModel):
    text: str = Field(min_length=1)
    label_type: LabelType
    tape_size: TapeWidthMm
    copies: int = Field(default=1, ge=1, le=100)


class QueuePrintResponse(BaseModel):
    status: str
    job_id: str
    printer_id: str
    queue_size: int


JobStatus = Literal["queued", "running", "done", "failed"]


class PrintJobRecord(BaseModel):
    job_id: str
    printer_id: str
    status: JobStatus
    text: str
    label_type: LabelType
    tape_size: TapeWidthMm
    copies: int
    error: str | None = None
    created_at: str
    updated_at: str


class PrinterQueueStatusResponse(BaseModel):
    printer_id: str
    queue_size: int
    jobs: list[PrintJobRecord]


class PrinterStatusRecord(BaseModel):
    printer_id: str
    name: str
    ip: str
    model: PrinterModel
    tape_size_mm: TapeWidthMm | None = None
    enabled: bool
    registered: bool
    reachable: bool
    status: str | None = None
    status_ok: bool
    error: str | None = None


class PrinterRebootRequest(BaseModel):
    community: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "SNMP write community. When omitted, PRINTER_SNMP_WRITE_COMMUNITY is used."
        ),
    )
    wait_until_online: bool = True
    timeout_s: int = Field(default=120, ge=1, le=600)
    grace_s: int = Field(default=5, ge=0, le=60)


class PrinterRebootResponse(BaseModel):
    status: str
    printer_id: str
    ip: str
    reachable_after_reboot: bool
    waited: bool
