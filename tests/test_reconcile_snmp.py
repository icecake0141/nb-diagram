import unittest
from unittest.mock import patch

from nbcart.reconcile.collectors.snmp import SnmpLldpCollector


class SnmpCollectorTests(unittest.TestCase):
    def test_parse_walk_line_extracts_indices_and_value(self):
        line = '.1.0.8802.1.1.2.1.4.1.1.9.600.12.1 = STRING: "leaf-01"'
        parsed = SnmpLldpCollector._parse_walk_line(line)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        indices, value = parsed
        self.assertEqual(indices[-3:], [600, 12, 1])
        self.assertEqual(value, "leaf-01")

    @patch("nbcart.reconcile.collectors.snmp.subprocess.run")
    def test_collect_builds_links_from_snmpwalk_outputs(self, run_mock):
        def mk(stdout: str, returncode: int = 0, stderr: str = ""):
            class Result:
                pass

            r = Result()
            r.stdout = stdout
            r.stderr = stderr
            r.returncode = returncode
            return r

        run_mock.side_effect = [
            mk(
                '.1.0.8802.1.1.2.1.4.1.1.9.600.12.1 = STRING: "leaf-01"\n'
                '.1.0.8802.1.1.2.1.4.1.1.9.600.13.1 = STRING: "leaf-02"\n'
            ),
            mk(
                '.1.0.8802.1.1.2.1.4.1.1.7.600.12.1 = STRING: "Ethernet1/1"\n'
                '.1.0.8802.1.1.2.1.4.1.1.7.600.13.1 = STRING: "Ethernet1/2"\n'
            ),
            mk(
                '.1.0.8802.1.1.2.1.3.7.1.4.12 = STRING: "xe-0/0/12"\n'
                '.1.0.8802.1.1.2.1.3.7.1.4.13 = STRING: "xe-0/0/13"\n'
            ),
            mk(
                '.1.3.6.1.2.1.31.1.1.1.1.12 = STRING: "xe-0/0/12"\n'
                '.1.3.6.1.2.1.31.1.1.1.1.13 = STRING: "xe-0/0/13"\n'
            ),
        ]

        collector = SnmpLldpCollector()
        links = collector.collect(
            seed_device="spine-01",
            params={"host": "192.0.2.10", "community": "public"},
        )

        self.assertEqual(len(links), 2)
        keys = {
            (link.left.device, link.left.interface, link.right.device, link.right.interface)
            for link in links
        }
        self.assertIn(("leaf-01", "ethernet1/1", "spine-01", "xe-0/0/12"), keys)
        self.assertIn(("leaf-02", "ethernet1/2", "spine-01", "xe-0/0/13"), keys)
        self.assertEqual(run_mock.call_count, 4)

    @patch("nbcart.reconcile.collectors.snmp.subprocess.run")
    def test_collect_raises_on_snmp_error(self, run_mock):
        class Result:
            stdout = ""
            stderr = "Timeout: No Response from 192.0.2.10"
            returncode = 1

        run_mock.return_value = Result()
        collector = SnmpLldpCollector()

        with self.assertRaisesRegex(ValueError, "Timeout"):
            collector.collect(
                seed_device="spine-01",
                params={"host": "192.0.2.10", "community": "public"},
            )

    @patch("nbcart.reconcile.collectors.snmp.subprocess.run")
    @patch.dict("os.environ", {"SNMP_COMMUNITY": "from-env"}, clear=True)
    def test_collect_reads_community_from_env_name(self, run_mock):
        def mk(stdout: str):
            class Result:
                pass

            r = Result()
            r.stdout = stdout
            r.stderr = ""
            r.returncode = 0
            return r

        run_mock.side_effect = [
            mk('.1.0.8802.1.1.2.1.4.1.1.9.600.12.1 = STRING: "leaf-01"\n'),
            mk('.1.0.8802.1.1.2.1.4.1.1.7.600.12.1 = STRING: "Ethernet1/1"\n'),
            mk('.1.0.8802.1.1.2.1.3.7.1.4.12 = STRING: "xe-0/0/12"\n'),
            mk('.1.3.6.1.2.1.31.1.1.1.1.12 = STRING: "xe-0/0/12"\n'),
        ]

        collector = SnmpLldpCollector()
        links = collector.collect(
            seed_device="spine-01",
            params={"host": "192.0.2.10", "community_env": "SNMP_COMMUNITY"},
        )
        self.assertEqual(len(links), 1)
        used_cmd = run_mock.call_args_list[0][0][0]
        self.assertIn("from-env", used_cmd)

    @patch("nbcart.reconcile.collectors.snmp.subprocess.run")
    def test_collect_falls_back_to_ifname_when_lldp_local_desc_missing(self, run_mock):
        def mk(stdout: str):
            class Result:
                pass

            r = Result()
            r.stdout = stdout
            r.stderr = ""
            r.returncode = 0
            return r

        run_mock.side_effect = [
            mk('.1.0.8802.1.1.2.1.4.1.1.9.600.12.1 = STRING: "leaf-01"\n'),
            mk('.1.0.8802.1.1.2.1.4.1.1.7.600.12.1 = STRING: "Ethernet1/1"\n'),
            mk(""),
            mk('.1.3.6.1.2.1.31.1.1.1.1.12 = STRING: "xe-0/0/12"\n'),
        ]
        collector = SnmpLldpCollector()
        links = collector.collect(
            seed_device="spine-01",
            params={"host": "192.0.2.10", "community": "public"},
        )
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].right.interface, "xe-0/0/12")


if __name__ == "__main__":
    unittest.main()
