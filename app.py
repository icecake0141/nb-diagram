from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
import sqlite3
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence
from xml.sax.saxutils import escape

from flask import Flask, abort, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MiB upload limit

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"
DB_PATH = DATA_DIR / "results.db"


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


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def detect_encoding(file_bytes: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            file_bytes.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "utf-8"


def find_column(headers: Sequence[str], patterns: Sequence[str]) -> str | None:
    normalized = {h: normalize(h) for h in headers}
    for pattern in patterns:
        regex = re.compile(pattern)
        for original, norm in normalized.items():
            if regex.search(norm):
                return original
    return None


def choose_columns(headers: Sequence[str]) -> dict[str, str | None]:
    return {
        "a_device": find_column(
            headers, [r"terminationa.*device", r"sidea.*device", r"devicea", r"adevice"]
        ),
        "a_port": find_column(
            headers,
            [r"terminationa.*(name|port)", r"^terminationa$", r"interfacea", r"porta", r"aname"],
        ),
        "a_type": find_column(
            headers, [r"terminationa.*type", r"sidea.*type", r"^atype$", r"endpa.*type"]
        ),
        "b_device": find_column(
            headers, [r"terminationb.*device", r"sideb.*device", r"deviceb", r"bdevice"]
        ),
        "b_port": find_column(
            headers,
            [r"terminationb.*(name|port)", r"^terminationb$", r"interfaceb", r"portb", r"bname"],
        ),
        "b_type": find_column(
            headers, [r"terminationb.*type", r"sideb.*type", r"^btype$", r"endpb.*type"]
        ),
        "cable_id": find_column(headers, [r"^id$", r"cable.*id", r"^pk$", r"objectid"]),
        "cable_label": find_column(headers, [r"^label$", r"cable.*label", r"^name$"]),
        "cable_type": find_column(headers, [r"^type$", r"cable.*type", r"mediatype"]),
        "cable_color": find_column(headers, [r"^color$", r"cable.*color"]),
    }


def build_endpoint(device: str, port: str) -> str:
    device = (device or "").strip()
    port = (port or "").strip()
    if device and port:
        return f"{device}:{port}"
    if device:
        return device
    return port


def infer_device_interface(device: str, termination: str, side: str) -> tuple[str, str]:
    dev = (device or "").strip()
    term = (termination or "").strip()
    if dev and term:
        return dev, term
    if dev and not term:
        return dev, "(no-interface)"
    if term:
        m = re.match(r"^\s*([^:]+)\s*:\s*(.+)\s*$", term)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return f"Unassigned-{side}", term
    return f"Unknown-{side}", "(unknown-interface)"


def normalize_endpoint_type(endpoint_type: str) -> str:
    return normalize(endpoint_type)


def classify_endpoint_kind(endpoint_type: str) -> str:
    t = normalize_endpoint_type(endpoint_type)
    if "frontport" in t:
        return "front_port"
    if "rearport" in t:
        return "rear_port"
    if "circuittermination" in t:
        return "circuit_termination"
    if "powerport" in t:
        return "power_port"
    if "poweroutlet" in t:
        return "power_outlet"
    if "powerfeed" in t:
        return "power_feed"
    return "interface"


def infer_domain(a_kind: str, b_kind: str) -> str:
    kinds = {a_kind, b_kind}
    if any(k in kinds for k in {"power_port", "power_outlet", "power_feed"}):
        return "power"
    if "circuit_termination" in kinds:
        return "circuit"
    if any(k in kinds for k in {"front_port", "rear_port"}):
        return "pass_through"
    return "data"


def node_id(kind: str, endpoint: str) -> str:
    return f"{kind}|{endpoint}"


TYPE_PALETTE = [
    "#0f766e",
    "#2563eb",
    "#7c3aed",
    "#be123c",
    "#ea580c",
    "#0891b2",
    "#4d7c0f",
    "#334155",
]


def init_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    RESULT_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                upload_path TEXT NOT NULL,
                graph_path TEXT NOT NULL,
                rows_path TEXT NOT NULL,
                node_count INTEGER NOT NULL,
                edge_count INTEGER NOT NULL,
                columns_json TEXT NOT NULL,
                type_legend_json TEXT NOT NULL
            )
            """
        )
        con.commit()


def stable_type_color(cable_type: str) -> str:
    n = sum(ord(ch) for ch in cable_type)
    return TYPE_PALETTE[n % len(TYPE_PALETTE)]


def normalize_color(color: str | None, cable_type: str) -> str:
    value = (color or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.lower()
    return stable_type_color(cable_type)


def parse_cables_csv(file_bytes: bytes) -> tuple[list[CableRow], dict[str, str | None]]:
    enc = detect_encoding(file_bytes)
    text = file_bytes.decode(enc)
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    if not headers:
        raise ValueError("CSV header is missing.")

    columns = choose_columns(headers)
    if all(columns.get(name) is None for name in ("a_device", "a_port", "b_device", "b_port")):
        return [], columns
    rows: list[CableRow] = []

    for idx, row in enumerate(reader, start=1):
        raw_a_device = row.get(columns["a_device"] or "", "") if columns["a_device"] else ""
        raw_a_port = row.get(columns["a_port"] or "", "") if columns["a_port"] else ""
        raw_b_device = row.get(columns["b_device"] or "", "") if columns["b_device"] else ""
        raw_b_port = row.get(columns["b_port"] or "", "") if columns["b_port"] else ""

        a_device, a_port = infer_device_interface(raw_a_device, raw_a_port, "A")
        b_device, b_port = infer_device_interface(raw_b_device, raw_b_port, "B")
        a_type = (row.get(columns["a_type"] or "", "") or "").strip() if columns["a_type"] else ""
        b_type = (row.get(columns["b_type"] or "", "") or "").strip() if columns["b_type"] else ""

        a_endpoint = build_endpoint(a_device, a_port)
        b_endpoint = build_endpoint(b_device, b_port)
        if not a_endpoint and not b_endpoint:
            continue

        cable_label = ""
        if columns["cable_label"]:
            cable_label = (row.get(columns["cable_label"] or "", "") or "").strip()
        if not cable_label and columns["cable_id"]:
            cable_label = f"Cable-{(row.get(columns['cable_id'] or '', '') or '').strip() or idx}"
        if not cable_label:
            cable_label = f"Cable-{idx}"

        cable_type = "Unknown"
        if columns["cable_type"]:
            cable_type = (row.get(columns["cable_type"] or "", "") or "").strip() or "Unknown"

        raw_color = ""
        if columns["cable_color"]:
            raw_color = (row.get(columns["cable_color"] or "", "") or "").strip()

        cable_color = normalize_color(raw_color, cable_type)
        edge_label = f"{cable_label} [{cable_type}]"
        a_kind = classify_endpoint_kind(a_type)
        b_kind = classify_endpoint_kind(b_type)
        domain = infer_domain(a_kind, b_kind)
        rack_a = (row.get("Rack A", "") or "").strip()
        rack_b = (row.get("Rack B", "") or "").strip()
        location_a = (row.get("Location A", "") or "").strip()
        location_b = (row.get("Location B", "") or "").strip()

        rows.append(
            CableRow(
                a_device=a_device,
                a_interface=a_port,
                b_device=b_device,
                b_interface=b_port,
                a_endpoint=a_endpoint or f"Unknown-A-{idx}",
                b_endpoint=b_endpoint or f"Unknown-B-{idx}",
                a_type=a_type or "Unknown",
                b_type=b_type or "Unknown",
                a_kind=a_kind,
                b_kind=b_kind,
                cable_label=cable_label,
                cable_type=cable_type,
                cable_color=cable_color,
                domain=domain,
                edge_label=edge_label,
                rack_a=rack_a,
                rack_b=rack_b,
                location_a=location_a,
                location_b=location_b,
                raw=row,
            )
        )

    return rows, columns


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

        dev_x, dev_y = sorted((dev_a, dev_b))
        key = (dev_x, dev_y)
        pair_counter[key] = pair_counter.get(key, 0) + 1
        if key not in pair_types:
            pair_types[key] = Counter()
        pair_types[key][row.cable_type] += 1
        if key not in pair_colors:
            pair_colors[key] = Counter()
        pair_colors[key][row.cable_color] += 1
        if key not in pair_domains:
            pair_domains[key] = Counter()
        pair_domains[key][row.domain] += 1

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
        top_color = (
            pair_colors[pair].most_common(1)[0][0]
            if pair in pair_colors and pair_colors[pair]
            else "#64748b"
        )
        top_domain = (
            pair_domains[pair].most_common(1)[0][0]
            if pair in pair_domains and pair_domains[pair]
            else "data"
        )
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


def store_result(
    *,
    original_filename: str,
    file_bytes: bytes,
    rows: list[CableRow],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    columns: dict[str, str | None],
    type_legend: list[dict[str, Any]],
) -> int:
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    safe_name = secure_filename(original_filename) or "upload.csv"
    upload_rel = Path("uploads") / f"{stamp}_{suffix}_{safe_name}"
    graph_rel = Path("results") / f"{stamp}_{suffix}_graph.json"
    rows_rel = Path("results") / f"{stamp}_{suffix}_rows.json"

    (DATA_DIR / upload_rel).write_bytes(file_bytes)
    (DATA_DIR / graph_rel).write_text(
        json.dumps(nodes + edges, ensure_ascii=False), encoding="utf-8"
    )
    (DATA_DIR / rows_rel).write_text(
        json.dumps([asdict(r) for r in rows], ensure_ascii=False), encoding="utf-8"
    )

    created_at = dt.datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            """
            INSERT INTO results (
                created_at, original_filename, upload_path, graph_path, rows_path,
                node_count, edge_count, columns_json, type_legend_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                original_filename,
                str(upload_rel),
                str(graph_rel),
                str(rows_rel),
                len(nodes),
                len(edges),
                json.dumps(columns, ensure_ascii=False),
                json.dumps(type_legend, ensure_ascii=False),
            ),
        )
        con.commit()
        row_id = cur.lastrowid
        if row_id is None:
            raise RuntimeError("Failed to persist result row.")
        return int(row_id)


