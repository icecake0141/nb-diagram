from __future__ import annotations

import re
import uuid
from typing import Any
from xml.sax.saxutils import escape


def xml_attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


def drawio_node_style(role: str) -> str:
    base = (
        "rounded=1;whiteSpace=wrap;html=1;fontColor=#ffffff;"
        "align=center;verticalAlign=middle;strokeWidth=2;"
    )
    styles = {
        "core": "fillColor=#1d4ed8;strokeColor=#1e40af;",
        "leaf": "fillColor=#0f766e;strokeColor=#0b5f59;",
        "server": "fillColor=#475569;strokeColor=#334155;",
        "powered_device": "fillColor=#64748b;strokeColor=#475569;",
        "external": "shape=hexagon;fillColor=#1d4ed8;strokeColor=#1e3a8a;",
        "patch_panel": "fillColor=#a16207;strokeColor=#92400e;",
        "pdu": "fillColor=#ea580c;strokeColor=#c2410c;",
        "power_source": "shape=rhombus;fillColor=#dc2626;strokeColor=#991b1b;",
    }
    return base + styles.get(role, "fillColor=#0f766e;strokeColor=#0b5f59;")


def drawio_edge_style(domain: str, color: str) -> str:
    base = (
        "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
        "jettySize=auto;html=1;exitPerimeter=1;entryPerimeter=1;"
        "startArrow=none;endArrow=none;"
    )
    if domain == "power":
        return base + f"dashed=1;strokeWidth=2;strokeColor={color};"
    if domain == "circuit":
        return base + f"dashed=1;dashPattern=1 4;strokeWidth=3;strokeColor={color};"
    if domain == "pass_through":
        return base + f"strokeWidth=2.5;strokeColor={color};"
    return base + f"strokeWidth=2;strokeColor={color};"


