import unittest
from unittest.mock import patch

from nbcart.reconcile.collectors.ssh import SshLldpCollector


class SshCollectorTests(unittest.TestCase):
    @patch("nbcart.reconcile.collectors.ssh.subprocess.run")
    def test_collect_parses_json_neighbors(self, run_mock):
        class Result:
            returncode = 0
            stderr = ""
            stdout = (
                '[{"local_interface":"xe-0/0/1","remote_device":"leaf-01",'
                '"remote_interface":"Eth1/1"}]'
            )

        run_mock.return_value = Result()

        collector = SshLldpCollector()
        links = collector.collect(
            seed_device="spine-01",
            params={
                "host": "192.0.2.20",
                "username": "netops",
                "command": "show lldp neighbors",
            },
        )
        self.assertEqual(len(links), 1)
        link = links[0]
        self.assertEqual(link.left.device, "leaf-01")
        self.assertEqual(link.right.device, "spine-01")

    @patch("nbcart.reconcile.collectors.ssh.subprocess.run")
    def test_collect_parses_csv_lines_when_not_json(self, run_mock):
        class Result:
            returncode = 0
            stderr = ""
            stdout = "xe-0/0/1,leaf-01,Eth1/1\nxe-0/0/2,leaf-02,Eth1/2\n"

        run_mock.return_value = Result()
        collector = SshLldpCollector()
        links = collector.collect(
            seed_device="spine-01",
            params={"host": "192.0.2.20", "username": "netops", "command": "show lldp"},
        )
        self.assertEqual(len(links), 2)

    def test_collect_uses_neighbors_param_without_ssh_command(self):
        collector = SshLldpCollector()
        links = collector.collect(
            seed_device="spine-01",
            params={
                "neighbors": [
                    {
                        "local_interface": "xe-0/0/1",
                        "remote_device": "leaf-01",
                        "remote_interface": "Eth1/1",
                    }
                ]
            },
        )
        self.assertEqual(len(links), 1)

    def test_collect_accepts_neighbor_alias_keys(self):
        collector = SshLldpCollector()
        links = collector.collect(
            seed_device="spine-01",
            params={
                "neighbors": [
                    {
                        "local_port": "xe-0/0/1",
                        "system_name": "leaf-01",
                        "port_id": "Eth1/1",
                    }
                ]
            },
        )
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].left.device, "leaf-01")

    @patch("nbcart.reconcile.collectors.ssh.subprocess.run")
    def test_collect_parses_pipe_separated_table_lines(self, run_mock):
        class Result:
            returncode = 0
            stderr = ""
            stdout = "xe-0/0/1 | leaf-01 | Eth1/1\nxe-0/0/2 | leaf-02 | Eth1/2\n"

        run_mock.return_value = Result()
        collector = SshLldpCollector()
        links = collector.collect(
            seed_device="spine-01",
            params={"host": "192.0.2.20", "username": "netops", "command": "show lldp"},
        )
        self.assertEqual(len(links), 2)


if __name__ == "__main__":
    unittest.main()
