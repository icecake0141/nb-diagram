from __future__ import annotations

import json
import re

from nbcart.reconcile.models import LinkRecord
from nbcart.reconcile.normalize import normalize_link


def _pick(item: dict[str, object], keys: list[str]) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _iter_dicts(value: object) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    if isinstance(value, dict):
        out.append(value)
        for child in value.values():
            out.extend(_iter_dicts(child))
    elif isinstance(value, list):
        for item in value:
            out.extend(_iter_dicts(item))
    return out


def _unique(links: list[LinkRecord]) -> list[LinkRecord]:
    return list(
        {
            (
                link.left.device,
                link.left.interface,
                link.right.device,
                link.right.interface,
            ): link
            for link in links
        }.values()
    )


def parse_generic(seed_device: str, stdout: str) -> list[LinkRecord]:
    text = stdout.strip()
    if not text:
        return []

    links: list[LinkRecord] = []
    try:
        payload = json.loads(text)
        for item in _iter_dicts(payload):
            local_interface = _pick(
                item,
                [
                    "local_interface",
                    "local_if",
                    "local_port",
                    "port",
                    "interface",
                    "port_description",
                ],
            )
            remote_device = _pick(
                item,
                [
                    "remote_device",
                    "neighbor",
                    "system_name",
                    "chassis",
                    "device_id",
                ],
            )
            remote_interface = _pick(
                item,
                [
                    "remote_interface",
                    "remote_if",
                    "neighbor_port",
                    "port_id",
                    "port_description",
                ],
            )
            if not all((local_interface, remote_device, remote_interface)):
                continue
            links.append(
                normalize_link(seed_device, local_interface, remote_device, remote_interface)
            )
        if links:
            return _unique(links)
    except json.JSONDecodeError:
        pass

    block_local = ""
    block_remote_device = ""
    block_remote_port = ""
    kv_patterns = [
        (
            re.compile(r"^\s*(?:Local (?:Intf|Interface)|Interface)\s*:?\s*(.+?)\s*$", re.I),
            "local",
        ),
        (
            re.compile(r"^\s*(?:System Name|Device ID|Chassis id)\s*:?\s*(.+?)\s*$", re.I),
            "remote_device",
        ),
        (
            re.compile(r"^\s*(?:Port id|Port ID|Port Description)\s*:?\s*(.+?)\s*$", re.I),
            "remote_port",
        ),
    ]

    def flush_block() -> None:
        nonlocal block_local, block_remote_device, block_remote_port
        if block_local and block_remote_device and block_remote_port:
            links.append(
                normalize_link(seed_device, block_local, block_remote_device, block_remote_port)
            )
        block_local = ""
        block_remote_device = ""
        block_remote_port = ""

    for line in text.splitlines():
        if not line.strip() or re.fullmatch(r"[-=]{3,}", line.strip()):
            flush_block()
            continue

        matched = False
        for regex, kind in kv_patterns:
            m = regex.match(line)
            if not m:
                continue
            value = m.group(1).strip()
            if kind == "local":
                block_local = value
            elif kind == "remote_device":
                block_remote_device = value
            else:
                block_remote_port = value
            matched = True
            break
        if matched:
            continue

        pipe_parts = [
            part.strip() for part in re.split(r"\s*\|\s*", line.strip()) if part.strip()
        ]
        if len(pipe_parts) >= 3:
            local_interface, remote_device, remote_interface = pipe_parts[:3]
            if all((local_interface, remote_device, remote_interface)):
                links.append(
                    normalize_link(seed_device, local_interface, remote_device, remote_interface)
                )
                continue

        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        local_interface, remote_device, remote_interface = parts[:3]
        if not all((local_interface, remote_device, remote_interface)):
            continue
        links.append(
            normalize_link(seed_device, local_interface, remote_device, remote_interface)
        )

    flush_block()
    return _unique(links)
