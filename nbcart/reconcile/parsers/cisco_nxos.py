from __future__ import annotations

import json

from nbcart.reconcile.models import LinkRecord
from nbcart.reconcile.normalize import normalize_link


def parse_cisco_nxos(seed_device: str, stdout: str) -> list[LinkRecord]:
    text = stdout.strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []

    rows = []
    if isinstance(payload, dict):
        table = payload.get("TABLE_nbor")
        if isinstance(table, dict):
            row = table.get("ROW_nbor")
            if isinstance(row, list):
                rows.extend([item for item in row if isinstance(item, dict)])
            elif isinstance(row, dict):
                rows.append(row)

    links: list[LinkRecord] = []
    for item in rows:
        local_interface = (
            str(item.get("l_port_id", "")).strip() or str(item.get("local_port_id", "")).strip()
        )
        remote_device = (
            str(item.get("sys_name", "")).strip() or str(item.get("device_id", "")).strip()
        )
        remote_interface = (
            str(item.get("port_id", "")).strip() or str(item.get("remote_port_id", "")).strip()
        )
        if not all((local_interface, remote_device, remote_interface)):
            continue
        links.append(normalize_link(seed_device, local_interface, remote_device, remote_interface))

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
