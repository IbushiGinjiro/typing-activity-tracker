"""バースト区切り・タイポ訂正/推敲の分類・日次集計ロジック。

分類のしきい値(SPEC.md参照):
- バースト区切り: 打鍵間隔が burst_gap_seconds 以上空いたら新しいバースト
- タイポ訂正: 直前の打鍵から typo_window_seconds 以内のBackspace/Delete
              (それより間隔が空いていれば「推敲」として扱う)
"""
import statistics
from collections import defaultdict
from datetime import datetime

CORRECTION_TYPES = ("backspace", "delete")


def _group_by_keyboard(events):
    groups = defaultdict(list)
    for ts, key_type, keyboard_name in events:
        groups[keyboard_name].append((ts, key_type))
    return groups


def build_bursts(events, burst_gap_seconds, typo_window_seconds):
    """events: (ts, key_type, keyboard_name) のイテラブル(ts昇順)。

    戻り値: バーストのdictのリスト。
    """
    bursts = []
    for keyboard_name, kb_events in _group_by_keyboard(events).items():
        current = None
        prev_ts = None
        for ts, key_type in kb_events:
            gap = None if prev_ts is None else ts - prev_ts
            if current is None or gap is None or gap >= burst_gap_seconds:
                current = {
                    "keyboard": keyboard_name,
                    "start": ts,
                    "end": ts,
                    "char_count": 0,
                    "correction_count": 0,
                    "typo_count": 0,
                    "revision_count": 0,
                }
                bursts.append(current)

            if key_type == "char":
                current["char_count"] += 1
            else:
                current["correction_count"] += 1
                is_typo = gap is not None and gap <= typo_window_seconds
                if is_typo:
                    current["typo_count"] += 1
                else:
                    current["revision_count"] += 1

            current["end"] = ts
            prev_ts = ts

    for b in bursts:
        b["duration_seconds"] = b["end"] - b["start"]
    return bursts


def burst_cpm(burst, include_corrections=False):
    """1分あたりの打鍵数。バースト時間が0(単発打鍵)の場合はNoneを返す。"""
    duration_min = burst["duration_seconds"] / 60.0
    if duration_min <= 0:
        return None
    count = burst["char_count"]
    if include_corrections:
        count += burst["correction_count"]
    return count / duration_min


def burst_correction_rate(burst):
    total_keystrokes = burst["char_count"] + burst["correction_count"]
    if total_keystrokes == 0:
        return None
    return burst["typo_count"] / total_keystrokes


def _local_date(ts):
    return datetime.fromtimestamp(ts).date().isoformat()


def _period_key(ts, range_type):
    dt = datetime.fromtimestamp(ts)
    if range_type == "week":
        iso_year, iso_week, _ = dt.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if range_type == "month":
        return dt.strftime("%Y-%m")
    if range_type == "year":
        return dt.strftime("%Y")
    raise ValueError(f"unknown range_type: {range_type}")


def aggregate_daily(bursts):
    """(date, keyboard) ごとの日次サマリを返す。

    speed_cpm_median: バーストごとのCPM(文字のみ)の中央値
    correction_rate: タイポ訂正回数 / 総打鍵数
    """
    groups = defaultdict(list)
    for b in bursts:
        key = (_local_date(b["start"]), b["keyboard"])
        groups[key].append(b)

    results = []
    for (date, keyboard), day_bursts in sorted(groups.items()):
        cpm_values = [c for c in (burst_cpm(b) for b in day_bursts) if c is not None]
        total_char = sum(b["char_count"] for b in day_bursts)
        total_correction = sum(b["correction_count"] for b in day_bursts)
        total_typo = sum(b["typo_count"] for b in day_bursts)
        total_keystrokes = total_char + total_correction

        results.append(
            {
                "date": date,
                "keyboard": keyboard,
                "burst_count": len(day_bursts),
                "speed_cpm_median": statistics.median(cpm_values) if cpm_values else None,
                "total_keystrokes": total_keystrokes,
                "correction_rate": (total_typo / total_keystrokes) if total_keystrokes else None,
                "revision_count": sum(b["revision_count"] for b in day_bursts),
            }
        )
    return results


def aggregate_period(bursts, range_type):
    """(期間, keyboard) ごとのサマリを返す。range_typeは "week" / "month" / "year"。

    フィールドの意味は`aggregate_daily`と同じ(日付の代わりに期間ラベルを"period"に持つ)。
    """
    groups = defaultdict(list)
    for b in bursts:
        key = (_period_key(b["start"], range_type), b["keyboard"])
        groups[key].append(b)

    results = []
    for (period, keyboard), period_bursts in sorted(groups.items()):
        cpm_values = [c for c in (burst_cpm(b) for b in period_bursts) if c is not None]
        total_char = sum(b["char_count"] for b in period_bursts)
        total_correction = sum(b["correction_count"] for b in period_bursts)
        total_typo = sum(b["typo_count"] for b in period_bursts)
        total_keystrokes = total_char + total_correction

        results.append(
            {
                "period": period,
                "keyboard": keyboard,
                "burst_count": len(period_bursts),
                "speed_cpm_median": statistics.median(cpm_values) if cpm_values else None,
                "total_keystrokes": total_keystrokes,
                "correction_rate": (total_typo / total_keystrokes) if total_keystrokes else None,
                "revision_count": sum(b["revision_count"] for b in period_bursts),
            }
        )
    return results
