from __future__ import annotations

import json
import re
import subprocess

from ..models import LinkRecord
from ..normalize import normalize_link


class SshLldpCollector:
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

        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                payload = payload.get("neighbors", [])
            if isinstance(payload, list):
                links: list[LinkRecord] = []
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    local_interface = SshLldpCollector._pick(
                        item,
                        ["local_interface", "local_if", "local_port", "port", "interface"],
                    )
                    remote_device = SshLldpCollector._pick(
                        item,
                        ["remote_device", "neighbor", "system_name", "chassis"],
                    )
                    remote_interface = SshLldpCollector._pick(
                        item,
                        ["remote_interface", "remote_if", "neighbor_port", "port_id"],
                    )
                    if not all((local_interface, remote_device, remote_interface)):
                        continue
                    links.append(
                        normalize_link(
                            seed_device, local_interface, remote_device, remote_interface
                        )
                    )
                return links
        except json.JSONDecodeError:
            pass

        links = []
        for line in text.splitlines():
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
        timeout = int(params.get("timeout", 10))

        if not host:
            raise ValueError("params.host is required for ssh method.")
        if not username:
            raise ValueError("params.username is required for ssh method.")
        if not command:
            raise ValueError("params.command is required for ssh method.")

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
