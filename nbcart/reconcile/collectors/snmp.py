from __future__ import annotations

import re
import subprocess

from ..models import LinkRecord
from ..normalize import normalize_link

LLDP_REM_SYSNAME_OID = ".1.0.8802.1.1.2.1.4.1.1.9"
LLDP_REM_PORTID_OID = ".1.0.8802.1.1.2.1.4.1.1.7"
LLDP_LOC_PORTDESC_OID = ".1.0.8802.1.1.2.1.3.7.1.4"


class SnmpLldpCollector:
    def _run_walk(
        self,
        *,
        host: str,
        community: str,
        oid: str,
        timeout: int,
        retries: int,
        port: int,
    ) -> str:
        cmd = [
            "snmpwalk",
            "-v2c",
            "-c",
            community,
            "-On",
            "-t",
            str(timeout),
            "-r",
            str(retries),
            f"{host}:{port}",
            oid,
        ]
        try:
            proc = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise NotImplementedError("snmpwalk command is not available.") from exc
        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or "snmpwalk failed"
            raise ValueError(detail)
        return proc.stdout

    @staticmethod
    def _extract_value(raw_value: str) -> str:
        value = raw_value.strip()
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1].strip()
        return value.strip()

    @staticmethod
    def _parse_walk_line(line: str) -> tuple[list[int], str] | None:
        m = re.match(r"^\s*([^\s=]+)\s*=\s*[^:]+:\s*(.*?)\s*$", line)
        if not m:
            return None
        oid, raw_value = m.groups()
        tail_match = re.search(r"(\d+(?:\.\d+)*)$", oid)
        if not tail_match:
            return None
        indices = [int(part) for part in tail_match.group(1).split(".")]
        return indices, SnmpLldpCollector._extract_value(raw_value)

    def collect(self, *, seed_device: str, params: dict[str, object]) -> list[LinkRecord]:
        host = str(params.get("host", "")).strip()
        community = str(params.get("community", "")).strip()
        timeout = int(params.get("timeout", 2))
        retries = int(params.get("retries", 1))
        port = int(params.get("port", 161))

        if not host:
            raise ValueError("params.host is required for snmp method.")
        if not community:
            raise ValueError("params.community is required for snmp method.")
        if not seed_device:
            raise ValueError("seed_device is required for snmp method.")

        sysname_out = self._run_walk(
            host=host,
            community=community,
            oid=LLDP_REM_SYSNAME_OID,
            timeout=timeout,
            retries=retries,
            port=port,
        )
        remote_port_out = self._run_walk(
            host=host,
            community=community,
            oid=LLDP_REM_PORTID_OID,
            timeout=timeout,
            retries=retries,
            port=port,
        )
        local_desc_out = self._run_walk(
            host=host,
            community=community,
            oid=LLDP_LOC_PORTDESC_OID,
            timeout=timeout,
            retries=retries,
            port=port,
        )

        remote_sys_by_key: dict[tuple[int, int], str] = {}
        remote_port_by_key: dict[tuple[int, int], str] = {}
        local_desc_by_port: dict[int, str] = {}

        for line in sysname_out.splitlines():
            parsed = self._parse_walk_line(line)
            if parsed is None:
                continue
            indices, value = parsed
            if len(indices) < 3 or not value:
                continue
            key = (indices[-2], indices[-1])
            remote_sys_by_key[key] = value

        for line in remote_port_out.splitlines():
            parsed = self._parse_walk_line(line)
            if parsed is None:
                continue
            indices, value = parsed
            if len(indices) < 3 or not value:
                continue
            key = (indices[-2], indices[-1])
            remote_port_by_key[key] = value

        for line in local_desc_out.splitlines():
            parsed = self._parse_walk_line(line)
            if parsed is None:
                continue
            indices, value = parsed
            if not indices or not value:
                continue
            local_desc_by_port[indices[-1]] = value

        links: list[LinkRecord] = []
        for key, remote_device in remote_sys_by_key.items():
            local_port_num, _remote_index = key
            remote_interface = remote_port_by_key.get(key, "(unknown-remote-port)")
            local_interface = local_desc_by_port.get(local_port_num, f"port-{local_port_num}")
            links.append(
                normalize_link(
                    seed_device,
                    local_interface,
                    remote_device,
                    remote_interface,
                )
            )
        return links
