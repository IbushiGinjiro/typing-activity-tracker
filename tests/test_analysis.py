import datetime
import unittest

from app.analysis import aggregate_daily, aggregate_period, build_bursts, burst_correction_rate, burst_cpm


class BuildBurstsTest(unittest.TestCase):
    def test_splits_on_gap(self):
        events = [
            (0.0, "char", "kbA"),
            (0.5, "char", "kbA"),
            (1.0, "char", "kbA"),
            (5.0, "char", "kbA"),  # gap >= 2s -> new burst
        ]
        bursts = build_bursts(events, burst_gap_seconds=2.0, typo_window_seconds=1.0)
        self.assertEqual(len(bursts), 2)
        self.assertEqual(bursts[0]["char_count"], 3)
        self.assertEqual(bursts[1]["char_count"], 1)

    def test_separates_keyboards_independently(self):
        events = [
            (0.0, "char", "kbA"),
            (0.5, "char", "kbB"),
            (1.0, "char", "kbA"),
        ]
        bursts = build_bursts(events, burst_gap_seconds=2.0, typo_window_seconds=1.0)
        keyboards = {b["keyboard"] for b in bursts}
        self.assertEqual(keyboards, {"kbA", "kbB"})

    def test_typo_vs_revision_classification(self):
        events = [
            (0.0, "char", "kbA"),
            (0.5, "backspace", "kbA"),   # gap 0.5s <= 1.0s -> typo
            (5.0, "char", "kbA"),
            (5.2, "char", "kbA"),
            (10.0, "backspace", "kbA"),  # gap 4.8s > 1.0s -> revision
        ]
        bursts = build_bursts(events, burst_gap_seconds=2.0, typo_window_seconds=1.0)
        self.assertEqual(sum(b["typo_count"] for b in bursts), 1)
        self.assertEqual(sum(b["revision_count"] for b in bursts), 1)


class CpmTest(unittest.TestCase):
    def test_cpm_calculation(self):
        burst = {"duration_seconds": 60.0, "char_count": 300, "correction_count": 0}
        self.assertAlmostEqual(burst_cpm(burst), 300.0)

    def test_cpm_none_for_zero_duration(self):
        burst = {"duration_seconds": 0.0, "char_count": 1, "correction_count": 0}
        self.assertIsNone(burst_cpm(burst))

    def test_cpm_include_corrections(self):
        burst = {"duration_seconds": 60.0, "char_count": 100, "correction_count": 20}
        self.assertAlmostEqual(burst_cpm(burst, include_corrections=True), 120.0)


class CorrectionRateTest(unittest.TestCase):
    def test_rate(self):
        burst = {"char_count": 8, "correction_count": 2, "typo_count": 1}
        self.assertAlmostEqual(burst_correction_rate(burst), 1 / 10)


class AggregateDailyTest(unittest.TestCase):
    def test_groups_by_date_and_keyboard(self):
        day1 = datetime.datetime(2026, 9, 8, 10, 0, 0).timestamp()
        events = [
            (day1, "char", "kbA"),
            (day1 + 0.5, "char", "kbA"),
        ]
        bursts = build_bursts(events, burst_gap_seconds=2.0, typo_window_seconds=1.0)
        summary = aggregate_daily(bursts)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["keyboard"], "kbA")
        self.assertEqual(summary[0]["total_keystrokes"], 2)


class AggregatePeriodTest(unittest.TestCase):
    def test_groups_by_iso_week(self):
        # 2026-09-08(火)と2026-09-10(木)は同じISO週(2026-W37)のはず
        d1 = datetime.datetime(2026, 9, 8, 10, 0, 0).timestamp()
        d2 = datetime.datetime(2026, 9, 10, 10, 0, 0).timestamp()
        events = [(d1, "char", "kbA"), (d2, "char", "kbA")]
        bursts = build_bursts(events, burst_gap_seconds=2.0, typo_window_seconds=1.0)
        summary = aggregate_period(bursts, "week")
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["period"], "2026-W37")
        self.assertEqual(summary[0]["total_keystrokes"], 2)

    def test_different_weeks_not_merged(self):
        d1 = datetime.datetime(2026, 9, 6, 10, 0, 0).timestamp()   # 2026-W36
        d2 = datetime.datetime(2026, 9, 8, 10, 0, 0).timestamp()   # 2026-W37
        events = [(d1, "char", "kbA"), (d2, "char", "kbA")]
        bursts = build_bursts(events, burst_gap_seconds=2.0, typo_window_seconds=1.0)
        summary = aggregate_period(bursts, "week")
        self.assertEqual(len(summary), 2)

    def test_groups_by_month(self):
        d1 = datetime.datetime(2026, 9, 1, 10, 0, 0).timestamp()
        d2 = datetime.datetime(2026, 9, 30, 10, 0, 0).timestamp()
        events = [(d1, "char", "kbA"), (d2, "char", "kbA")]
        bursts = build_bursts(events, burst_gap_seconds=2.0, typo_window_seconds=1.0)
        summary = aggregate_period(bursts, "month")
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["period"], "2026-09")

    def test_groups_by_year(self):
        d1 = datetime.datetime(2026, 1, 1, 10, 0, 0).timestamp()
        d2 = datetime.datetime(2026, 12, 31, 10, 0, 0).timestamp()
        events = [(d1, "char", "kbA"), (d2, "char", "kbA")]
        bursts = build_bursts(events, burst_gap_seconds=2.0, typo_window_seconds=1.0)
        summary = aggregate_period(bursts, "year")
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["period"], "2026")

    def test_invalid_range_type_raises(self):
        events = [(datetime.datetime(2026, 9, 8, 10, 0, 0).timestamp(), "char", "kbA")]
        bursts = build_bursts(events, burst_gap_seconds=2.0, typo_window_seconds=1.0)
        with self.assertRaises(ValueError):
            aggregate_period(bursts, "day")


if __name__ == "__main__":
    unittest.main()