def build_drawio_xml(elements: list[dict[str, Any]], diagram_name: str) -> str:
    node_elements = [el for el in elements if "source" not in el.get("data", {})]
    edge_elements = [el for el in elements if "source" in el.get("data", {})]
    device_nodes = [
        el
        for el in node_elements
        if str(el.get("data", {}).get("node_type", "")).strip().lower() != "rack"
    ]

    degree_by_id: dict[str, int] = {}
    for edge in edge_elements:
        data = edge.get("data", {})
        src = str(data.get("source", ""))
        dst = str(data.get("target", ""))
        if src:
            degree_by_id[src] = degree_by_id.get(src, 0) + 1
        if dst:
            degree_by_id[dst] = degree_by_id.get(dst, 0) + 1

    fixed_roles = {"external", "patch_panel", "pdu", "power_source", "powered_device"}
    inferred_role_by_id: dict[str, str] = {}
    unknown_ids: list[str] = []
    for el in device_nodes:
        data = el.get("data", {})
        node_id = str(data.get("id", ""))
        role_hint = str(data.get("role") or data.get("role_hint") or "").strip().lower()
        if role_hint in fixed_roles:
            inferred_role_by_id[node_id] = role_hint
        else:
            unknown_ids.append(node_id)

    unknown_degrees = sorted(degree_by_id.get(node_id, 0) for node_id in unknown_ids)

    def percentile(values: list[int], p: float) -> int:
        if not values:
            return 0
        idx = max(0, min(len(values) - 1, int((len(values) - 1) * p)))
        return values[idx]

    low_deg = max(1, percentile(unknown_degrees, 0.25))
    high_deg = max(low_deg + 1, percentile(unknown_degrees, 0.75))

    for el in device_nodes:
        data = el.get("data", {})
        node_id = str(data.get("id", ""))
        if node_id in inferred_role_by_id:
            continue
        label = str(data.get("label", "")).lower()
        deg = degree_by_id.get(node_id, 0)
        if re.search(r"(server|\-srv\d+|host|compute)", label):
            inferred_role_by_id[node_id] = "server"
        elif re.search(r"(spine|core)", label):
            inferred_role_by_id[node_id] = "core"
        elif re.search(r"(leaf|tor|edge)", label):
            inferred_role_by_id[node_id] = "leaf"
        elif deg <= low_deg:
            inferred_role_by_id[node_id] = "server"
        elif deg >= high_deg:
            inferred_role_by_id[node_id] = "core"
        else:
            inferred_role_by_id[node_id] = "leaf"

    role_order = [
        "external",
        "patch_panel",
        "core",
        "leaf",
        "power_source",
        "pdu",
        "powered_device",
        "server",
    ]
    y_map = {
        "external": 120,
        "patch_panel": 260,
        "core": 430,
        "leaf": 610,
        "power_source": 800,
        "pdu": 800,
        "powered_device": 980,
        "server": 980,
    }
    size_map: dict[str, tuple[int, int]] = {
        "external": (148, 64),
        "patch_panel": (148, 54),
        "core": (148, 54),
        "leaf": (148, 54),
        "power_source": (126, 56),
        "pdu": (120, 50),
        "powered_device": (118, 46),
        "server": (118, 46),
    }

    rack_names = sorted(
        {str(el.get("data", {}).get("rack", "")).strip() or "UNASSIGNED" for el in device_nodes}
    )
    if not rack_names:
        rack_names = ["UNASSIGNED"]
    rack_index_map = {name: idx for idx, name in enumerate(rack_names)}
    rack_gap = 560
    rack_width = 520
    start_x = 60

    node_id_map: dict[str, str] = {}
    node_geom_by_id: dict[str, tuple[float, float, int, int]] = {}
    xml_parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<mxfile host="app.diagrams.net">',
        f'  <diagram id="{uuid.uuid4().hex[:10]}" name="{xml_attr(diagram_name)}">',
        (
            '    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            'pageWidth="1920" pageHeight="1080">'
        ),
        "      <root>",
        '        <mxCell id="0"/>',
        '        <mxCell id="1" parent="0"/>',
    ]

    for ridx, rack in enumerate(rack_names, start=1):
        rack_draw_id = f"rack{ridx}"
        center_x = start_x + (ridx - 1) * (rack_width + rack_gap) + rack_width / 2
        xml_parts.append(
            f'        <mxCell id="{rack_draw_id}" value="{xml_attr(rack)}" '
            'style="rounded=1;whiteSpace=wrap;html=1;fillColor=#0f766e;strokeColor=#0b5f59;'
            'fontColor=#ffffff;fontStyle=1;align=center;verticalAlign=middle;strokeWidth=2;" '
            'vertex="1" parent="1">'
        )
        xml_parts.append(
            f'          <mxGeometry x="{int(center_x - 72)}" y="30" width="144" '
            'height="48" as="geometry"/>'
        )
        xml_parts.append("        </mxCell>")

    nodes_by_rack_role: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for el in device_nodes:
        data = el.get("data", {})
        rack_name = str(data.get("rack", "")).strip() or "UNASSIGNED"
        node_id = str(data.get("id", ""))
        role = inferred_role_by_id.get(node_id, "leaf")
        key = (rack_name, role)
        nodes_by_rack_role.setdefault(key, []).append(el)

    ordered_nodes: list[dict[str, Any]] = []
    for rack_name in rack_names:
        for role in role_order:
            group = nodes_by_rack_role.get((rack_name, role), [])
            group.sort(
                key=lambda n: (
                    -degree_by_id.get(str(n.get("data", {}).get("id", "")), 0),
                    str(n.get("data", {}).get("label", "")),
                )
            )
            ordered_nodes.extend(group)

    for idx, el in enumerate(ordered_nodes, start=1):
        data = el.get("data", {})
        source_id = str(data.get("id", f"node-{idx}"))
        draw_id = f"n{idx}"
        node_id_map[source_id] = draw_id
        role = inferred_role_by_id.get(source_id, "leaf")
        label = str(data.get("label", source_id))
        rack = str(data.get("rack", "")).strip()
        value = label if not rack else f"{label}\\n[{rack}]"
        rack_name = rack or "UNASSIGNED"
        rack_idx = rack_index_map.get(rack_name, 0)
        center_x = start_x + rack_idx * (rack_width + rack_gap) + rack_width / 2
        same_bucket = nodes_by_rack_role.get((rack_name, role), [])
        bucket_index = next(
            (
                i
                for i, n in enumerate(same_bucket)
                if str(n.get("data", {}).get("id", "")) == source_id
            ),
            0,
        )
        bucket_count = max(1, len(same_bucket))
        role_gap = 360 if role in {"server", "powered_device"} else 420
        start_bucket_x = center_x - ((bucket_count - 1) * role_gap) / 2
        x_center = start_bucket_x + bucket_index * role_gap
        node_w, node_h = size_map.get(role, (148, 54))
        x = int(x_center - node_w / 2)
        y = int(y_map.get(role, y_map["leaf"]) - node_h / 2)
        node_geom_by_id[draw_id] = (x_center, y + node_h / 2, node_w, node_h)
        xml_parts.append(
            f'        <mxCell id="{draw_id}" value="{xml_attr(value)}" '
            f'style="{drawio_node_style(role)}" vertex="1" parent="1">'
        )
        xml_parts.append(
            f'          <mxGeometry x="{x}" y="{y}" width="{node_w}" '
            f'height="{node_h}" as="geometry"/>'
        )
        xml_parts.append("        </mxCell>")

    for idx, el in enumerate(edge_elements, start=1):
        data = el.get("data", {})
        src = node_id_map.get(str(data.get("source", "")), "")
        dst = node_id_map.get(str(data.get("target", "")), "")
        if not src or not dst:
            continue
        draw_id = f"e{idx}"
        label = str(data.get("label", ""))
        color = str(data.get("color", "#475569"))
        domain = str(data.get("domain", "data"))
        src_x = src_y = dst_x = dst_y = None
        if src in node_geom_by_id and dst in node_geom_by_id:
            s_cx, s_cy, _, _ = node_geom_by_id[src]
            t_cx, t_cy, _, _ = node_geom_by_id[dst]
            if abs(t_cy - s_cy) >= abs(t_cx - s_cx):
                src_x = 0.5
                src_y = 1.0 if t_cy > s_cy else 0.0
                dst_x = 0.5
                dst_y = 0.0 if t_cy > s_cy else 1.0
            else:
                src_x = 1.0 if t_cx > s_cx else 0.0
                src_y = 0.5
                dst_x = 0.0 if t_cx > s_cx else 1.0
                dst_y = 0.5
        snap_ports = ""
        if src_x is not None and src_y is not None and dst_x is not None and dst_y is not None:
            snap_ports = (
                f"exitX={src_x};exitY={src_y};exitDx=0;exitDy=0;"
                f"entryX={dst_x};entryY={dst_y};entryDx=0;entryDy=0;"
            )
        xml_parts.append(
            f'        <mxCell id="{draw_id}" value="{xml_attr(label)}" '
            f'style="{drawio_edge_style(domain, color)}{snap_ports}" edge="1" parent="1" '
            f'source="{src}" target="{dst}">'
        )
        xml_parts.append('          <mxGeometry relative="1" as="geometry"/>')
        xml_parts.append("        </mxCell>")

    xml_parts.extend(
        [
            "      </root>",
            "    </mxGraphModel>",
            "  </diagram>",
            "</mxfile>",
        ]
    )
    return "\n".join(xml_parts)
