import unittest
from pathlib import Path

from nbcart.reconcile.parsers import VENDOR_PARSERS, parse_generic

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ssh_lldp"


def _edges(links):
    return {
        (link.left.device, link.left.interface, link.right.device, link.right.interface)
        for link in links
    }


class ParserFixtureTests(unittest.TestCase):
    def test_arista_eos_fixture(self):
        text = (FIXTURE_DIR / "arista_eos.json").read_text(encoding="utf-8")
        links = VENDOR_PARSERS["arista_eos"]("spine-01", text)
        self.assertEqual(len(links), 2)
        self.assertIn(("leaf-01", "ethernet2", "spine-01", "ethernet1"), _edges(links))

    def test_cisco_ios_fixture(self):
        text = (FIXTURE_DIR / "cisco_ios.txt").read_text(encoding="utf-8")
        links = VENDOR_PARSERS["cisco_ios"]("spine-01", text)
        self.assertEqual(len(links), 2)
        self.assertIn(("leaf-02", "ethernet2/2", "spine-01", "ethernet1/2"), _edges(links))

    def test_cisco_nxos_fixture(self):
        text = (FIXTURE_DIR / "cisco_nxos.json").read_text(encoding="utf-8")
        links = VENDOR_PARSERS["cisco_nxos"]("spine-01", text)
        self.assertEqual(len(links), 2)
        self.assertIn(("leaf-01", "ethernet2/1", "spine-01", "ethernet1/1"), _edges(links))

    def test_juniper_junos_fixture(self):
        text = (FIXTURE_DIR / "juniper_junos.json").read_text(encoding="utf-8")
        links = VENDOR_PARSERS["juniper_junos"]("spine-01", text)
        self.assertEqual(len(links), 2)
        self.assertIn(("leaf-02", "ethernet1/2", "spine-01", "ge-0/0/2"), _edges(links))

    def test_fortinet_fixture(self):
        text = (FIXTURE_DIR / "fortinet_fortiswitch_os.txt").read_text(encoding="utf-8")
        links = VENDOR_PARSERS["fortinet_fortiswitch_os"]("fsw-core", text)
        self.assertEqual(len(links), 2)
        self.assertIn(("fsw-core", "port1", "leaf-01", "port2"), _edges(links))

    def test_generic_pipe_fixture(self):
        text = (FIXTURE_DIR / "generic_pipe.txt").read_text(encoding="utf-8")
        links = parse_generic("spine-01", text)
        self.assertEqual(len(links), 2)
        self.assertIn(("leaf-01", "ethernet1/1", "spine-01", "xe-0/0/1"), _edges(links))


if __name__ == "__main__":
    unittest.main()
