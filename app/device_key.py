"""PnPデバイスのDeviceID文字列から、機種を識別するためのVID/PIDキーを取り出す。

例:
    HID\\VID_FEED&PID_4346&MI_00\\8&273C3704&0&0000  -> "VID_FEED&PID_4346"
    ACPI\\ATK3001\\4&230E843&0                        -> None(VID/PIDを持たない内蔵キーボード等)
"""
import re

_VID_PID_RE = re.compile(r"VID_([0-9A-Fa-f]{4}).*?PID_([0-9A-Fa-f]{4})", re.IGNORECASE)


def extract_device_key(device_id):
    """device_id(WMIのDeviceID)から "VID_xxxx&PID_yyyy" 形式のキーを返す。

    複数インターフェース(MI_00/MI_01等)を持つ複合デバイスでも、同じ物理キーボードなら
    同じキーになるよう、インターフェース番号・インスタンスパスは含めない。
    VID/PIDが見つからない場合(内蔵PS/2キーボード等)はNoneを返す。
    """
    if not device_id:
        return None
    m = _VID_PID_RE.search(device_id)
    if not m:
        return None
    vid, pid = m.group(1).upper(), m.group(2).upper()
    return f"VID_{vid}&PID_{pid}"
