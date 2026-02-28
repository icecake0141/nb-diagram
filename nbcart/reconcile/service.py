from __future__ import annotations

from nbcart.models import CableRow

from .collectors import COLLECTORS
from .match import reconcile
from .models import LinkRecord, ReconcileReport
from .normalize import normalize_link


def expected_links_from_rows(rows: list[CableRow]) -> list[LinkRecord]:
    links = {
        normalize_link(row.a_device, row.a_interface, row.b_device, row.b_interface)
        for row in rows
        if row.a_device and row.a_interface and row.b_device and row.b_interface
    }
    return sorted(
        links,
        key=lambda item: (
            item.left.device,
            item.left.interface,
            item.right.device,
        ),
    )


def collect_observed_links(
    *,
    method: str,
    seed_device: str,
    params: dict[str, object],
) -> list[LinkRecord]:
    collector = COLLECTORS.get(method)
    if collector is None:
        raise ValueError(f"Unsupported method: {method}")
    return collector.collect(seed_device=seed_device, params=params)


def reconcile_links(
    *,
    rows: list[CableRow],
    method: str,
    seed_device: str,
    params: dict[str, object],
) -> ReconcileReport:
    expected = expected_links_from_rows(rows)
    observed = collect_observed_links(method=method, seed_device=seed_device, params=params)
    return reconcile(expected, observed)
