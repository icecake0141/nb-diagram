from __future__ import annotations

from collections import defaultdict

from .models import DiffRecord, LinkRecord, ReconcileReport
from .normalize import link_key, pair_key


def _as_link_dict(link: LinkRecord) -> dict[str, str]:
    return {
        "left_device": link.left.device,
        "left_interface": link.left.interface,
        "right_device": link.right.device,
        "right_interface": link.right.interface,
    }


def reconcile(
    expected_links: list[LinkRecord],
    observed_links: list[LinkRecord],
) -> ReconcileReport:
    expected_map = {link_key(link): link for link in expected_links}
    observed_map = {link_key(link): link for link in observed_links}

    expected_keys = set(expected_map)
    observed_keys = set(observed_map)
    matched_keys = expected_keys & observed_keys

    expected_pairs: dict[str, set[str]] = defaultdict(set)
    observed_pairs: dict[str, set[str]] = defaultdict(set)
    for key, link in expected_map.items():
        expected_pairs[pair_key(link)].add(key)
    for key, link in observed_map.items():
        observed_pairs[pair_key(link)].add(key)

    missing_keys = set(expected_keys - observed_keys)
    unexpected_keys = set(observed_keys - expected_keys)
    mismatched: list[DiffRecord] = []
    common_pairs = set(expected_pairs) & set(observed_pairs)
    for key in sorted(common_pairs):
        if expected_pairs[key] == observed_pairs[key]:
            continue
        pair_missing = sorted(expected_pairs[key] & missing_keys)
        pair_unexpected = sorted(observed_pairs[key] & unexpected_keys)
        for diff_key in pair_missing:
            missing_keys.discard(diff_key)
        for diff_key in pair_unexpected:
            unexpected_keys.discard(diff_key)
        mismatched.append(
            DiffRecord(
                category="attribute_mismatch",
                key=key,
                expected={"links": ", ".join(pair_missing)},
                observed={"links": ", ".join(pair_unexpected)},
                reason="Device pair exists in both sources, but interface mapping differs.",
            )
        )

    missing = [
        DiffRecord(
            category="missing_in_observed",
            key=key,
            expected=_as_link_dict(expected_map[key]),
            reason="Expected link was not found in observed LLDP data.",
        )
        for key in sorted(missing_keys)
    ]
    unexpected = [
        DiffRecord(
            category="unexpected_in_observed",
            key=key,
            observed=_as_link_dict(observed_map[key]),
            reason="Observed LLDP link is not present in NetBox topology.",
        )
        for key in sorted(unexpected_keys)
    ]

    return ReconcileReport(
        expected_count=len(expected_links),
        observed_count=len(observed_links),
        matched_count=len(matched_keys),
        missing=missing,
        unexpected=unexpected,
        mismatched=mismatched,
    )
