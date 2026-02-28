from __future__ import annotations

from .base import LldpCollector
from .payload import PayloadCollector
from .snmp import SnmpLldpCollector
from .ssh import SshLldpCollector

COLLECTORS: dict[str, LldpCollector] = {
    "payload": PayloadCollector(),
    "snmp": SnmpLldpCollector(),
    "ssh": SshLldpCollector(),
}
