from __future__ import annotations

import csv
import io
import re
from typing import Sequence

from .models import CableRow

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

MAPPING_KEYS = (
    "a_device",
    "a_port",
    "a_type",
    "b_device",
    "b_port",
    "b_type",
    "cable_id",
    "cable_label",
    "cable_type",
    "cable_color",
)


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


def sanitize_mapping(
    headers: Sequence[str],
    mapping: dict[str, str | None] | None,
) -> dict[str, str | None]:
    if mapping is None:
        return choose_columns(headers)

    header_set = set(headers)
    out: dict[str, str | None] = {k: None for k in MAPPING_KEYS}
    for key in MAPPING_KEYS:
        candidate = mapping.get(key)
        if candidate and candidate in header_set:
            out[key] = candidate
    return out


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


def stable_type_color(cable_type: str) -> str:
    n = sum(ord(ch) for ch in cable_type)
    return TYPE_PALETTE[n % len(TYPE_PALETTE)]


def normalize_color(color: str | None, cable_type: str) -> str:
    value = (color or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.lower()
    return stable_type_color(cable_type)


def parse_cables_csv(
    file_bytes: bytes,
    mapping: dict[str, str | None] | None = None,
) -> tuple[list[CableRow], dict[str, str | None]]:
    enc = detect_encoding(file_bytes)
    text = file_bytes.decode(enc)
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    if not headers:
        raise ValueError("CSV header is missing.")

    columns = sanitize_mapping(headers, mapping)
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
