from fastapi import APIRouter, HTTPException

from api.schemas import (
    PrinterCreateRequest,
    PrinterModel,
    PrinterQueueStatusResponse,
    PrinterRebootRequest,
    PrinterRebootResponse,
    PrinterRecord,
    PrinterStatusRecord,
    PrinterUpdateRequest,
    PrintJobRecord,
    PrintRequest,
    QueuePrintRequest,
    QueuePrintResponse,
)
from core.label_generator import generate_label, get_font_check
from core.print_queue import get_printer_queue_manager
from core.printer_registry import get_printer_registry
from core.printer_status import (
    collect_network_status,
    reboot_printer,
    wait_until_reachable,
)
from core.printing import get_supported_tape_sizes, initialize_printer, print_labels

router = APIRouter()


@router.post("/printer/init")
def init_printer(ip: str, model: PrinterModel = "PT-P950NW"):
    """Initialize legacy single-printer target by IP."""
    initialize_printer(ip, model)
    return {"status": "initialized", "ip": ip, "model": model}


@router.post("/printers", response_model=PrinterRecord)
def create_printer(req: PrinterCreateRequest):
    """Create and persist a printer entry in the registry."""
    registry = get_printer_registry()
    try:
        return registry.create(req)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/printers", response_model=list[PrinterRecord])
def list_printers():
    """List all configured printers."""
    registry = get_printer_registry()
    return registry.list()


@router.get("/printers/status", response_model=list[PrinterStatusRecord])
def list_printer_status():
    """Return registration + live network status for all configured printers."""
    registry = get_printer_registry()
    status_records: list[PrinterStatusRecord] = []

    for printer in registry.list():
        network = collect_network_status(printer.ip)
        status_records.append(
            PrinterStatusRecord(
                printer_id=printer.printer_id,
                name=printer.name,
                ip=printer.ip,
                model=printer.model,
                tape_size_mm=printer.tape_size_mm,
                enabled=printer.enabled,
                registered=True,
                reachable=network.reachable,
                status=network.status,
                status_ok=network.status_ok,
                error=network.error,
            )
        )

    return status_records


