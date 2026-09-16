"""キーボード別タスクトレイアイコンの生成スクリプト。

32x32のドット絵をPillowで描画し、
  - pystray用のPNG(`*.png`、64x64にニアレストネイバー拡大)
  - Piskelエディタで直接開いて修正できる`*.piskel`(同じ32x32画像をそのまま埋め込んだもの)
を同じ描画コードから生成する。両者が同じ元データから作られるため、手作業でのズレが起きない。

再生成する場合:
    python -m app.assets.icons.generate_icons
"""
import base64
import io
import json
import os

from PIL import Image, ImageDraw

GRID = 32
PNG_SCALE = 2  # pystray用PNGの拡大率(32x32 -> 64x64)

ICON_DIR = os.path.dirname(os.path.abspath(__file__))
PISKEL_DIR = os.path.join(ICON_DIR, "piskel")


def _new_canvas():
    return Image.new("RGBA", (GRID, GRID), (0, 0, 0, 0))


def _draw_keyboard(rows, side_cluster, split_space, body, body_shadow, key, accent):
    """簡易化したキーボードのドット絵を描く共通ロジック。

    実機の精密な模写ではなく、タスクトレイの実表示(16〜24px程度)でも
    キーボードごとの見分けがつくシルエット+差し色を狙う。
    """
    img = _new_canvas()
    draw = ImageDraw.Draw(img)

    main_w = 22 if side_cluster else 26
    x0, y0 = 2, 8
    x1 = x0 + main_w
    y1 = 26

    # ケース本体(主要キー領域)
    draw.rectangle((x0, y0, x1, y1), fill=body, outline=body_shadow)

    # キートップ(行ごとの細長い矩形で簡略化)
    row_h = (y1 - y0 - 2) / rows
    for r in range(rows - 1):  # 最下段はスペースバー行として別扱い
        ry0 = int(y0 + 1 + r * row_h)
        ry1 = int(y0 + 1 + (r + 1) * row_h) - 1
        draw.rectangle((x0 + 1, ry0, x1 - 1, ry1), fill=key)

    # 最下段: スペースバー
    space_y0 = int(y1 - row_h) + 1
    if split_space:
        mid = (x0 + x1) // 2
        draw.rectangle((x0 + 1, space_y0, mid - 1, y1 - 1), fill=accent)
        draw.rectangle((mid + 1, space_y0, x1 - 1, y1 - 1), fill=accent)
    else:
        draw.rectangle((x0 + 5, space_y0, x1 - 5, y1 - 1), fill=accent)

    # 右側のナビゲーションキー列(65%のみ)
    if side_cluster:
        nx0, nx1 = x1 + 2, x1 + 2 + 5
        ny0, ny1 = y0, y0 + 12
        draw.rectangle((nx0, ny0, nx1, ny1), fill=body, outline=body_shadow)
        for r in range(3):
            ry0 = ny0 + 1 + r * 4
            draw.rectangle((nx0 + 1, ry0, nx1 - 1, ry0 + 2), fill=key)

    return img


def _draw_f65():
    return _draw_keyboard(
        rows=5,
        side_cluster=True,
        split_space=False,
        body=(214, 214, 219, 255),        # 白に近いグレー(ケース)
        body_shadow=(176, 176, 183, 255),
        key=(240, 240, 243, 255),
        accent=(74, 144, 226, 255),        # ブルーの差し色
    )


def _draw_th40():
    return _draw_keyboard(
        rows=4,
        side_cluster=False,
        split_space=True,
        body=(196, 168, 172, 255),        # 赤みがかったグレー(ケース)
        body_shadow=(157, 132, 136, 255),
        key=(224, 204, 207, 255),
        accent=(163, 58, 102, 255),        # 赤紫の差し色
    )


def _draw_laptop():
    """デフォルト用: ASUS Vivobook(黒っぽいノートPC)のキーボード面+タッチパッドを上から見た構図。"""
    img = _new_canvas()
    draw = ImageDraw.Draw(img)

    body = (46, 46, 50, 255)          # 黒っぽい筐体
    body_shadow = (25, 25, 28, 255)
    key = (92, 92, 98, 255)           # キートップ(筐体よりやや明るいダークグレー)
    trackpad = (70, 70, 76, 255)
    trackpad_outline = (112, 112, 118, 255)

    x0, y0, x1, y1 = 3, 3, 28, 28
    draw.rectangle((x0, y0, x1, y1), fill=body, outline=body_shadow)

    # キーボード領域(上側)
    kb_y0, kb_y1 = y0 + 2, y0 + 15
    rows = 4
    row_h = (kb_y1 - kb_y0) / rows
    for r in range(rows):
        ry0 = int(kb_y0 + r * row_h)
        ry1 = int(kb_y0 + (r + 1) * row_h) - 1
        draw.rectangle((x0 + 2, ry0, x1 - 2, ry1), fill=key)

    # タッチパッド(下側中央、角丸)
    tp_x0, tp_x1 = x0 + 7, x1 - 7
    tp_y0, tp_y1 = kb_y1 + 2, y1 - 2
    draw.rounded_rectangle((tp_x0, tp_y0, tp_x1, tp_y1), radius=1, fill=trackpad, outline=trackpad_outline)

    return img


ICONS = {
    "default": _draw_laptop,
    "f65": _draw_f65,
    "th40": _draw_th40,
}


def _png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _write_piskel(name, img):
    """32x32画像をそのまま埋め込んだ.piskelファイルを書き出す。"""
    b64 = base64.b64encode(_png_bytes(img)).decode("ascii")
    layer = {
        "name": "Layer 1",
        "opacity": 1,
        "frameCount": 1,
        "chunks": [
            {
                "layout": [[0]],
                "base64PNG": f"data:image/png;base64,{b64}",
            }
        ],
    }
    piskel_doc = {
        "modelVersion": 2,
        "piskel": {
            "name": name,
            "description": f"{name} タスクトレイアイコン(打鍵アクティビティトラッカー用)",
            "fps": 12,
            "height": GRID,
            "width": GRID,
            "layers": [json.dumps(layer, ensure_ascii=False)],
        },
    }
    path = os.path.join(PISKEL_DIR, f"{name}.piskel")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(piskel_doc, f, ensure_ascii=False, indent=2)
    return path


def generate(names=None):
    """`names`を指定すると、そのアイコンだけを(再)生成する。省略時は全アイコンを生成し直す。

    既存のPNGを手動編集(Piskelでの微調整等)している場合、そのアイコンは`names`に
    含めないこと。含めると手動編集分が上書きされてしまう。
    """
    os.makedirs(ICON_DIR, exist_ok=True)
    os.makedirs(PISKEL_DIR, exist_ok=True)

    targets = {name: ICONS[name] for name in names} if names else ICONS

    for name, draw_fn in targets.items():
        img = draw_fn()

        png_path = os.path.join(ICON_DIR, f"{name}.png")
        upscaled = img.resize((GRID * PNG_SCALE, GRID * PNG_SCALE), Image.NEAREST)
        upscaled.save(png_path)

        piskel_path = _write_piskel(name, img)

        print(f"generated: {png_path}")
        print(f"generated: {piskel_path}")


if __name__ == "__main__":
    generate()
