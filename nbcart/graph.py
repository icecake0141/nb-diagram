from __future__ import annotations

from collections import Counter
from typing import Any

from .models import CableRow


def build_graph(rows: list[CableRow]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    device_ids: set[str] = set()
    interface_ids: set[str] = set()

    def device_id(device_name: str) -> str:
        return f"dev::{device_name}"

    def interface_id(device_name: str, interface_name: str) -> str:
        return f"if::{device_name}::{interface_name}"

    for i, row in enumerate(rows, start=1):
        for dev_name, if_name in ((row.a_device, row.a_interface), (row.b_device, row.b_interface)):
            dev_node_id = device_id(dev_name)
            if dev_node_id not in device_ids:
                device_ids.add(dev_node_id)
                nodes.append(
                    {
                        "data": {
                            "id": dev_node_id,
                            "label": dev_name,
                            "node_type": "device",
                        },
                        "classes": "device",
                    }
                )

            if_node_id = interface_id(dev_name, if_name)
            if if_node_id not in interface_ids:
                interface_ids.add(if_node_id)
                nodes.append(
                    {
                        "data": {
                            "id": if_node_id,
                            "parent": dev_node_id,
                            "label": if_name,
                            "node_type": "interface",
                        },
                        "classes": "interface",
                    }
                )

        edges.append(
            {
                "data": {
                    "id": f"e{i}",
                    "source": interface_id(row.a_device, row.a_interface),
                    "target": interface_id(row.b_device, row.b_interface),
                    "label": row.edge_label,
                    "cable_label": row.cable_label,
                    "cable_type": row.cable_type,
                    "color": row.cable_color,
                    "domain": row.domain,
                }
            }
        )

    return nodes, edges


def build_device_graph(rows: list[CableRow]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    device_nodes: set[str] = set()
    rack_by_device: dict[str, str] = {}
    endpoint_kinds_by_device: dict[str, Counter[str]] = {}
    pair_counter: dict[tuple[str, str], int] = {}
    pair_types: dict[tuple[str, str], Counter[str]] = {}
    pair_colors: dict[tuple[str, str], Counter[str]] = {}
    pair_domains: dict[tuple[str, str], Counter[str]] = {}

    def bump_kind(device: str, kind: str) -> None:
        if device not in endpoint_kinds_by_device:
            endpoint_kinds_by_device[device] = Counter()
        endpoint_kinds_by_device[device][kind] += 1

    def infer_role_hint(kind_counter: Counter[str]) -> str:
        if kind_counter.get("circuit_termination", 0) > 0:
            return "external"
        if kind_counter.get("front_port", 0) > 0 or kind_counter.get("rear_port", 0) > 0:
            return "patch_panel"
        if kind_counter.get("power_outlet", 0) > 0:
            return "pdu"
        if kind_counter.get("power_feed", 0) > 0:
            return "power_source"
        if kind_counter.get("power_port", 0) > 0:
            return "powered_device"
        return "unknown"

    for row in rows:
        dev_a = row.a_device
        dev_b = row.b_device
        if not dev_a or not dev_b:
            continue
        device_nodes.add(dev_a)
        device_nodes.add(dev_b)
        rack_by_device.setdefault(dev_a, row.rack_a.strip())
        rack_by_device.setdefault(dev_b, row.rack_b.strip())
        bump_kind(dev_a, row.a_kind)
        bump_kind(dev_b, row.b_kind)

        key = tuple(sorted((dev_a, dev_b)))
        pair_counter[key] = pair_counter.get(key, 0) + 1
        pair_types.setdefault(key, Counter())[row.cable_type] += 1
        pair_colors.setdefault(key, Counter())[row.cable_color] += 1
        pair_domains.setdefault(key, Counter())[row.domain] += 1

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    rack_nodes: set[str] = set()
    for dev in sorted(device_nodes):
        kind_counter = endpoint_kinds_by_device.get(dev, Counter())
        role_hint = infer_role_hint(kind_counter)
        rack_name = rack_by_device.get(dev, "") or "UNASSIGNED"
        rack_id = f"rack::{rack_name}"
        if rack_id not in rack_nodes:
            rack_nodes.add(rack_id)
            nodes.append(
                {
                    "data": {
                        "id": rack_id,
                        "label": rack_name,
                        "node_type": "rack",
                    },
                    "classes": "rack-group",
                }
            )
        nodes.append(
            {
                "data": {
                    "id": f"dev::{dev}",
                    "label": dev,
                    "node_type": "device",
                    "rack": rack_name,
                    "parent": rack_id,
                    "role_hint": role_hint,
                },
                "classes": "device-summary",
            }
        )

    for i, (pair, count) in enumerate(sorted(pair_counter.items()), start=1):
        a, b = pair
        top_type = pair_types[pair].most_common(1)[0][0] if pair_types[pair] else "Unknown"
        top_color = pair_colors[pair].most_common(1)[0][0] if pair_colors[pair] else "#64748b"
        top_domain = pair_domains[pair].most_common(1)[0][0] if pair_domains[pair] else "data"
        edges.append(
            {
                "data": {
                    "id": f"d{i}",
                    "source": f"dev::{a}",
                    "target": f"dev::{b}",
                    "label": f"{count} links ({top_type})",
                    "count": count,
                    "cable_type": top_type,
                    "color": top_color,
                    "domain": top_domain,
                }
            }
        )

    return nodes, edges


def list_racks(rows: list[CableRow]) -> list[str]:
    racks = {(r.rack_a or "").strip() for r in rows} | {(r.rack_b or "").strip() for r in rows}
    racks = {r for r in racks if r}
    return sorted(racks)
