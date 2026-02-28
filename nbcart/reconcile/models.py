from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LinkEndpoint:
    device: str
    interface: str


@dataclass(frozen=True)
class LinkRecord:
    left: LinkEndpoint
    right: LinkEndpoint


@dataclass
class DiffRecord:
    category: str
    key: str
    expected: dict[str, str] | None = None
    observed: dict[str, str] | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class ReconcileReport:
    expected_count: int
    observed_count: int
    matched_count: int
    missing: list[DiffRecord]
    unexpected: list[DiffRecord]
    mismatched: list[DiffRecord]

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": {
                "expected_count": self.expected_count,
                "observed_count": self.observed_count,
                "matched_count": self.matched_count,
                "missing_count": len(self.missing),
                "unexpected_count": len(self.unexpected),
                "mismatched_count": len(self.mismatched),
            },
            "missing": [item.to_dict() for item in self.missing],
            "unexpected": [item.to_dict() for item in self.unexpected],
            "mismatched": [item.to_dict() for item in self.mismatched],
        }
