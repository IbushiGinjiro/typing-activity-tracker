"""SQLiteへのイベント記録・読み出し。

記録するのはキー種別(char/backspace/delete)とタイムスタンプ、
現在選択中のキーボードラベルのみ。実際に入力された文字列は記録しない。
"""
import os
import sqlite3
import threading

_SCHEMA = """
CREATE TABLE IF NOT EXISTS keyboards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    key_type TEXT NOT NULL CHECK (key_type IN ('char', 'backspace', 'delete')),
    keyboard_id INTEGER NOT NULL REFERENCES keyboards(id)
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
CREATE INDEX IF NOT EXISTS idx_events_keyboard ON events (keyboard_id);

-- USB/BluetoothキーボードのVID/PID("VID_xxxx&PID_yyyy")と登録済みラベルの対応表。
-- 自動検出(PnPイベント)で「このデバイスはこのラベルである」を引くのに使う。
CREATE TABLE IF NOT EXISTS device_keyboards (
    device_key TEXT PRIMARY KEY,
    keyboard_id INTEGER NOT NULL REFERENCES keyboards(id)
);

-- 打鍵イベント記録時点で、どのラベルが「どのVID/PID・どの切替経路」で
-- 選ばれていたかの履歴。VID/PID衝突等で誤ラベリングに後から気づいた際に、
-- 該当期間だけ遡って訂正できるようにするための監査ログ。
CREATE TABLE IF NOT EXISTS keyboard_switches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    keyboard_id INTEGER NOT NULL REFERENCES keyboards(id),
    device_key TEXT,
    method TEXT NOT NULL CHECK (method IN ('manual', 'auto', 'fallback'))
);

CREATE INDEX IF NOT EXISTS idx_switches_ts ON keyboard_switches (ts);
"""


class Database:
    """1プロセス内で使い回す薄いラッパー。書き込みはロックで直列化する。"""

    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def get_or_create_keyboard(self, name):
        with self._lock:
            cur = self._conn.execute("SELECT id FROM keyboards WHERE name = ?", (name,))
            row = cur.fetchone()
            if row:
                return row[0]
            cur = self._conn.execute("INSERT INTO keyboards (name) VALUES (?)", (name,))
            self._conn.commit()
            return cur.lastrowid

    def list_keyboards(self):
        cur = self._conn.execute("SELECT id, name FROM keyboards ORDER BY name")
        return cur.fetchall()

    def record_event(self, ts, key_type, keyboard_id):
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (ts, key_type, keyboard_id) VALUES (?, ?, ?)",
                (ts, key_type, keyboard_id),
            )
            self._conn.commit()

    def get_keyboard_for_device(self, device_key):
        """device_key("VID_xxxx&PID_yyyy")に紐付くラベル名を返す。未登録ならNone。"""
        cur = self._conn.execute(
            "SELECT k.name FROM device_keyboards d JOIN keyboards k ON k.id = d.keyboard_id "
            "WHERE d.device_key = ?",
            (device_key,),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def set_device_keyboard(self, device_key, keyboard_name):
        """device_keyをkeyboard_nameに紐付ける(既存の紐付けは上書き)。"""
        keyboard_id = self.get_or_create_keyboard(keyboard_name)
        with self._lock:
            self._conn.execute(
                "INSERT INTO device_keyboards (device_key, keyboard_id) VALUES (?, ?) "
                "ON CONFLICT(device_key) DO UPDATE SET keyboard_id = excluded.keyboard_id",
                (device_key, keyboard_id),
            )
            self._conn.commit()
        return keyboard_id

    def record_switch(self, ts, keyboard_id, device_key, method):
        """キーボードラベルの切替履歴を記録する(method: manual/auto/fallback)。

        VID/PID衝突等で誤ラベリングに後から気づいた際、どの期間がどのdevice_key・
        どの経路で記録されていたかを遡って確認・訂正できるようにするための監査ログ。
        """
        with self._lock:
            self._conn.execute(
                "INSERT INTO keyboard_switches (ts, keyboard_id, device_key, method) VALUES (?, ?, ?, ?)",
                (ts, keyboard_id, device_key, method),
            )
            self._conn.commit()

    def fetch_events(self, since_ts=None):
        """(ts, key_type, keyboard_name) のタプル列を時刻順に返す。"""
        query = (
            "SELECT e.ts, e.key_type, k.name FROM events e "
            "JOIN keyboards k ON k.id = e.keyboard_id"
        )
        params = ()
        if since_ts is not None:
            query += " WHERE e.ts >= ?"
            params = (since_ts,)
        query += " ORDER BY e.ts"
        cur = self._conn.execute(query, params)
        return cur.fetchall()

    def close(self):
        self._conn.close()
