from __future__ import annotations

import subprocess

from ..models import LinkRecord
from ..normalize import normalize_link
from ..parsers import VENDOR_PARSERS, parse_generic

SSH_VENDOR_PROFILES: dict[str, dict[str, str]] = {
    "arista_eos": {"command": "show lldp neighbors detail | json"},
    "cisco_ios": {"command": "show lldp neighbors detail"},
    "cisco_nxos": {"command": "show lldp neighbors detail | json"},
    "juniper_junos": {"command": "show lldp neighbors detail | display json"},
    "fortinet_fortiswitch_os": {"command": "get switch lldp neighbors detail"},
}

SSH_VENDOR_ALIASES = {
    "foritnet_fortiswitch_os": "fortinet_fortiswitch_os",
    "fortinet_fortiswitch": "fortinet_fortiswitch_os",
    "fortiswitch_os": "fortinet_fortiswitch_os",
}


class SshLldpCollector:
    @staticmethod
    def _int_param(params: dict[str, object], key: str, default: int) -> int:
        value = params.get(key, default)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                return default
        return default

    @staticmethod
    def _normalize_vendor(vendor: str) -> str:
        key = vendor.strip().lower()
        if not key:
            return ""
        return SSH_VENDOR_ALIASES.get(key, key)

    @staticmethod
    def _profile_command(vendor: str) -> str:
        normalized = SshLldpCollector._normalize_vendor(vendor)
        profile = SSH_VENDOR_PROFILES.get(normalized)
        if not profile:
            raise ValueError(f"Unsupported SSH vendor profile: {vendor}")
        return profile["command"]

    def _collect_from_neighbors_param(
        self,
        *,
        seed_device: str,
        params: dict[str, object],
    ) -> list[LinkRecord]:
        raw_neighbors = params.get("neighbors")
        if not isinstance(raw_neighbors, list):
            return []
        links: list[LinkRecord] = []
        for item in raw_neighbors:
            if not isinstance(item, dict):
                continue
            local_interface = ""
            for key in ["local_interface", "local_if", "local_port", "port", "interface"]:
                v = str(item.get(key, "")).strip()
                if v:
                    local_interface = v
                    break
            remote_device = ""
            for key in ["remote_device", "neighbor", "system_name", "chassis"]:
                v = str(item.get(key, "")).strip()
                if v:
                    remote_device = v
                    break
            remote_interface = ""
            for key in ["remote_interface", "remote_if", "neighbor_port", "port_id"]:
                v = str(item.get(key, "")).strip()
                if v:
                    remote_interface = v
                    break
            if not all((local_interface, remote_device, remote_interface)):
                continue
            links.append(
                normalize_link(seed_device, local_interface, remote_device, remote_interface)
            )
        return links

    def collect(self, *, seed_device: str, params: dict[str, object]) -> list[LinkRecord]:
        if not seed_device:
            raise ValueError("seed_device is required for ssh method.")

        from_param = self._collect_from_neighbors_param(seed_device=seed_device, params=params)
        if from_param:
            return from_param

        host = str(params.get("host", "")).strip()
        username = str(params.get("username", "")).strip()
        command = str(params.get("command", "")).strip()
        vendor = self._normalize_vendor(str(params.get("vendor", "")))
        timeout = self._int_param(params, "timeout", 10)

        if not host:
            raise ValueError("params.host is required for ssh method.")
        if not username:
            raise ValueError("params.username is required for ssh method.")
        if not command:
            if vendor:
                command = self._profile_command(vendor)
            else:
                raise ValueError("params.command or params.vendor is required for ssh method.")

        ssh_cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={timeout}",
            f"{username}@{host}",
            command,
        ]
        try:
            proc = subprocess.run(
                ssh_cmd,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise NotImplementedError("ssh command is not available.") from exc

        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or "ssh command failed"
            raise ValueError(detail)

        parser = VENDOR_PARSERS.get(vendor) if vendor else None
        links = parser(seed_device, proc.stdout) if parser else []
        if not links:
            links = parse_generic(seed_device, proc.stdout)
        if not links:
            raise ValueError("No LLDP neighbors parsed from ssh output.")
        return links
