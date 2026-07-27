from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Event, Lock, Thread
from uuid import uuid4

from api.schemas import PrintJobRecord, QueuePrintRequest
from core.label_generator import LabelType, generate_label
from core.printer_registry import get_printer_registry
from core.printer_status import (
    collect_network_status,
    reboot_printer,
    wait_until_reachable,
)
from core.printing import print_labels_to_ip

ERROR_STATE_VALUE = "ERROR"
ERROR_REBOOT_WAIT_TIMEOUT_S = 120
ERROR_REBOOT_GRACE_S = 5


@dataclass(slots=True)
class PrintTask:
    """Work item consumed by a single printer worker thread."""

    job_id: str
    printer_id: str
    text: str
    label_type: LabelType
    tape_size: int
    copies: int


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PrinterQueueManager:
    """Manage per-printer queues and in-memory job lifecycle tracking."""

    def __init__(self) -> None:
        self._queues: dict[str, Queue[PrintTask]] = {}
        self._workers: dict[str, Thread] = {}
        self._jobs: dict[str, PrintJobRecord] = {}
        self._stop = Event()
        self._lock = Lock()

    def enqueue(
        self, printer_id: str, req: QueuePrintRequest
    ) -> tuple[PrintJobRecord, int]:
        """Enqueue a print request for a target printer and return job + queue size."""
        queue_ref = self._ensure_worker(printer_id)
        now = _utc_now_iso()
        job_id = str(uuid4())
        job = PrintJobRecord(
            job_id=job_id,
            printer_id=printer_id,
            status="queued",
            text=req.text,
            label_type=req.label_type,
            tape_size=req.tape_size,
            copies=req.copies,
            error=None,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job_id] = job

        task = PrintTask(
            job_id=job_id,
            printer_id=printer_id,
            text=req.text,
            label_type=req.label_type,
            tape_size=int(req.tape_size),
            copies=req.copies,
        )
        queue_ref.put(task)
        return job, queue_ref.qsize()

    def get_job(self, job_id: str) -> PrintJobRecord | None:
        """Return one tracked job by id, if present."""
        with self._lock:
            return self._jobs.get(job_id)

    def get_printer_queue_jobs(self, printer_id: str) -> list[PrintJobRecord]:
        """Return active jobs (queued/running) for one printer."""
        with self._lock:
            jobs = [
                job
                for job in self._jobs.values()
                if job.printer_id == printer_id and job.status in ("queued", "running")
            ]
            jobs.sort(key=lambda job: job.created_at)
            return jobs

    def get_queue_size(self, printer_id: str) -> int:
        """Return current pending queue size for a printer."""
        with self._lock:
            queue_ref = self._queues.get(printer_id)
            return queue_ref.qsize() if queue_ref else 0

    def stop(self) -> None:
        """Request worker shutdown and wait briefly for threads to stop."""
        self._stop.set()
        with self._lock:
            workers = list(self._workers.values())
        for worker in workers:
            worker.join(timeout=2.0)

    def _ensure_worker(self, printer_id: str) -> Queue[PrintTask]:
        """Create queue/worker lazily for a printer and return its queue."""
        with self._lock:
            if printer_id not in self._queues:
                self._queues[printer_id] = Queue()

            if (
                printer_id not in self._workers
                or not self._workers[printer_id].is_alive()
            ):
                worker = Thread(
                    target=self._worker_loop, args=(printer_id,), daemon=True
                )
                worker.start()
                self._workers[printer_id] = worker

            return self._queues[printer_id]

    def _worker_loop(self, printer_id: str) -> None:
        """Consume queued jobs for one printer in FIFO order."""
        queue_ref = self._queues[printer_id]
        registry = get_printer_registry()

        while not self._stop.is_set():
            try:
                task = queue_ref.get(timeout=0.5)
            except Empty:
                continue

            try:
                self._update_job(task.job_id, status="running", error=None)
                printer = registry.get(printer_id)
                if printer is None or not printer.enabled:
                    self._update_job(
                        task.job_id,
                        status="failed",
                        error="Printer not found or disabled",
                    )
                    continue

                self._recover_printer_if_error(printer.ip)

                labels = generate_label(
                    text=task.text,
                    label_type=task.label_type,
                    tape_size=task.tape_size,
                    copies=task.copies,
                )

                print_labels_to_ip(
                    labels=labels,
                    printer_ip=printer.ip,
                    tape_mm=task.tape_size,
                )
                self._update_job(task.job_id, status="done", error=None)
            # A failed job must not terminate the long-lived printer worker.
            except Exception as exc:  # noqa: BLE001
                self._update_job(task.job_id, status="failed", error=str(exc))
            finally:
                queue_ref.task_done()

    def _recover_printer_if_error(self, printer_ip: str) -> None:
        """Reboot printer and wait for recovery if live status reports ERROR."""
        network = collect_network_status(printer_ip)
        status_value = (network.status or "").strip().upper()

        if status_value != ERROR_STATE_VALUE:
            return

        reboot_printer(printer_ip)

        reachable = wait_until_reachable(
            printer_ip,
            timeout_s=ERROR_REBOOT_WAIT_TIMEOUT_S,
            grace_s=ERROR_REBOOT_GRACE_S,
        )
        if not reachable:
            raise RuntimeError(
                "Printer reboot triggered but device did not come back online in time"
            )

        post_recovery = collect_network_status(printer_ip)
        post_status = (post_recovery.status or "").strip().upper()
        if post_status == ERROR_STATE_VALUE:
            raise RuntimeError("Printer still reports ERROR after automatic reboot")

    def _update_job(self, job_id: str, status: str, error: str | None) -> None:
        """Update tracked job status and timestamp atomically."""
        with self._lock:
            current = self._jobs.get(job_id)
            if current is None:
                return
            payload = current.model_dump()
            payload["status"] = status
            payload["error"] = error
            payload["updated_at"] = _utc_now_iso()
            self._jobs[job_id] = PrintJobRecord(**payload)


_queue_manager: PrinterQueueManager | None = None


def init_printer_queue_manager() -> PrinterQueueManager:
    """Initialize global queue manager singleton."""
    global _queue_manager
    _queue_manager = PrinterQueueManager()
    return _queue_manager


def get_printer_queue_manager() -> PrinterQueueManager:
    """Return initialized global queue manager singleton."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = init_printer_queue_manager()
    return _queue_manager


def stop_printer_queue_manager() -> None:
    """Stop global queue manager workers if initialized."""
    global _queue_manager
    if _queue_manager is not None:
        _queue_manager.stop()
        _queue_manager = None
