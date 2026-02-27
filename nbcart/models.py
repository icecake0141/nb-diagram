from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CableRow:
    a_device: str = ""
    a_interface: str = ""
    b_device: str = ""
    b_interface: str = ""
    a_endpoint: str = ""
    b_endpoint: str = ""
    a_type: str = "Unknown"
    b_type: str = "Unknown"
    a_kind: str = "interface"
    b_kind: str = "interface"
    cable_label: str = ""
    cable_type: str = "Unknown"
    cable_color: str = "#64748b"
    domain: str = "data"
    edge_label: str = ""
    rack_a: str = ""
    rack_b: str = ""
    location_a: str = ""
    location_b: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
