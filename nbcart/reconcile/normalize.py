from __future__ import annotations

import re

from .models import LinkEndpoint, LinkRecord


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", (value or "").strip().lower())


def normalize_endpoint(device: str, interface: str) -> LinkEndpoint:
    return LinkEndpoint(device=_normalize_text(device), interface=_normalize_text(interface))


def normalize_link(
    left_device: str,
    left_interface: str,
    right_device: str,
    right_interface: str,
) -> LinkRecord:
    left = normalize_endpoint(left_device, left_interface)
    right = normalize_endpoint(right_device, right_interface)
    if (left.device, left.interface) <= (right.device, right.interface):
        return LinkRecord(left=left, right=right)
    return LinkRecord(left=right, right=left)


def link_key(record: LinkRecord) -> str:
    return (
        f"{record.left.device}:{record.left.interface}"
        f"<->{record.right.device}:{record.right.interface}"
    )


def pair_key(record: LinkRecord) -> str:
    return f"{record.left.device}<->{record.right.device}"
