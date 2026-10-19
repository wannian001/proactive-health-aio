"""Optional training-runtime checks; synthetic data only, no personal files."""
import copy
import importlib.util
import unittest
from datetime import timedelta

from test_hrv_model import records
from healthaio.hrv_train import train


@unittest.skipUnless(importlib.util.find_spec("sklearn"),"training tests require optional scikit-learn")
class HRVTraining(unittest.TestCase):
    def test_changing_holdout_labels_cannot_change_selection_or_calibration(self):
        rows=records()
        now=rows[-1]["date"]+timedelta(days=1)
        before=train(rows,now)
        changed=copy.deepcopy(rows)
        for r in changed:
            if r["date"].isoformat() >= before["evaluation"]["start"]: r["hrv_ms"]*=1.8
        after=train(changed,now)
        self.assertEqual(before["selection"],after["selection"])
        self.assertEqual(before["selected"],after["selected"])
        self.assertEqual(before["interval_halfwidth_ms"],after["interval_halfwidth_ms"])
        self.assertNotEqual(before["evaluation"]["mae_ms"],after["evaluation"]["mae_ms"])
        self.assertLess(before["training"]["parity_max_abs_ms"],1e-7)


if __name__ == "__main__": unittest.main()
