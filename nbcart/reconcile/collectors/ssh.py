from __future__ import annotations

import json
import subprocess

from ..models import LinkRecord
from ..normalize import normalize_link


class SshLldpCollector:
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
            local_interface = str(item.get("local_interface", "")).strip()
            remote_device = str(item.get("remote_device", "")).strip()
            remote_interface = str(item.get("remote_interface", "")).strip()
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
                    local_interface = str(item.get("local_interface", "")).strip()
                    remote_device = str(item.get("remote_device", "")).strip()
                    remote_interface = str(item.get("remote_interface", "")).strip()
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
