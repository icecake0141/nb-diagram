import unittest

from nbcart.reconcile.match import reconcile
from nbcart.reconcile.normalize import normalize_link


class ReconcileMatchTests(unittest.TestCase):
    def test_pair_interface_diff_is_classified_as_mismatch(self):
        expected = [normalize_link("sw1", "xe-0/0/1", "sw2", "xe-0/0/2")]
        observed = [normalize_link("sw1", "xe-0/0/9", "sw2", "xe-0/0/10")]

        report = reconcile(expected, observed)
        out = report.to_dict()
        self.assertEqual(out["summary"]["mismatched_count"], 1)
        self.assertEqual(out["summary"]["missing_count"], 0)
        self.assertEqual(out["summary"]["unexpected_count"], 0)

    def test_unrelated_pair_remains_missing_unexpected(self):
        expected = [normalize_link("sw1", "xe-0/0/1", "sw2", "xe-0/0/2")]
        observed = [normalize_link("sw3", "xe-0/0/9", "sw4", "xe-0/0/10")]

        report = reconcile(expected, observed)
        out = report.to_dict()
        self.assertEqual(out["summary"]["mismatched_count"], 0)
        self.assertEqual(out["summary"]["missing_count"], 1)
        self.assertEqual(out["summary"]["unexpected_count"], 1)


if __name__ == "__main__":
    unittest.main()
