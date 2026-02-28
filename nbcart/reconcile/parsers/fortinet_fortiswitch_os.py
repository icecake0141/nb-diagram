from __future__ import annotations

import re

from nbcart.reconcile.models import LinkRecord
from nbcart.reconcile.normalize import normalize_link


def parse_fortinet_fortiswitch_os(seed_device: str, stdout: str) -> list[LinkRecord]:
    text = stdout.strip()
    if not text:
        return []

    links: list[LinkRecord] = []
    local_interface = ""
    remote_device = ""
    remote_interface = ""

    kv_patterns = [
        (
            re.compile(r"^\s*(?:Local (?:Interface|Port)|Interface)\s*:?\s*(.+?)\s*$", re.I),
            "local",
        ),
        (
            re.compile(r"^\s*(?:System Name|Remote Device|Neighbor)\s*:?\s*(.+?)\s*$", re.I),
            "remote_device",
        ),
        (
            re.compile(
                r"^\s*(?:Remote (?:Interface|Port)|Port id|Port ID)\s*:?\s*(.+?)\s*$",
                re.I,
            ),
            "remote_port",
        ),
    ]

    def flush_block() -> None:
        nonlocal local_interface, remote_device, remote_interface
        if local_interface and remote_device and remote_interface:
            links.append(
                normalize_link(seed_device, local_interface, remote_device, remote_interface)
            )
        local_interface = ""
        remote_device = ""
        remote_interface = ""

    for line in text.splitlines():
        line_s = line.strip()
        if not line_s or re.fullmatch(r"[-=]{3,}", line_s):
            flush_block()
            continue
        matched = False
        for pattern, kind in kv_patterns:
            m = pattern.match(line)
            if not m:
                continue
            value = m.group(1).strip()
            if kind == "local":
                local_interface = value
            elif kind == "remote_device":
                remote_device = value
            else:
                remote_interface = value
            matched = True
            break
        if matched:
            continue

    flush_block()
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