def list_racks(rows: list[CableRow]) -> list[str]:
    racks = {(r.rack_a or "").strip() for r in rows} | {(r.rack_b or "").strip() for r in rows}
    racks = {r for r in racks if r}
    return sorted(racks)


def list_recent_results(limit: int = 20) -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT id, created_at, original_filename, node_count, edge_count
            FROM results
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_result(result_id: int) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM results WHERE id = ?", (result_id,)).fetchone()
    return dict(row) if row else None


def resolve_data_path(rel_path: str) -> Path:
    path = (DATA_DIR / rel_path).resolve()
    if DATA_DIR.resolve() not in path.parents and path != DATA_DIR.resolve():
        raise ValueError("Invalid path.")
    return path


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
    # Draw.io output targets the same "device summary" view as the app.
    # Rack group helper nodes are omitted as regular vertices and represented by layout lanes.
    device_nodes = [
        el
        for el in node_elements
        if str(el.get("data", {}).get("node_type", "")).strip().lower() != "rack"
    ]

    # Build degree map to infer roles for unknown nodes, mirroring frontend heuristics.
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
        f'  <diagram id="{uuid.uuid4().hex[:10]}" name="{escape(diagram_name)}">',
        (
            '    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            'pageWidth="1920" pageHeight="1080">'
        ),
        "      <root>",
        '        <mxCell id="0"/>',
        '        <mxCell id="1" parent="0"/>',
    ]

    # Rack header cells to make rack lanes visible in draw.io.
    for ridx, rack in enumerate(rack_names, start=1):
        rack_draw_id = f"rack{ridx}"
        center_x = start_x + (ridx - 1) * (rack_width + rack_gap) + rack_width / 2
        xml_parts.append(
            f'        <mxCell id="{rack_draw_id}" value="{escape(rack)}" '
            'style="rounded=1;whiteSpace=wrap;html=1;fillColor=#0f766e;strokeColor=#0b5f59;'
            'fontColor=#ffffff;fontStyle=1;align=center;verticalAlign=middle;strokeWidth=2;" '
            'vertex="1" parent="1">'
        )
        xml_parts.append(
            f'          <mxGeometry x="{int(center_x - 72)}" y="30" width="144" '
            'height="48" as="geometry"/>'
        )
        xml_parts.append("        </mxCell>")

    # Place device nodes by rack + role, similar to the app's readable hierarchical layout.
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
            f'        <mxCell id="{draw_id}" value="{escape(value)}" '
            f'style="{drawio_node_style(role)}" vertex="1" parent="1">'
        )
        xml_parts.append(
            f'          <mxGeometry x="{x}" y="{y}" width="{node_w}" '
            f'height="{node_h}" as="geometry"/>'
        )
        xml_parts.append("        </mxCell>")

    for idx, el in enumerate(edge_elements, start=1):
        data = el.get("data", {})
        src_id = node_id_map.get(str(data.get("source", "")))
        dst_id = node_id_map.get(str(data.get("target", "")))
        if not src_id or not dst_id:
            continue
        draw_id = f"e{idx}"
        label = str(data.get("label", ""))
        color = str(data.get("color", "#475569"))
        domain = str(data.get("domain", "data"))
        src_x = src_y = dst_x = dst_y = None
        if src_id in node_geom_by_id and dst_id in node_geom_by_id:
            s_cx, s_cy, _, _ = node_geom_by_id[src_id]
            t_cx, t_cy, _, _ = node_geom_by_id[dst_id]
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
            f'        <mxCell id="{draw_id}" value="{escape(label)}" '
            f'style="{drawio_edge_style(domain, color)}{snap_ports}" edge="1" parent="1" '
            f'source="{src_id}" target="{dst_id}">'
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


