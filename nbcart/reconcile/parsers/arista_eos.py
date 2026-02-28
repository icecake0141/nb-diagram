from __future__ import annotations

import json

from nbcart.reconcile.models import LinkRecord
from nbcart.reconcile.normalize import normalize_link


def parse_arista_eos(seed_device: str, stdout: str) -> list[LinkRecord]:
    text = stdout.strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []

    neighbors = payload.get("lldpNeighbors") if isinstance(payload, dict) else None
    if not isinstance(neighbors, list):
        return []

    links: list[LinkRecord] = []
    for item in neighbors:
        if not isinstance(item, dict):
            continue
        local_interface = (
            str(item.get("port", "")).strip() or str(item.get("localInterface", "")).strip()
        )
        remote_device = (
            str(item.get("neighborDevice", "")).strip()
            or str(item.get("systemName", "")).strip()
            or str(item.get("chassisId", "")).strip()
        )
        remote_interface = (
            str(item.get("neighborPort", "")).strip()
            or str(item.get("portId", "")).strip()
            or str(item.get("remoteInterface", "")).strip()
        )
        if not all((local_interface, remote_device, remote_interface)):
            continue
        links.append(
            normalize_link(seed_device, local_interface, remote_device, remote_interface)
        )

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
