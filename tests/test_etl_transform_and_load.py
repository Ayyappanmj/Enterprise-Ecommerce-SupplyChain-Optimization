import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.etl import transform, load as load_module


class TestTransform(unittest.TestCase):
    def test_add_ingestion_metadata_adds_expected_columns(self):
        df = pd.DataFrame({"a": [1, 2]})
        out = transform.add_ingestion_metadata(df, "web_orders")
        self.assertEqual(list(out["_source_system"]), ["web_orders", "web_orders"])
        self.assertIn("_ingested_at", out.columns)
        self.assertEqual(len(out), 2)

    def test_add_ingestion_metadata_does_not_mutate_input(self):
        df = pd.DataFrame({"a": [1]})
        transform.add_ingestion_metadata(df, "x")
        self.assertNotIn("_source_system", df.columns)  # original untouched

    def test_standardize_dates_converts_strings_to_timestamps(self):
        df = pd.DataFrame({"order_date": ["2024-01-01", "2024-06-15"]})
        out = transform.standardize_dates(df, ["order_date"])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(out["order_date"]))

    def test_standardize_dates_coerces_bad_values_to_nat(self):
        df = pd.DataFrame({"d": ["2024-01-01", "not-a-date"]})
        out = transform.standardize_dates(df, ["d"])
        self.assertTrue(pd.isna(out["d"].iloc[1]))

    def test_standardize_dates_ignores_missing_column(self):
        df = pd.DataFrame({"a": [1]})
        out = transform.standardize_dates(df, ["nonexistent"])
        pd.testing.assert_frame_equal(out, df)


class TestLoad(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.processed_dir = os.path.join(self.tmpdir.name, "processed")
        self.rejected_dir = os.path.join(self.tmpdir.name, "processed", "rejected")
        os.makedirs(self.rejected_dir, exist_ok=True)
        self.patchers = [
            patch.object(load_module, "PROCESSED_DIR", self.processed_dir),
            patch.object(load_module, "REJECTED_DIR", self.rejected_dir),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        self.tmpdir.cleanup()

    def test_load_creates_file_with_header_on_first_write(self):
        df = pd.DataFrame({"a": [1, 2]})
        n = load_module.load(df, "orders")
        self.assertEqual(n, 2)
        out_path = os.path.join(self.processed_dir, "orders.csv")
        self.assertTrue(os.path.exists(out_path))
        self.assertEqual(len(pd.read_csv(out_path)), 2)

    def test_load_appends_without_duplicating_header(self):
        load_module.load(pd.DataFrame({"a": [1]}), "orders")
        load_module.load(pd.DataFrame({"a": [2, 3]}), "orders")
        out_path = os.path.join(self.processed_dir, "orders.csv")
        result = pd.read_csv(out_path)
        self.assertEqual(len(result), 3)  # 1 + 2, not duplicated headers/rows
        self.assertEqual(list(result["a"]), [1, 2, 3])

    def test_load_empty_dataframe_writes_nothing(self):
        n = load_module.load(pd.DataFrame(), "orders")
        self.assertEqual(n, 0)
        self.assertFalse(os.path.exists(os.path.join(self.processed_dir, "orders.csv")))

    def test_quarantine_writes_timestamped_file(self):
        df = pd.DataFrame({"a": [1], "rejection_reason": ["bad"]})
        n = load_module.quarantine(df, "orders")
        self.assertEqual(n, 1)
        files = os.listdir(self.rejected_dir)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("orders_rejected_"))

    def test_quarantine_empty_or_none_writes_nothing(self):
        self.assertEqual(load_module.quarantine(pd.DataFrame(), "orders"), 0)
        self.assertEqual(load_module.quarantine(None, "orders"), 0)
        self.assertEqual(len(os.listdir(self.rejected_dir)), 0)


if __name__ == "__main__":
    unittest.main()
