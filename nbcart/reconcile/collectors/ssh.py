from __future__ import annotations

import json
import re
import subprocess

from ..models import LinkRecord
from ..normalize import normalize_link

SSH_VENDOR_PROFILES: dict[str, dict[str, str]] = {
    "arista_eos": {"command": "show lldp neighbors detail | json"},
    "cisco_ios": {"command": "show lldp neighbors detail"},
    "cisco_nxos": {"command": "show lldp neighbors detail | json"},
    "juniper_junos": {"command": "show lldp neighbors detail | display json"},
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
    def _pick(item: dict[str, object], keys: list[str]) -> str:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    @staticmethod
    def _iter_dicts(value: object) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        if isinstance(value, dict):
            out.append(value)
            for child in value.values():
                out.extend(SshLldpCollector._iter_dicts(child))
        elif isinstance(value, list):
            for item in value:
                out.extend(SshLldpCollector._iter_dicts(item))
        return out

    @staticmethod
    def _profile_command(vendor: str) -> str:
        profile = SSH_VENDOR_PROFILES.get(vendor)
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
            local_interface = self._pick(
                item,
                ["local_interface", "local_if", "local_port", "port", "interface"],
            )
            remote_device = self._pick(
                item, ["remote_device", "neighbor", "system_name", "chassis"]
            )
            remote_interface = self._pick(
                item,
                ["remote_interface", "remote_if", "neighbor_port", "port_id"],
            )
            if not all((local_interface, remote_device, remote_interface)):
                continue
            links.append(
                normalize_link(seed_device, local_interface, remote_device, remote_interface)
            )
        return links

    @staticmethod
    def _parse_stdout_to_links(seed_device: str, stdout: str) -> list[LinkRecord]:
        text = stdout.strip()
        if not text:
            return []

        links: list[LinkRecord] = []
        try:
            payload = json.loads(text)
            for item in SshLldpCollector._iter_dicts(payload):
                local_interface = SshLldpCollector._pick(
                    item,
                    [
                        "local_interface",
                        "local_if",
                        "local_port",
                        "port",
                        "interface",
                        "port_description",
                    ],
                )
                remote_device = SshLldpCollector._pick(
                    item,
                    [
                        "remote_device",
                        "neighbor",
                        "system_name",
                        "chassis",
                        "device_id",
                    ],
                )
                remote_interface = SshLldpCollector._pick(
                    item,
                    [
                        "remote_interface",
                        "remote_if",
                        "neighbor_port",
                        "port_id",
                        "port_description",
                    ],
                )
                if not all((local_interface, remote_device, remote_interface)):
                    continue
                links.append(
                    normalize_link(seed_device, local_interface, remote_device, remote_interface)
                )
            if links:
                unique = list(
                    {
                        (
                            link.left.device,
                            link.left.interface,
                            link.right.device,
                            link.right.interface,
                        ): link
                        for link in links
                    }.values()
                )
                return unique
        except json.JSONDecodeError:
            pass

        block_local = ""
        block_remote_device = ""
        block_remote_port = ""
        kv_patterns = [
            (
                re.compile(r"^\s*(?:Local (?:Intf|Interface)|Interface)\s*:?\s*(.+?)\s*$", re.I),
                "local",
            ),
            (
                re.compile(r"^\s*(?:System Name|Device ID|Chassis id)\s*:?\s*(.+?)\s*$", re.I),
                "remote_device",
            ),
            (
                re.compile(r"^\s*(?:Port id|Port ID|Port Description)\s*:?\s*(.+?)\s*$", re.I),
                "remote_port",
            ),
        ]

        def flush_block() -> None:
            nonlocal block_local, block_remote_device, block_remote_port
            if block_local and block_remote_device and block_remote_port:
                links.append(
                    normalize_link(seed_device, block_local, block_remote_device, block_remote_port)
                )
            block_local = ""
            block_remote_device = ""
            block_remote_port = ""

        for line in text.splitlines():
            if not line.strip() or re.fullmatch(r"[-=]{3,}", line.strip()):
                flush_block()
                continue

            matched = False
            for regex, kind in kv_patterns:
                m = regex.match(line)
                if not m:
                    continue
                value = m.group(1).strip()
                if kind == "local":
                    block_local = value
                elif kind == "remote_device":
                    block_remote_device = value
                else:
                    block_remote_port = value
                matched = True
                break
            if matched:
                continue

            pipe_parts = [
                part.strip() for part in re.split(r"\s*\|\s*", line.strip()) if part.strip()
            ]
            if len(pipe_parts) >= 3:
                local_interface, remote_device, remote_interface = pipe_parts[:3]
                if all((local_interface, remote_device, remote_interface)):
                    links.append(
                        normalize_link(
                            seed_device, local_interface, remote_device, remote_interface
                        )
                    )
                    continue

            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 3:
                continue
            local_interface, remote_device, remote_interface = parts[:3]
            if not all((local_interface, remote_device, remote_interface)):
                continue
            links.append(
                normalize_link(seed_device, local_interface, remote_device, remote_interface)
            )
        flush_block()

        links = list(
            {
                (
                    link.left.device,
                    link.left.interface,
                    link.right.device,
                    link.right.interface,
                ): link
                for link in links
            }.values()
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
        vendor = str(params.get("vendor", "")).strip().lower()
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

        links = self._parse_stdout_to_links(seed_device, proc.stdout)
        if not links:
            raise ValueError("No LLDP neighbors parsed from ssh output.")
        return links
