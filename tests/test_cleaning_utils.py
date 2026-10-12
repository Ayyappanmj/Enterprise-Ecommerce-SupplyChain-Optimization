"""
Unit tests for src/cleaning/cleaning_utils.py.

Written as unittest.TestCase classes (not pytest fixtures/plain asserts) so
they run two ways with zero extra setup:
    python -m unittest tests.test_cleaning_utils      (stdlib only)
    pytest tests/test_cleaning_utils.py                (pytest auto-discovers
                                                          unittest.TestCase)
This project was verified with the first form - no network access was
available to install pytest in the build environment (see README Phase 10).
"""
import unittest

import numpy as np
import pandas as pd

from src.cleaning import cleaning_utils as cu


class TestDropDuplicates(unittest.TestCase):
    def test_removes_exact_duplicate_keys(self):
        df = pd.DataFrame({"id": ["A", "A", "B"], "val": [1, 2, 3]})
        out, n_removed = cu.drop_duplicates(df, subset=["id"])
        self.assertEqual(n_removed, 1)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[out["id"] == "A"]["val"].iloc[0], 1)  # first occurrence kept

    def test_no_duplicates_removes_nothing(self):
        df = pd.DataFrame({"id": ["A", "B", "C"]})
        out, n_removed = cu.drop_duplicates(df, subset=["id"])
        self.assertEqual(n_removed, 0)
        self.assertEqual(len(out), 3)


class TestDropNullCritical(unittest.TestCase):
    def test_drops_rows_with_null_key(self):
        df = pd.DataFrame({"id": ["A", None, "C"], "fk": [1, 2, None]})
        out, n_dropped = cu.drop_null_critical(df, critical_cols=["id", "fk"])
        # row 1 (None id) and row 2 (None fk) both drop -> only row 0 survives
        self.assertEqual(n_dropped, 2)
        self.assertEqual(len(out), 1)

    def test_empty_critical_list_drops_nothing(self):
        df = pd.DataFrame({"id": ["A", None]})
        out, n_dropped = cu.drop_null_critical(df, critical_cols=[])
        self.assertEqual(n_dropped, 0)
        self.assertEqual(len(out), 2)


class TestFixNegativeValues(unittest.TestCase):
    def test_clips_negative_to_zero_and_counts(self):
        df = pd.DataFrame({"qty": [5, -3, 0, -1]})
        out, n_fixed = cu.fix_negative_values(df, cols=["qty"])
        self.assertEqual(n_fixed, 2)
        self.assertEqual(list(out["qty"]), [5, 0, 0, 0])

    def test_positive_values_untouched(self):
        df = pd.DataFrame({"qty": [5, 10, 0]})
        out, n_fixed = cu.fix_negative_values(df, cols=["qty"])
        self.assertEqual(n_fixed, 0)
        self.assertEqual(list(out["qty"]), [5, 10, 0])

    def test_missing_column_is_ignored_not_an_error(self):
        df = pd.DataFrame({"other": [1, 2]})
        out, n_fixed = cu.fix_negative_values(df, cols=["does_not_exist"])
        self.assertEqual(n_fixed, 0)
        self.assertEqual(len(out), 2)


class TestFlagOutliersIQR(unittest.TestCase):
    def test_flags_an_extreme_value(self):
        # 19 normal values clustered near 10, one wildly larger outlier.
        values = [10, 11, 9, 10, 12, 9, 11, 10, 9, 10, 11, 10, 9, 12, 10, 11, 9, 10, 11, 500]
        df = pd.DataFrame({"amount": values})
        out, n_flagged = cu.flag_outliers_iqr(df, cols=["amount"])
        self.assertEqual(n_flagged, 1)
        self.assertTrue(out["amount_is_outlier"].iloc[-1])
        self.assertFalse(out["amount_is_outlier"].iloc[0])

    def test_does_not_delete_rows(self):
        df = pd.DataFrame({"amount": [1, 2, 3, 1000]})
        out, _ = cu.flag_outliers_iqr(df, cols=["amount"])
        self.assertEqual(len(out), len(df))  # flagged, not removed


class TestFixImpossibleDates(unittest.TestCase):
    def test_nulls_end_date_when_before_start_date(self):
        df = pd.DataFrame({
            "ship_date": ["2024-01-10", "2024-01-10"],
            "delivery_date": ["2024-01-15", "2024-01-05"],  # 2nd row is impossible
        })
        out, n_bad = cu.fix_impossible_dates(df, "ship_date", "delivery_date")
        self.assertEqual(n_bad, 1)
        self.assertFalse(pd.isna(out["delivery_date"].iloc[0]))
        self.assertTrue(pd.isna(out["delivery_date"].iloc[1]))

    def test_missing_columns_returns_unchanged(self):
        df = pd.DataFrame({"a": [1, 2]})
        out, n_bad = cu.fix_impossible_dates(df, "start", "end")
        self.assertEqual(n_bad, 0)
        pd.testing.assert_frame_equal(out, df)


class TestNormalizeToUtc(unittest.TestCase):
    def test_subtracts_country_offset(self):
        countries_df = pd.DataFrame({
            "country_id": ["CTY001"],
            "country_name": ["Germany"],  # UTC+1 per COUNTRY_UTC_OFFSET_HOURS
        })
        df = pd.DataFrame({
            "order_date": ["2024-06-01 12:00:00"],
            "ship_country_id": ["CTY001"],
        })
        out = cu.normalize_to_utc(df, ["order_date"], "ship_country_id", countries_df)
        expected = pd.Timestamp("2024-06-01 11:00:00")  # 12:00 local - 1h offset = 11:00 UTC
        self.assertEqual(out["order_date_utc"].iloc[0], expected)

    def test_unknown_country_defaults_to_zero_offset(self):
        countries_df = pd.DataFrame({"country_id": ["CTY999"], "country_name": ["Nowhereland"]})
        df = pd.DataFrame({"order_date": ["2024-01-01 00:00:00"], "ship_country_id": ["CTY999"]})
        out = cu.normalize_to_utc(df, ["order_date"], "ship_country_id", countries_df)
        self.assertEqual(out["order_date_utc"].iloc[0], pd.Timestamp("2024-01-01 00:00:00"))


class TestConvertAmountToLocalCurrency(unittest.TestCase):
    def test_converts_using_most_recent_rate_on_or_before_date(self):
        df = pd.DataFrame({
            "order_date": ["2024-01-15"],
            "currency_code": ["EUR"],
            "amount_usd": [100.0],
        })
        fx_df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-10", "2024-01-20"],  # last one is AFTER the order
            "currency_code": ["EUR", "EUR", "EUR"],
            "rate_to_usd": [1.0, 0.5, 0.25],  # expect the Jan-10 rate (0.5) to apply
        })
        out = cu.convert_amount_to_local_currency(df, "amount_usd", "currency_code", "order_date", fx_df, "amount_local")
        self.assertAlmostEqual(out["amount_local"].iloc[0], 200.0)  # 100 / 0.5

    def test_missing_currency_in_fx_table_gives_nan(self):
        df = pd.DataFrame({"order_date": ["2024-01-15"], "currency_code": ["XYZ"], "amount_usd": [100.0]})
        fx_df = pd.DataFrame({"date": ["2024-01-01"], "currency_code": ["EUR"], "rate_to_usd": [1.0]})
        out = cu.convert_amount_to_local_currency(df, "amount_usd", "currency_code", "order_date", fx_df, "amount_local")
        self.assertTrue(pd.isna(out["amount_local"].iloc[0]))


if __name__ == "__main__":
    unittest.main()