@router.get("/printers/{printer_id}", response_model=PrinterRecord)
def get_printer(printer_id: str):
    """Return one printer by id."""
    registry = get_printer_registry()
    printer = registry.get(printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")
    return printer


@router.get("/printers/{printer_id}/status", response_model=PrinterStatusRecord)
def get_printer_status_endpoint(printer_id: str):
    """Return registration + live network status for one configured printer."""
    registry = get_printer_registry()
    printer = registry.get(printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    network = collect_network_status(printer.ip)
    return PrinterStatusRecord(
        printer_id=printer.printer_id,
        name=printer.name,
        ip=printer.ip,
        model=printer.model,
        tape_size_mm=printer.tape_size_mm,
        enabled=printer.enabled,
        registered=True,
        reachable=network.reachable,
        status=network.status,
        status_ok=network.status_ok,
        error=network.error,
    )


@router.post("/printers/{printer_id}/reboot", response_model=PrinterRebootResponse)
def reboot_printer_endpoint(printer_id: str, req: PrinterRebootRequest):
    """Trigger remote reboot via SNMP and optionally wait until printer is reachable again."""
    registry = get_printer_registry()
    printer = registry.get(printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    try:
        reboot_printer(printer.ip, community=req.community)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reboot printer: {exc}"
        ) from exc

    reachable_after_reboot = True
    if req.wait_until_online:
        reachable_after_reboot = wait_until_reachable(
            printer.ip,
            timeout_s=req.timeout_s,
            grace_s=req.grace_s,
        )

    return PrinterRebootResponse(
        status="reboot_requested",
        printer_id=printer.printer_id,
        ip=printer.ip,
        reachable_after_reboot=reachable_after_reboot,
        waited=req.wait_until_online,
    )


@router.patch("/printers/{printer_id}", response_model=PrinterRecord)
def update_printer(printer_id: str, req: PrinterUpdateRequest):
    """Update mutable printer fields such as name, IP, or enabled state."""
    registry = get_printer_registry()
    try:
        return registry.update(printer_id, req)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Printer '{printer_id}' not found"
        ) from exc


@router.delete("/printers/{printer_id}")
def delete_printer(printer_id: str):
    """Delete a printer from the registry."""
    registry = get_printer_registry()
    try:
        registry.delete(printer_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Printer '{printer_id}' not found"
        ) from exc
    return {"status": "deleted", "printer_id": printer_id}


@router.get("/printer/sizes")
def supported_sizes():
    """Return supported tape sizes for PT-P950NW."""
    return {"sizes": get_supported_tape_sizes()}


@router.get("/printer/font-check")
def font_check():
    """Return status of required bundled font for text label rendering."""
    info = get_font_check()
    status = "ok" if info["exists"] and info["loadable"] else "error"
    return {"status": status, **info}


@router.post("/printers/{printer_id}/print", response_model=QueuePrintResponse)
def queue_print_endpoint(printer_id: str, req: QueuePrintRequest):
    """Queue a print job for a specific printer id."""
    registry = get_printer_registry()
    queue_manager = get_printer_queue_manager()
    target_printer_id = printer_id

    if printer_id == "auto":
        candidates = [
            item
            for item in registry.list()
            if item.enabled and item.tape_size_mm == req.tape_size
        ]
        if not candidates:
            raise HTTPException(
                status_code=404,
                detail=f"No enabled printer configured for tape size {req.tape_size}mm",
            )
        selected = min(
            candidates,
            key=lambda item: (
                queue_manager.get_queue_size(item.printer_id),
                item.printer_id,
            ),
        )
        target_printer_id = selected.printer_id
    else:
        printer = registry.get(printer_id)
        if printer is None:
            raise HTTPException(
                status_code=404, detail=f"Printer '{printer_id}' not found"
            )
        if not printer.enabled:
            raise HTTPException(
                status_code=409, detail=f"Printer '{printer_id}' is disabled"
            )
        if printer.tape_size_mm is not None and printer.tape_size_mm != req.tape_size:
            matching_printers = [
                item.printer_id
                for item in registry.list()
                if item.enabled and item.tape_size_mm == req.tape_size
            ]
            suggestion = (
                f" Use one of: {', '.join(matching_printers)} or 'auto'."
                if matching_printers
                else " No enabled printer is configured for the requested tape size."
            )
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Tape size mismatch: printer '{printer_id}' is configured for "
                    f"{printer.tape_size_mm}mm, but request is {req.tape_size}mm.{suggestion}"
                ),
            )

    job, queue_size = queue_manager.enqueue(target_printer_id, req)

    return {
        "status": "queued",
        "job_id": job.job_id,
        "printer_id": target_printer_id,
        "queue_size": queue_size,
    }


@router.get("/print-jobs/{job_id}", response_model=PrintJobRecord)
def get_print_job(job_id: str):
    """Return current status for a previously queued print job."""
    queue_manager = get_printer_queue_manager()
    job = queue_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.get("/printers/{printer_id}/queue", response_model=PrinterQueueStatusResponse)
def get_printer_queue(printer_id: str):
    """Return active queue state for one printer."""
    registry = get_printer_registry()
    printer = registry.get(printer_id)
    if printer is None:
        raise HTTPException(status_code=404, detail=f"Printer '{printer_id}' not found")

    queue_manager = get_printer_queue_manager()
    jobs = queue_manager.get_printer_queue_jobs(printer_id)
    queue_size = queue_manager.get_queue_size(printer_id)

    return {
        "printer_id": printer_id,
        "queue_size": queue_size,
        "jobs": jobs,
    }


@router.post("/printer/print")
def print_endpoint(req: PrintRequest):
    """Print immediately through legacy single-printer flow."""
    labels = generate_label(
        text=req.text,
        label_type=req.label_type,
        tape_size=req.tape_size,
        copies=req.copies,
    )

    print_labels(labels, tape_mm=req.tape_size)

    return {
        "status": "printed",
        "count": len(labels),
        "label_type": req.label_type,
        "tape_size": req.tape_size,
    }
