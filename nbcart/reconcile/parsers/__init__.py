from __future__ import annotations

from collections.abc import Callable

from nbcart.reconcile.models import LinkRecord

from .arista_eos import parse_arista_eos
from .fortinet_fortiswitch_os import parse_fortinet_fortiswitch_os
from .generic import parse_generic

ParserFn = Callable[[str, str], list[LinkRecord]]

VENDOR_PARSERS: dict[str, ParserFn] = {
    "arista_eos": parse_arista_eos,
    "fortinet_fortiswitch_os": parse_fortinet_fortiswitch_os,
}

__all__ = ["ParserFn", "VENDOR_PARSERS", "parse_generic"]
