from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass

PRINTER_STATUS_OID = "1.3.6.1.2.1.43.16.5.1.2.1.1"
PRINTER_REBOOT_OID = "1.3.6.1.4.1.1240.2.3.4.2.3.0"
PRINTER_REBOOT_VALUE = 21930
DEFAULT_SNMP_READ_COMMUNITY = "public"
DEFAULT_SNMP_WRITE_COMMUNITY = "private"


@dataclass(slots=True)
class PrinterNetworkStatus:
    reachable: bool
    status: str | None
    status_ok: bool
    error: str | None


def get_snmp_read_community() -> str:
    """Return the SNMP read community configured for this process."""
    return os.getenv("PRINTER_SNMP_READ_COMMUNITY", DEFAULT_SNMP_READ_COMMUNITY)


def get_snmp_write_community() -> str:
    """Return the SNMP write community configured for this process."""
    return os.getenv("PRINTER_SNMP_WRITE_COMMUNITY", DEFAULT_SNMP_WRITE_COMMUNITY)


def ping_host(ip: str, timeout_s: int = 1) -> bool:
    timeout_s = max(1, int(timeout_s))
    ping_exe = shutil.which("ping")
    if ping_exe:
        if os.name == "nt":
            cmd = [ping_exe, "-n", "1", "-w", str(timeout_s * 1000), ip]
        else:
            cmd = [ping_exe, "-c", "1", "-W", str(timeout_s), ip]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True

    return _tcp_probe(ip, timeout_s=timeout_s)


def _tcp_probe(ip: str, timeout_s: int = 1) -> bool:
    ports = (9100, 161, 80)
    for port in ports:
        try:
            with socket.create_connection((ip, port), timeout=max(1, int(timeout_s))):
                return True
        except OSError:
            continue
    return False


def _pretty_snmp_value(value: object) -> str:
    pretty = getattr(value, "prettyPrint", None)
    if callable(pretty):
        return pretty()
    return str(value)


def _legacy_snmp_get(
    ip: str, community: str, oid: str, timeout_s: int
) -> tuple[object, object, object, object]:
    from pysnmp.hlapi import (  # type: ignore[attr-defined]
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        getCmd,
    )

    return next(
        getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=0),
            UdpTransportTarget((ip, 161), timeout=max(1, int(timeout_s)), retries=0),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )
    )


def _legacy_snmp_set(
    ip: str,
    community: str,
    oid: str,
    integer_value: int,
    timeout_s: int,
) -> tuple[object, object, object, object]:
    from pysnmp.hlapi import (  # type: ignore[attr-defined]
        CommunityData,
        ContextData,
        Integer,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        setCmd,
    )

    return next(
        setCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=0),
            UdpTransportTarget((ip, 161), timeout=max(1, int(timeout_s)), retries=0),
            ContextData(),
            ObjectType(ObjectIdentity(oid), Integer(integer_value)),
        )
    )


async def _modern_snmp_get_async(
    ip: str,
    community: str,
    oid: str,
    timeout_s: int,
) -> tuple[object, object, object, object]:
    from pysnmp.hlapi.v1arch import (  # type: ignore[attr-defined]
        CommunityData,
        ObjectIdentity,
        ObjectType,
        SnmpDispatcher,
        UdpTransportTarget,
        get_cmd,
    )

    target = await UdpTransportTarget.create(
        (ip, 161),
        timeout=max(1, int(timeout_s)),
        retries=0,
    )
    return await get_cmd(
        SnmpDispatcher(),
        CommunityData(community, mpModel=0),
        target,
        ObjectType(ObjectIdentity(oid)),
    )


async def _modern_snmp_set_async(
    ip: str,
    community: str,
    oid: str,
    integer_value: int,
    timeout_s: int,
) -> tuple[object, object, object, object]:
    from pysnmp.hlapi.v1arch import (  # type: ignore[attr-defined]
        CommunityData,
        ObjectIdentity,
        ObjectType,
        SnmpDispatcher,
        UdpTransportTarget,
        set_cmd,
    )
    from pysnmp.proto.rfc1902 import Integer32

    target = await UdpTransportTarget.create(
        (ip, 161),
        timeout=max(1, int(timeout_s)),
        retries=0,
    )
    return await set_cmd(
        SnmpDispatcher(),
        CommunityData(community, mpModel=0),
        target,
        ObjectType(ObjectIdentity(oid), Integer32(integer_value)),
    )


