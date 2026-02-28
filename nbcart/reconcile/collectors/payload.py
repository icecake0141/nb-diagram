from __future__ import annotations

from ..models import LinkRecord
from ..normalize import normalize_link


class PayloadCollector:
    """Collector used for API-driven ingestion of observed LLDP neighbors."""

    def collect(self, *, seed_device: str, params: dict[str, object]) -> list[LinkRecord]:
        _ = seed_device  # Seed device is unused for payload mode.
        raw_neighbors = params.get("neighbors")
        if not isinstance(raw_neighbors, list):
            raise ValueError("params.neighbors must be a list.")

        links: list[LinkRecord] = []
        for item in raw_neighbors:
            if not isinstance(item, dict):
                continue
            local_device = str(item.get("local_device", "")).strip()
            local_interface = str(item.get("local_interface", "")).strip()
            remote_device = str(item.get("remote_device", "")).strip()
            remote_interface = str(item.get("remote_interface", "")).strip()
            if not all((local_device, local_interface, remote_device, remote_interface)):
                continue
            links.append(
                normalize_link(
                    local_device,
                    local_interface,
                    remote_device,
                    remote_interface,
                )
            )
        return links
