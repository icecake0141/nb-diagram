from __future__ import annotations

import json

from nbcart.reconcile.models import LinkRecord
from nbcart.reconcile.normalize import normalize_link


def _extract_data(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            extracted = _extract_data(item)
            if extracted:
                return extracted
        return ""
    if isinstance(value, dict):
        if "data" in value:
            return _extract_data(value["data"])
        for v in value.values():
            extracted = _extract_data(v)
            if extracted:
                return extracted
    return ""


def parse_juniper_junos(seed_device: str, stdout: str) -> list[LinkRecord]:
    text = stdout.strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []

    records: list[dict[str, object]] = []
    if isinstance(payload, dict):
        outer = payload.get("lldp-neighbors-information")
        if isinstance(outer, list):
            for item in outer:
                if not isinstance(item, dict):
                    continue
                inner = item.get("lldp-neighbor-information")
                if isinstance(inner, list):
                    records.extend([x for x in inner if isinstance(x, dict)])

    links: list[LinkRecord] = []
    for item in records:
        local_interface = _extract_data(item.get("lldp-local-port-id", ""))
        remote_device = _extract_data(item.get("lldp-remote-system-name", "")) or _extract_data(
            item.get("lldp-remote-chassis-id", "")
        )
        remote_interface = _extract_data(item.get("lldp-remote-port-id", ""))
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
