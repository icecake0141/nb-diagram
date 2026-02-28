from __future__ import annotations

from collections.abc import Callable

from nbcart.reconcile.models import LinkRecord

from .arista_eos import parse_arista_eos
from .cisco_ios import parse_cisco_ios
from .cisco_nxos import parse_cisco_nxos
from .fortinet_fortiswitch_os import parse_fortinet_fortiswitch_os
from .generic import parse_generic
from .juniper_junos import parse_juniper_junos

ParserFn = Callable[[str, str], list[LinkRecord]]

VENDOR_PARSERS: dict[str, ParserFn] = {
    "arista_eos": parse_arista_eos,
    "cisco_ios": parse_cisco_ios,
    "cisco_nxos": parse_cisco_nxos,
    "juniper_junos": parse_juniper_junos,
    "fortinet_fortiswitch_os": parse_fortinet_fortiswitch_os,
}

__all__ = ["ParserFn", "VENDOR_PARSERS", "parse_generic"]
