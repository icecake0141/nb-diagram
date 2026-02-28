from __future__ import annotations

from typing import Protocol

from ..models import LinkRecord


class LldpCollector(Protocol):
    def collect(self, *, seed_device: str, params: dict[str, object]) -> list[LinkRecord]:
        """Collect observed links from network devices."""