def _snmp_get(
    ip: str, community: str, oid: str, timeout_s: int
) -> tuple[object, object, object, object]:
    try:
        return _legacy_snmp_get(
            ip=ip, community=community, oid=oid, timeout_s=timeout_s
        )
    except (ImportError, AttributeError):
        return asyncio.run(
            _modern_snmp_get_async(
                ip=ip, community=community, oid=oid, timeout_s=timeout_s
            )
        )


def _snmp_set(
    ip: str,
    community: str,
    oid: str,
    integer_value: int,
    timeout_s: int,
) -> tuple[object, object, object, object]:
    try:
        return _legacy_snmp_set(
            ip=ip,
            community=community,
            oid=oid,
            integer_value=integer_value,
            timeout_s=timeout_s,
        )
    except (ImportError, AttributeError):
        return asyncio.run(
            _modern_snmp_set_async(
                ip=ip,
                community=community,
                oid=oid,
                integer_value=integer_value,
                timeout_s=timeout_s,
            )
        )


def get_printer_status(
    ip: str,
    community: str | None = None,
    timeout_s: int = 2,
) -> str:
    community = community or get_snmp_read_community()
    error_indication, error_status, error_index, var_binds = _snmp_get(
        ip=ip,
        community=community,
        oid=PRINTER_STATUS_OID,
        timeout_s=timeout_s,
    )

    if error_indication:
        raise RuntimeError(str(error_indication))
    if error_status:
        idx = int(error_index) - 1 if error_index else 0
        oid = str(var_binds[idx][0]) if var_binds and idx >= 0 else PRINTER_STATUS_OID
        raise RuntimeError(f"SNMP error at {oid}: {_pretty_snmp_value(error_status)}")

    if not var_binds:
        raise RuntimeError("No SNMP response")

    value = _pretty_snmp_value(var_binds[0][1])
    return value.strip()


def reboot_printer(
    ip: str,
    community: str | None = None,
    timeout_s: int = 2,
) -> None:
    community = community or get_snmp_write_community()
    error_indication, error_status, error_index, var_binds = _snmp_set(
        ip=ip,
        community=community,
        oid=PRINTER_REBOOT_OID,
        integer_value=PRINTER_REBOOT_VALUE,
        timeout_s=timeout_s,
    )

    if error_indication:
        raise RuntimeError(str(error_indication))
    if error_status:
        idx = int(error_index) - 1 if error_index else 0
        oid = str(var_binds[idx][0]) if var_binds and idx >= 0 else PRINTER_REBOOT_OID
        raise RuntimeError(f"SNMP error at {oid}: {_pretty_snmp_value(error_status)}")


def wait_until_reachable(ip: str, timeout_s: int = 120, grace_s: int = 5) -> bool:
    deadline = time.monotonic() + max(1, int(timeout_s))
    while time.monotonic() < deadline:
        if ping_host(ip, timeout_s=1):
            if grace_s > 0:
                time.sleep(grace_s)
            return True
        time.sleep(1)
    return False


def collect_network_status(
    ip: str,
    status_community: str | None = None,
) -> PrinterNetworkStatus:
    reachable = ping_host(ip)
    if not reachable:
        return PrinterNetworkStatus(
            reachable=False,
            status=None,
            status_ok=False,
            error="Printer not reachable via ping",
        )

    try:
        status_value = get_printer_status(ip, community=status_community)
    # Status aggregation should report protocol/import failures, not raise them.
    except Exception as exc:  # noqa: BLE001
        return PrinterNetworkStatus(
            reachable=True,
            status=None,
            status_ok=False,
            error=f"SNMP status read failed: {exc}",
        )

    normalized = status_value.strip().upper()
    status_ok = normalized != "ERROR"
    return PrinterNetworkStatus(
        reachable=True,
        status=status_value,
        status_ok=status_ok,
        error=None,
    )