@app.get("/")
def index() -> str:
    return render_template("index.html", recent_results=list_recent_results())


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(_: RequestEntityTooLarge):
    return (
        render_template(
            "index.html",
            error="Uploaded file is too large. Maximum size is 5 MiB.",
            recent_results=list_recent_results(),
        ),
        413,
    )


@app.post("/upload")
def upload() -> str:
    file = request.files.get("csv_file")
    if not file or not file.filename:
        return render_template(
            "index.html",
            error="Please select a CSV file.",
            recent_results=list_recent_results(),
        )

    file_bytes = file.read()

    try:
        rows, columns = parse_cables_csv(file_bytes)
    except Exception as exc:
        return render_template(
            "index.html",
            error=f"Failed to parse CSV: {exc}",
            recent_results=list_recent_results(),
        )

    if not rows:
        return render_template(
            "index.html",
            error="No connection data could be extracted. Please verify your column names.",
            recent_results=list_recent_results(),
        )

    nodes, edges = build_graph(rows)
    device_nodes, device_edges = build_device_graph(rows)
    missing = [
        name
        for name, col in columns.items()
        if col is None and name in {"a_device", "a_port", "b_device", "b_port"}
    ]
    type_counter = Counter(r.cable_type for r in rows)
    endpoint_kind_counter = Counter([r.a_kind for r in rows] + [r.b_kind for r in rows])
    legend_map: dict[str, str] = {}
    for r in rows:
        legend_map.setdefault(r.cable_type, r.cable_color)
    type_legend = [
        {"type": cable_type, "count": count, "color": legend_map.get(cable_type, "#64748b")}
        for cable_type, count in type_counter.most_common()
    ]
    kind_labels = {
        "interface": "Interface",
        "front_port": "FrontPort",
        "rear_port": "RearPort",
        "circuit_termination": "CircuitTermination",
        "power_port": "PowerPort",
        "power_outlet": "PowerOutlet",
        "power_feed": "PowerFeed",
    }
    node_legend = [
        {"kind": kind, "label": kind_labels.get(kind, kind), "count": count}
        for kind, count in endpoint_kind_counter.most_common()
    ]

    result_id = store_result(
        original_filename=file.filename,
        file_bytes=file_bytes,
        rows=rows,
        nodes=nodes,
        edges=edges,
        columns=columns,
        type_legend=type_legend,
    )

    return render_template(
        "index.html",
        graph_json=nodes + edges,
        device_graph_json=device_nodes + device_edges,
        rack_options=list_racks(rows),
        rows=rows,
        node_count=len(nodes),
        edge_count=len(edges),
        device_node_count=len(device_nodes),
        device_edge_count=len(device_edges),
        columns=columns,
        missing=missing,
        type_legend=type_legend,
        result_id=result_id,
        recent_results=list_recent_results(),
        node_legend=node_legend,
    )


@app.get("/result/<int:result_id>")
def result_detail(result_id: int) -> str:
    record = get_result(result_id)
    if not record:
        abort(404)

    graph_path = resolve_data_path(record["graph_path"])
    rows_path = resolve_data_path(record["rows_path"])
    if not graph_path.exists() or not rows_path.exists():
        abort(404)

    graph_json = json.loads(graph_path.read_text(encoding="utf-8"))
    row_items = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = [CableRow(**item) for item in row_items]
    device_nodes, device_edges = build_device_graph(rows)
    columns = json.loads(record["columns_json"])
    type_legend = json.loads(record["type_legend_json"])
    missing = [
        name
        for name, col in columns.items()
        if col is None and name in {"a_device", "a_port", "b_device", "b_port"}
    ]
    endpoint_kind_counter = Counter([r.a_kind for r in rows] + [r.b_kind for r in rows])
    kind_labels = {
        "interface": "Interface",
        "front_port": "FrontPort",
        "rear_port": "RearPort",
        "circuit_termination": "CircuitTermination",
        "power_port": "PowerPort",
        "power_outlet": "PowerOutlet",
        "power_feed": "PowerFeed",
    }
    node_legend = [
        {"kind": kind, "label": kind_labels.get(kind, kind), "count": count}
        for kind, count in endpoint_kind_counter.most_common()
    ]

    return render_template(
        "index.html",
        graph_json=graph_json,
        device_graph_json=device_nodes + device_edges,
        rack_options=list_racks(rows),
        rows=rows,
        node_count=record["node_count"],
        edge_count=record["edge_count"],
        device_node_count=len(device_nodes),
        device_edge_count=len(device_edges),
        columns=columns,
        missing=missing,
        type_legend=type_legend,
        node_legend=node_legend,
        result_id=result_id,
        recent_results=list_recent_results(),
    )


@app.get("/files/<int:result_id>/<kind>")
def download_file(result_id: int, kind: str):
    record = get_result(result_id)
    if not record:
        abort(404)

    if kind == "csv":
        path = resolve_data_path(record["upload_path"])
        download_name = record["original_filename"] or f"result-{result_id}.csv"
    elif kind == "graph":
        path = resolve_data_path(record["graph_path"])
        download_name = f"result-{result_id}-graph.json"
    elif kind == "drawio":
        rows_path = resolve_data_path(record["rows_path"])
        if not rows_path.exists():
            abort(404)
        row_items = json.loads(rows_path.read_text(encoding="utf-8"))
        rows = [CableRow(**item) for item in row_items]
        device_nodes, device_edges = build_device_graph(rows)
        drawio_xml = build_drawio_xml(
            device_nodes + device_edges, diagram_name=f"Result-{result_id}"
        )
        return send_file(
            io.BytesIO(drawio_xml.encode("utf-8")),
            as_attachment=True,
            download_name=f"result-{result_id}-diagram.drawio",
            mimetype="application/xml",
        )
    else:
        abort(404)

    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=download_name)


init_storage()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
